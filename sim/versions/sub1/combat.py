"""Combat: aim with lead, gun firing discipline, laser charge/release, reloads (interfaces.md "M1 modules")."""
import math

AIM_TOL_FRAC = 0.6  # fire when the actual aim is within 0.6 target radii of the desired aim at the target
MIN_TOL = 0.004  # rad, floor so long shots still fire
LOW_AMMO_FRAC = 0.5  # reload with no target in range at or below this fraction of the mag


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


class Combat:
    def __init__(self, cfg: dict, world) -> None:
        self.world = world
        self.wcfg = cfg.get("weapons", {})
        m = cfg.get("mech", {})
        self.radius = m.get("radius", 2.5)
        self.half_h = m.get("height", 9) / 2
        self.min_pitch = m.get("min_pitch", -0.7)
        self.max_pitch = m.get("max_pitch", 1.3)
        mt = cfg.get("match", {})
        self.dt = mt.get("decide_every", 2) / mt.get("tick_hz", 20)  # the trigger is held this long

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
        tc = [tp[0], tp[1], tp[2] + target.get("center_h", self.half_h * size)]
        tv = target.get("vel") or [0.0, 0.0, 0.0]
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
            lead = self._aim_at([d[k] + tv[k] * t for k in range(3)])
            aim = lead
            in_range = r0 + s.get("speed", 252) * t <= s.get("range", 230)
            ammo = w.get("ammo", 0)
            if ammo <= 0 and not w.get("reload"):
                reload = True
            elif ammo <= LOW_AMMO_FRAC * s.get("mag", 12) and not in_range and not w.get("reload"):
                reload = True
            fire[i] = (in_range and clear and ammo > 0 and not w.get("reload")
                       and w.get("cooldown", 0) <= self.dt and self._err(actual, lead) <= tol)
        for i, w in self._slots(obs, "laser"):
            s = self._stats(w)
            charge = w.get("charge", 0)
            if charge > 0:
                aim = direct  # hitscan: no lead; the beam owns the torso while charging
                fire[i] = not (charge >= s.get("charge", 0.75) and clear and self._err(actual, direct) <= tol)
            else:
                fire[i] = clear and dist <= s.get("range", 280) and w.get("cooldown", 0) <= self.dt
        return {"aim": aim, "fire": fire, "reload": reload}

    def face(self, obs: dict, yaw: float) -> dict:
        # A laser charge can't be cancelled (protocol §7): any release fires, at min_charge at least,
        # and holding only delays it by hold_s while halving move speed. So face() always lets go (F3 step 2).
        reload = False
        for _, w in self._slots(obs, "gun"):
            if w.get("ammo", 0) <= LOW_AMMO_FRAC * self._stats(w).get("mag", 12) and not w.get("reload"):
                reload = True
        return {"aim": [yaw, 0.0], "fire": [False, False], "reload": reload}
