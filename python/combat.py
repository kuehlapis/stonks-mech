"""Combat: aim with lead, gun firing discipline, laser charge/release, reloads (interfaces.md "M1 modules")."""
import math

AIM_TOL_FRAC = 0.6  # fire when the actual aim is within 0.6 target radii of the desired aim at the target
MIN_TOL = 0.004  # rad, floor so long shots still fire
LOW_AMMO_FRAC = 0.5  # reload with no target in range at or below this fraction of the mag
LETHAL = False       # release a partial laser charge early when it already kills (giddy's Lethal rule)
AIM_PREDICT = False  # A/B switch: lead with variance-blended smoothed velocity; laser aims at release time
HIT_GATE = 0.25  # AIM_PREDICT: hold gun fire under this P(hit) (a miss is heard 320 m away)
PREDICT_WINDOW_S = 1.0  # s of velocity history per target; also the max blind extrapolation
MORTAR_MIN_DIST = 12.0  # m: closer and our own 50% splash (radius 7 m + knockback) hurts too much
MORTAR_TOL_M = 3.0  # fire when the aim error at the target is under this (splash radius is 7 m)
MORTAR_READY_S = 0.5  # take the torso from the gun when the mortar is this close to ready


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def intercept(d, v, speed, r0):
    """Time t >= 0 when a shot starting r0 out from the muzzle at `speed` meets a target at offset d moving at v.
    Solves |d + v t| = r0 + speed t; None if it can't catch the target."""
    a = v[0] * v[0] + v[1] * v[1] + v[2] * v[2] - speed * speed
    b = 2 * (d[0] * v[0] + d[1] * v[1] + d[2] * v[2] - r0 * speed)
    c = d[0] * d[0] + d[1] * d[1] + d[2] * d[2] - r0 * r0
    if abs(a) < 1e-9:
        return -c / b if b < 0 else None
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    s = math.sqrt(disc)
    ts = [t for t in ((-b - s) / (2 * a), (-b + s) / (2 * a)) if t >= 0]
    return min(ts) if ts else (0.0 if c <= 0 else None)


def arc_pitch(dx, dz, v, g, high):
    """Launch pitch to hit a point dx out and dz up at speed v under gravity g; None if out of reach."""
    if dx < 1e-6:
        return None
    disc = v ** 4 - g * (g * dx * dx + 2 * dz * v * v)
    if disc < 0:
        return None
    return math.atan((v * v + (1 if high else -1) * math.sqrt(disc)) / (g * dx))


class Combat:
    def __init__(self, cfg: dict, world) -> None:
        self.world = world
        cc = cfg.get("cubes", {})
        self.cpc, self.cap = cc.get("damage_per_cube", 0.04), cc.get("stat_cap", 10)
        self.wcfg = cfg.get("weapons", {})
        m = cfg.get("mech", {})
        self.radius = m.get("radius", 2.5)
        self.half_h = m.get("height", 9) / 2
        self.min_pitch = m.get("min_pitch", -0.7)
        self.max_pitch = m.get("max_pitch", 1.3)
        self.g = m.get("gravity", 22)
        self.accel = m.get("ground_accel", 58.5)  # bounds how far a strafer can turn away from its velocity
        mt = cfg.get("match", {})
        self.dt = mt.get("decide_every", 2) / mt.get("tick_hz", 20)  # the trigger is held this long
        self.hist = {}  # target id -> [(t, vel)] over the last PREDICT_WINDOW_S

    def _predict(self, obs, target, tp, tv):
        """(pos, vel) to lead with. Blend mean and instantaneous velocity by the window's variance:
        a strafer's reversals average out (aim at the band centre), a steady mover keeps its velocity."""
        t, tid = obs.get("t", 0.0), target.get("id")
        h = [e for e in self.hist.get(tid, []) if t - e[0] <= PREDICT_WINDOW_S]
        if target.get("visible", True) and (not h or h[-1][0] != t):
            h.append((t, list(tv)))
        self.hist[tid] = h
        if len(self.hist) > 64:  # drop targets gone for good
            self.hist = {k: v for k, v in self.hist.items() if v and t - v[-1][0] <= PREDICT_WINDOW_S}
        n = len(h)
        m = [sum(e[1][k] for e in h) / n for k in range(3)] if n else list(tv)
        var = sum((e[1][k] - m[k]) ** 2 for e in h for k in range(3)) / n if n else 0.0
        w = var / (var + m[0] ** 2 + m[1] ** 2 + m[2] ** 2 + 1e-6)
        v = [w * m[k] + (1 - w) * tv[k] for k in range(3)]
        gap = t - target.get("last_seen", t)
        if not target.get("visible", True) and 0 < gap <= PREDICT_WINDOW_S:
            # Path hint: out of sight but heading to us or the next zone centre -> pre-aim where it reappears.
            me = obs["self"]["pos"]
            zc = ((obs.get("zone") or {}).get("next_center") or me)[:2]
            if any((g[0] - tp[0]) * v[0] + (g[1] - tp[1]) * v[1] > 0 for g in (me, zc)):
                tp = [tp[0] + v[0] * gap, tp[1] + v[1] * gap, tp[2]]
        return tp, v, math.sqrt(var)

    def _future(self, tp, tv0, v, T):
        """Offset of the target's feet after T s: smoothed velocity, but no further from the instantaneous
        prediction than a full-accel turn allows (0.5 a T^2); airborne targets follow the gravity parabola."""
        dev = [(v[k] - tv0[k]) * T for k in range(2)]
        lim = 0.5 * self.accel * T * T
        n = math.hypot(*dev)
        sc = lim / n if n > lim else 1.0
        dx, dy = tv0[0] * T + dev[0] * sc, tv0[1] * T + dev[1] * sc
        wd = self.world
        g0 = wd.ground(tp[0], tp[1]) if wd else tp[2]
        g1 = wd.ground(tp[0] + dx, tp[1] + dy) if wd else tp[2]
        if abs(tv0[2]) > 0.5:  # airborne
            # shortcut: lands on terrain, not roofs; upgrade if roof fights matter
            dz = max(tv0[2] * T - 0.5 * self.g * T * T, min(g1 - tp[2], 0.0) if wd else -1e9)
        else:
            dz = g1 - g0  # walk along the terrain
        return [dx, dy, dz]

    def _stats(self, w):
        return w.get("stats") or self.wcfg.get(w.get("kind"), {})

    def _slots(self, obs, kind):
        return [(i, w) for i, w in enumerate(obs["self"].get("weapons") or []) if w and w.get("kind") == kind]

    def _aim_at(self, d):
        yaw = math.atan2(d[1], d[0])
        pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
        return [yaw, min(self.max_pitch, max(self.min_pitch, pitch))]

    @staticmethod
    def _err(a, b):
        return math.hypot(_wrap(a[0] - b[0]) * math.cos(b[1]), a[1] - b[1])

    def attack(self, obs: dict, target: dict) -> dict:
        me = obs["self"]
        st = me.get("stats") or {}
        p = me["pos"]
        muzzle = [p[0], p[1], p[2] + st.get("muzzle_height", 7)]
        r0 = st.get("radius", self.radius) + 0.5
        size = target.get("size", 1.0)
        tp = target["pos"]
        tv = tv0 = target.get("vel") or [0.0, 0.0, 0.0]
        sd = 0.0
        if AIM_PREDICT:
            tp, tv, sd = self._predict(obs, target, tp, tv)
        tc = [tp[0], tp[1], tp[2] + target.get("center_h", self.half_h * size)]
        d = [tc[0] - muzzle[0], tc[1] - muzzle[1], tc[2] - muzzle[2]]
        dist = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
        tol = max(MIN_TOL, math.atan2(AIM_TOL_FRAC * target.get("radius", self.radius * size), max(dist, 1.0)))
        actual = me.get("aim") or [0.0, 0.0]
        direct = self._aim_at(d)
        clear = self.world is None or self.world.los(muzzle, tc)
        fire = [False, False]
        reload = False
        aim = direct
        guns = self._slots(obs, "gun")
        for i, w in guns:
            s = self._stats(w)
            t = intercept(d, tv, s.get("speed", 252), r0)
            if t is None:
                continue
            pd = [d[k] + tv[k] * t for k in range(3)]
            p_hit = 1.0
            if AIM_PREDICT:  # the shot leaves next tick (+dt); no muzzle-velocity inheritance (sim/engine.py _spawn_proj)
                T = t + self.dt
                for _ in range(2):
                    f = self._future(tp, tv0, tv, T)
                    pd = [d[k] + f[k] for k in range(3)]
                    t = max(0.0, (math.sqrt(sum(x * x for x in pd)) - r0) / s.get("speed", 252))
                    T = t + self.dt
                rad = target.get("radius", self.radius * size)
                sig2 = (dist * math.tan(math.radians(s.get("spread_deg", 0.6)))) ** 2 + (min(sd * T, 0.5 * self.accel * T * T) / 2) ** 2
                p_hit = 1 - math.exp(-rad * rad / (2 * sig2 + 1e-9))
            lead = self._aim_at(pd)
            aim = lead
            in_range = r0 + s.get("speed", 252) * t <= s.get("range", 230)
            ammo = w.get("ammo", 0)
            if ammo <= 0 and not w.get("reload"):
                reload = True
            elif ammo <= LOW_AMMO_FRAC * s.get("mag", 12) and not in_range and not w.get("reload"):
                reload = True
            fire[i] = (in_range and clear and ammo > 0 and not w.get("reload")
                       and w.get("cooldown", 0) <= self.dt and self._err(actual, lead) <= tol and p_hit >= HIT_GATE)
        for i, w in self._slots(obs, "mortar"):
            s = self._stats(w)
            sol = self._mortar(p[2] + st.get("height", 2 * self.half_h) + 0.5, p, tp, tv, s, r0, clear)
            ready = w.get("cooldown", 0)
            if sol is None or dist < MORTAR_MIN_DIST or ready > MORTAR_READY_S:
                continue
            aim, rng = sol
            fire[i] = ready <= self.dt and self._err(actual, aim) * rng <= MORTAR_TOL_M
        for i, w in self._slots(obs, "laser"):
            s = self._stats(w)
            charge = w.get("charge", 0)
            if AIM_PREDICT:  # hitscan fires at release: aim where the target will be then
                lead_t = max(s.get("charge", 0.75) - charge, 0.0) or self.dt
                direct = self._aim_at([d[k] + tv[k] * lead_t for k in range(3)])
            if charge > 0:
                aim = direct  # hitscan: no lead; the beam owns the torso while charging
                full = s.get("charge", 0.75)
                fire[i] = not (charge >= full and clear and self._err(actual, direct) <= tol)
                thp = target.get("hp")
                if LETHAL and fire[i] and thp is not None and charge >= s.get("min_charge", 0.15) and clear \
                        and self._err(actual, direct) <= tol * 0.9:
                    mf_ = s.get("min_frac", 0.35)
                    dmg = s.get("damage", 315) * (mf_ + (1 - mf_) * min(1.0, charge / full)) * self.cube_mult(obs)
                    if "mortar" in (target.get("weapons") or []):
                        dmg *= 1 + s.get("cookoff", 0.6)
                    if dmg * 0.8 >= thp:
                        fire[i] = False  # release now: this partial charge already kills
            else:
                fire[i] = clear and dist <= s.get("range", 280) and w.get("cooldown", 0) <= self.dt
        for i, w in self._slots(obs, "lightning"):
            s = self._stats(w)
            half = math.radians(s.get("cone_deg", 30)) / 2
            fire[i] = (dist <= s.get("range", 45) and clear and me.get("energy", 0) >= s.get("energy", 3) + 2
                       and w.get("cooldown", 0) <= self.dt and self._err(actual, direct) <= half * 0.8)
        return {"aim": aim, "fire": fire, "reload": reload}

    def _mortar(self, tube_z, p, tp, tv, s, r0, clear):
        """([yaw, pitch], range) to drop a shell on the target's feet, led by flight time; None if no arc fits.
        Low arc when the line is clear, high arc (lob over walls) when not."""
        v, g = s.get("speed", 72), s.get("gravity", 22)
        t, pitch = 0.0, None
        for _ in range(3):
            gx, gy, gz = tp[0] + tv[0] * t, tp[1] + tv[1] * t, tp[2]  # feet stay on the ground
            dx, dy = gx - p[0], gy - p[1]
            R = math.hypot(dx, dy)
            pitch = 0.0
            for _ in range(2):  # the shell starts r0 out along the aim
                pitch = arc_pitch(R - r0 * math.cos(pitch), gz - tube_z - r0 * math.sin(pitch), v, g, not clear)
                if pitch is None:
                    return None
            t = (R - r0 * math.cos(pitch)) / (v * math.cos(pitch))
        if not self.min_pitch <= pitch <= self.max_pitch:
            return None
        return [math.atan2(dy, dx), pitch], R

    def cube_mult(self, obs):
        me = obs["self"]
        return 1 + self.cpc * min(me.get("cubes") or 0, self.cap)

    def precharge(self, obs: dict) -> list:
        """fire flags that keep a laser charged (ready on sight) without auto-firing: hold while
        charge < charge + hold_s - 0.35 s and the laser is off cooldown."""
        fire = [False, False]
        for i, w in self._slots(obs, "laser"):
            s = self._stats(w)
            if w.get("cooldown", 0) <= 0.05 and w.get("charge", 0) < s.get("charge", 0.75) + s.get("hold_s", 2) - 0.35:
                fire[i] = True
        return fire

    def face(self, obs: dict, yaw: float) -> dict:
        # A laser charge can't be cancelled (protocol §7): any release fires, at min_charge at least,
        # and holding only delays it by hold_s while halving move speed. So face() always lets go (F3 step 2).
        reload = False
        for _, w in self._slots(obs, "gun"):
            if w.get("ammo", 0) <= LOW_AMMO_FRAC * self._stats(w).get("mag", 12) and not w.get("reload"):
                reload = True
        return {"aim": [yaw, 0.0], "fire": [False, False], "reload": reload}
