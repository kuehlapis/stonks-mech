"""mechfight/1 match engine, phase 1: movement, aim, HP/regen, rear armor, zone, gun, vision, sounds.

Pure simulation: no processes, no I/O. `run.py` drives it with real bot processes.
Rules: protocol.md (section numbers in comments). Every number comes from hello.config.
"""
import math
import random

TAU = 2 * math.pi


def wrap(a):
    return (a + math.pi) % TAU - math.pi


def is_rear(bearing, aim_yaw, front_arc_deg):
    """§7 Rear armor: hit from outside the front arc centered on the aim yaw. `bearing` points at the source."""
    return abs(wrap(bearing - aim_yaw)) > math.radians(front_arc_deg) / 2


def seg_cyl(p, q, c, R, z0, z1):
    """Fraction s in [0, 1] where segment p->q first enters the vertical cylinder (axis at c, radius R,
    z0 <= z <= z1), or None."""
    dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
    fx, fy = p[0] - c[0], p[1] - c[1]
    a = dx * dx + dy * dy
    cc = fx * fx + fy * fy - R * R
    if a < 1e-12:
        if cc > 0:
            return None
        lo, hi = 0.0, 1.0
    else:
        b = 2 * (fx * dx + fy * dy)
        disc = b * b - 4 * a * cc
        if disc < 0:
            return None
        sq = math.sqrt(disc)
        lo, hi = (-b - sq) / (2 * a), (-b + sq) / (2 * a)
    if abs(dz) < 1e-12:
        if not z0 <= p[2] <= z1:
            return None
    else:
        s2, s3 = (z0 - p[2]) / dz, (z1 - p[2]) / dz
        if s2 > s3:
            s2, s3 = s3, s2
        lo, hi = max(lo, s2), min(hi, s3)
    lo, hi = max(lo, 0.0), min(hi, 1.0)
    return lo if lo <= hi else None


def placements(death_ticks, hps, alive_before):
    """§4. death_ticks[i] is the tick mech i died (None = survivor). alive_before[i]: mechs alive just before
    its death tick, which is its place (same-tick deaths share it). Survivors are ranked by HP, equal HP shares."""
    place = {}
    for i, dt in death_ticks.items():
        if dt is not None:
            place[i] = alive_before[i]
    surv = [i for i, dt in death_ticks.items() if dt is None]
    for i in surv:
        place[i] = 1 + sum(1 for j in surv if hps[j] > hps[i])
    return place


class Zone:
    """§9. Phase k holds, then shrinks linearly from its circle to the next one. Next circles are random,
    fully inside the current one, center kept inside the arena."""

    def __init__(self, zcfg, rng, bounds, margin):
        c, r, t0 = list(zcfg["start_center"]), float(zcfg["start_radius"]), 0.0
        self.phases = []
        for p in zcfg["phases"]:
            nr = float(p["radius"])
            for _ in range(200):
                a, d = rng.uniform(0, TAU), (r - nr) * math.sqrt(rng.random())
                nc = [c[0] + d * math.cos(a), c[1] + d * math.sin(a)]
                if bounds[0] + margin <= nc[0] <= bounds[2] - margin and bounds[1] + margin <= nc[1] <= bounds[3] - margin:
                    break
            ts = t0 + p["hold_s"]
            te = ts + p["shrink_s"]
            self.phases.append((t0, ts, te, c, r, nc, nr, p["dps"]))
            c, r, t0 = nc, nr, te

    def phase(self, t):
        for ph in self.phases:
            if t < ph[2]:
                return ph
        return self.phases[-1]

    def circle(self, t):
        """(cx, cy, radius, dps) at time t."""
        _, ts, te, c, r, nc, nr, dps = self.phase(t)
        f = 1.0 if t >= te else max(0.0, (t - ts) / (te - ts)) if te > ts else 0.0
        return c[0] + (nc[0] - c[0]) * f, c[1] + (nc[1] - c[1]) * f, r + (nr - r) * f, dps

    def obs(self, t):
        # assumption: center/radius are the phase's start circle; bots interpolate with shrink_start/end (§9)
        _, ts, te, c, r, nc, nr, dps = self.phase(t)
        return {"center": [round(c[0], 2), round(c[1], 2)], "radius": r, "next_center": [round(nc[0], 2), round(nc[1], 2)],
                "next_radius": nr, "shrink_start": ts, "shrink_end": te, "dps": dps}


class Mech:
    def __init__(self, mid, pos, aim_yaw, cfg):
        mc, g = cfg["mech"], cfg["weapons"]["gun"]
        self.id = mid
        self.pos = list(pos)
        self.vel = [0.0, 0.0, 0.0]
        self.aim = [aim_yaw, 0.0]
        self.aim_cmd = [aim_yaw, 0.0]
        self.hp = self.max_hp = float(mc["hp"])
        self.energy = self.max_energy = float(mc["energy"])
        self.grounded = True
        self.alive = True
        self.move, self.boost, self.jump, self.fire, self.reload_req = [0.0, 0.0], False, False, False, False
        self.last_answer_t = 0.0
        self.cooldown, self.ammo, self.reloading = 0.0, int(g["mag"]), 0.0
        self.last_spend_t = -1e9
        self.last_combat_t = -1e9
        self.step_t = 0.0
        self.events = []
        self.seen = {}
        self.kills = 0
        self.death_tick = None
        self.death_cause = None
        self.killed_by = None
        self.death_pos = None
        self.hp_before_death = None
        self.in_zone = True
        # metrics
        self.ticks_alive = self.ticks_out = 0
        self.dmg_taken = self.dmg_rear = 0.0
        self.shots_mid = self.hits_mid = 0


class Match:
    def __init__(self, cfg, world, seed, n=None):
        self.cfg, self.world = cfg, world
        self.rng = random.Random(seed)
        m, mc = cfg["match"], cfg["mech"]
        self.dt = 1.0 / m["tick_hz"]
        self.tick = 0
        self.zone = Zone(cfg["zone"], self.rng, world.bounds, m["arena_margin"])
        self.mechs = [Mech(i, p, math.atan2(cfg["zone"]["start_center"][1] - p[1], cfg["zone"]["start_center"][0] - p[0]), cfg)
                      for i, p in enumerate(self.spawns(n or m["mechs"]))]
        self.bullets = []
        self.sounds = []  # (t, kind, x, y, src)
        self.next_bullet = 1
        self.alive_before = {}
        self.hp_at_3 = None  # {id: hp/max_hp} when alive first drops to <= 3
        self.hp_at_415 = None  # {id: hp/max_hp} of survivors at 415 s
        self.over = False

    @property
    def t(self):
        return self.tick * self.dt

    def alive(self):
        return [m for m in self.mechs if m.alive]

    def spawns(self, n):
        """Random open ground (no roof or bridge overhead, not in a wall) inside spawn_zone_fraction of the start
        circle, spawn_min_separation apart (relaxed if it can't fit)."""
        w, m, z, mc = self.world, self.cfg["match"], self.cfg["zone"], self.cfg["mech"]
        b, margin = w.bounds, m["arena_margin"]
        sep, rmax = m["spawn_min_separation"], m["spawn_zone_fraction"] * z["start_radius"]
        cx, cy = z["start_center"]
        out = []
        tries = 0
        while len(out) < n:
            tries += 1
            if tries % 3000 == 0:
                sep *= 0.8
            a, d = self.rng.uniform(0, TAU), rmax * math.sqrt(self.rng.random())
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if not (b[0] + margin <= x <= b[2] - margin and b[1] + margin <= y <= b[3] - margin):
                continue
            g = w.ground(x, y)
            if w.top(x, y, 1e4) > g + 0.01 or w.blocked(x, y, g, mc["radius"], mc["height"], mc["step_up"]):
                continue
            if any(math.hypot(x - p[0], y - p[1]) < sep for p in out):
                continue
            out.append((x, y, g))
        return out

    # ---- actions (§6, §2 timing) ----

    def apply_action(self, m, a):
        """a: parsed action dict for this decision, or None when the answer was missing or late."""
        t = self.t
        if a is None:
            m.fire = m.jump = m.reload_req = False  # coast: keep move/boost/aim, drop one-shots
            if t - m.last_answer_t > self.cfg["bot"]["coast_s"]:
                m.move, m.boost, m.aim_cmd = [0.0, 0.0], False, list(m.aim)  # idle
            return
        m.last_answer_t = t
        m.move = _vec(a.get("move"), 2) or [0.0, 0.0]
        m.boost = a.get("boost") is True
        m.jump = a.get("jump") is True
        m.aim_cmd = _vec(a.get("aim"), 2) or m.aim_cmd
        f = a.get("fire")
        m.fire = isinstance(f, list) and len(f) > 0 and f[0] is True
        m.reload_req = a.get("reload") is True

    # ---- simulation ----

    def step(self):
        """One sim tick."""
        dt, t = self.dt, self.t
        mc = self.cfg["mech"]
        for m in self.alive():
            self._aim(m, mc, dt)
            self._move(m, mc, dt, t)
            self._gun(m, t)
        self._push_apart(mc)
        self._bullets(t)
        cx, cy, r, dps = self.zone.circle(t)
        for m in self.alive():
            m.ticks_alive += 1
            m.in_zone = math.hypot(m.pos[0] - cx, m.pos[1] - cy) <= r
            if not m.in_zone:
                m.ticks_out += 1
                self._damage(m, dps * dt, "zone", None, None, t)
            elif t - m.last_combat_t >= mc["regen_delay"] and m.hp > 0:
                m.hp = min(m.max_hp, m.hp + mc["regen_per_s"] * dt)
        self._deaths()
        if self.hp_at_415 is None and t >= 415:
            self.hp_at_415 = {m.id: m.hp / m.max_hp for m in self.alive()}
        self.tick += 1
        if self.t >= self.cfg["match"]["duration_s"] - 1e-9:
            self.over = True

    def _aim(self, m, mc, dt):
        dy = wrap(m.aim_cmd[0] - m.aim[0])
        s = mc["turn_rate"] * dt
        m.aim[0] = wrap(m.aim[0] + max(-s, min(s, dy)))
        pc = max(mc["min_pitch"], min(mc["max_pitch"], m.aim_cmd[1]))
        s = mc["pitch_rate"] * dt
        m.aim[1] += max(-s, min(s, pc - m.aim[1]))

    def _move(self, m, mc, dt, t):
        w = self.world
        r, h, step = mc["radius"], mc["height"], mc["step_up"]
        mx, my = m.move
        L = math.hypot(mx, my)
        if L > 1:
            mx, my = mx / L, my / L
        moving = L > 1e-6
        boosting = m.boost and m.energy > 0
        spent = False
        vx, vy, vz = m.vel
        if m.grounded:
            speed = mc["boost_speed"] if boosting and moving else mc["walk_speed"]
            if boosting and moving:
                m.energy -= mc["boost_drain"] * dt
                spent = True
            acc = mc["ground_accel"]
            if m.jump:
                vz, m.grounded = mc["jump_speed"], False
            m.jump = False  # one-shot
        else:
            speed, acc = mc["walk_speed"], mc["air_accel"]
            if boosting:  # jet (§6 boost in the air)
                vz = min(mc["max_rise_speed"], vz + mc["jet_accel"] * dt)
                m.energy -= mc["jet_drain"] * dt
                spent = True
        ex, ey = mx * speed - vx, my * speed - vy
        e = math.hypot(ex, ey)
        lim = acc * dt
        if e > lim:
            ex, ey = ex * lim / e, ey * lim / e
        vx, vy = vx + ex, vy + ey
        m.energy = max(0.0, m.energy)
        if spent:
            m.last_spend_t = t
        elif t - m.last_spend_t >= mc["energy_regen_delay"]:
            m.energy = min(m.max_energy, m.energy + mc["energy_regen"] * dt)

        x, y, z = m.pos
        b = w.bounds
        st = step if m.grounded else 0.0  # in the air only surfaces below the feet can be passed over

        def bad(px, py):
            # shortcut: terrain steeper than step_up per tick is a wall; max_slope_deg not modelled, phase 2
            return w.blocked(px, py, z, r, h, st) or w.ground(px, py) > z + st

        if vx or vy:
            nx = min(b[2] - r, max(b[0] + r, x + vx * dt))
            ny = min(b[3] - r, max(b[1] + r, y + vy * dt))
            if bad(nx, ny):  # §7 walls: keep the part along the wall
                if not bad(nx, y):
                    ny, vy = y, 0.0
                elif not bad(x, ny):
                    nx, vx = x, 0.0
                else:
                    nx, ny, vx, vy = x, y, 0.0, 0.0
            if nx == b[0] + r or nx == b[2] - r:
                vx = 0.0
            if ny == b[1] + r or ny == b[3] - r:
                vy = 0.0
        else:
            nx, ny = x, y
        if m.grounded:
            floor = w.top(nx, ny, z + step)
            if floor >= z - step:  # step up / follow slopes down
                z = floor
                vz = 0.0
            else:
                m.grounded = False  # walked off a ledge
        if not m.grounded:
            vz -= mc["gravity"] * dt
            nz = z + vz * dt
            if vz > 0 and w.blocked(nx, ny, nz, r, h, 0.0):
                nz, vz = z, 0.0  # head hit an underside
            floor = w.top(nx, ny, z)
            if nz <= floor:
                nz, vz, m.grounded = floor, 0.0, True
            z0, z = z, nz
        else:
            z0 = m.pos[2]
        if vz <= 0 and w.blocked(nx, ny, z, r, h, 0.0):
            # §7 roof edge: part of the footprint is over a surface; stand on its highest point under us.
            # shortcut: no slide-off (0.6 m/tick) or step-on, phase 2
            z = max(w.top(nx + r * math.cos(k * TAU / 8), ny + r * math.sin(k * TAU / 8), max(z0, z) + 0.01) for k in range(8))
            vz, m.grounded = 0.0, True
        m.vel = [vx, vy, vz]
        m.pos = [nx, ny, z]
        # §8 steps
        sc = self.cfg["sound"]
        if m.grounded and math.hypot(vx, vy) > sc["step_speed"]:
            m.step_t += dt
            if m.step_t >= sc["step_every"]:
                m.step_t -= sc["step_every"]
                self.sounds.append((t, "boost" if boosting and moving else "step", nx, ny, m.id))
        else:
            m.step_t = 0.0

    def _push_apart(self, mc):
        r2 = 2 * mc["radius"]
        al = self.alive()
        for i, a in enumerate(al):
            for b in al[i + 1:]:
                dx, dy = b.pos[0] - a.pos[0], b.pos[1] - a.pos[1]
                d = math.hypot(dx, dy)
                if d >= r2 or abs(a.pos[2] - b.pos[2]) >= mc["height"]:
                    continue
                if d < 1e-6:
                    dx, dy, d = 1.0, 0.0, 1.0
                push = (r2 - d) / 2
                ux, uy = dx / d * push, dy / d * push
                for m, s in ((a, -1), (b, 1)):
                    px, py = m.pos[0] + s * ux, m.pos[1] + s * uy
                    if not self.world.blocked(px, py, m.pos[2], mc["radius"], mc["height"], mc["step_up"]):
                        m.pos[0], m.pos[1] = px, py

    def _gun(self, m, t):
        g = self.cfg["weapons"]["gun"]
        mc = self.cfg["mech"]
        dt = self.dt
        if m.reloading > 0:
            m.reloading -= dt
            if m.reloading <= 1e-9:
                m.reloading, m.ammo = 0.0, int(g["mag"])
        if m.reload_req and m.reloading == 0 and m.ammo < g["mag"]:
            m.reloading = g["reload"]
            self.sounds.append((t, "reload", m.pos[0], m.pos[1], m.id))
        m.reload_req = False
        m.cooldown = max(m.cooldown - dt, -dt if m.fire else 0.0)  # held trigger keeps the exact rate
        if not (m.fire and m.reloading == 0 and m.ammo > 0 and m.cooldown <= 1e-9):
            return
        m.cooldown += g["cooldown"]
        m.ammo -= 1
        if m.ammo == 0:
            m.reloading = g["reload"]
        sp = math.radians(g["spread_deg"])
        yaw, pitch = m.aim[0] + self.rng.gauss(0, sp), m.aim[1] + self.rng.gauss(0, sp)
        d = (math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))
        mz = m.pos[2] + mc["muzzle_height"]
        off = mc["radius"] + 0.5
        muzzle = (m.pos[0], m.pos[1], mz)
        origin = (m.pos[0] + d[0] * off, m.pos[1] + d[1] * off, mz + d[2] * off)
        self.sounds.append((t, "gun", m.pos[0], m.pos[1], m.id))
        if not self.world.los(muzzle, origin):
            return  # shortcut: barrel in a wall, the shot is lost (server stops it at the wall)
        # metric: the intended target is the enemy closest to the aim yaw (within 10 deg), 50-150 m away, moving
        tgt, best = None, math.radians(10)
        for o in self.alive():
            if o is m:
                continue
            dx, dy = o.pos[0] - m.pos[0], o.pos[1] - m.pos[1]
            off_yaw = abs(wrap(math.atan2(dy, dx) - m.aim[0]))
            if off_yaw < best and 50 <= math.hypot(dx, dy) <= 150 and math.hypot(o.vel[0], o.vel[1]) > 1:
                tgt, best = o.id, off_yaw
        if tgt is not None:
            m.shots_mid += 1
        self.bullets.append({"id": self.next_bullet, "by": m.id, "pos": origin,
                             "vel": (d[0] * g["speed"], d[1] * g["speed"], d[2] * g["speed"]),
                             "left": float(g["range"]), "dmg": float(g["damage"]), "mid": tgt})
        self.next_bullet += 1

    def _bullets(self, t):
        mc, gr = self.cfg["mech"], self.cfg["projectile"]["gun_radius"]
        keep = []
        for bl in self.bullets:
            p, v = bl["pos"], bl["vel"]
            sp = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
            f = min(1.0, bl["left"] / (sp * self.dt))
            q = (p[0] + v[0] * self.dt * f, p[1] + v[1] * self.dt * f, p[2] + v[2] * self.dt * f)
            hit, hs = None, 2.0
            for o in self.alive():
                if o.id == bl["by"]:
                    continue
                s = seg_cyl(p, q, o.pos, mc["radius"] + gr, o.pos[2] - gr, o.pos[2] + mc["height"] + gr)
                if s is not None and s < hs:
                    hit, hs = o, s
            if hit is not None:
                hp_ = (p[0] + (q[0] - p[0]) * hs, p[1] + (q[1] - p[1]) * hs, p[2] + (q[2] - p[2]) * hs)
                if self.world.los(p, hp_):
                    shooter = self.mechs[bl["by"]]
                    if bl["mid"] == hit.id:
                        shooter.hits_mid += 1
                    self._damage(hit, bl["dmg"], "gun", math.atan2(-v[1], -v[0]), shooter, t)
                continue
            if not self.world.los(p, q):
                continue
            bl["left"] -= sp * self.dt * f
            if bl["left"] <= 1e-6:
                continue
            bl["pos"] = q
            keep.append(bl)
        self.bullets = keep

    def _damage(self, m, amount, weapon, bearing, by, t):
        mc = self.cfg["mech"]
        ev = {"type": "damaged", "amount": 0, "weapon": weapon, "bearing": None, "by": None}
        if by is not None:
            rear = is_rear(bearing, m.aim[0], mc["front_arc_deg"])
            amount *= (mc["rear_mult"] if rear else 1.0) * (1 - mc["armor"])
            ev.update(bearing=round(bearing, 3), by=by.id)
            hit = {"type": "hit", "target": m.id, "amount": round(amount, 2), "weapon": weapon}
            if rear:
                ev["rear"] = hit["rear"] = True
                m.dmg_rear += amount
            m.dmg_taken += amount
            by.events.append(hit)
            by.last_combat_t = t
        ev["amount"] = round(amount, 2)
        m.events.append(ev)
        m.last_combat_t = t
        if m.hp - amount <= 0 and m.death_cause is None:
            m.death_cause, m.hp_before_death = weapon, round(m.hp, 1)
            m.killed_by = by.id if by is not None else None
            m.death_pos = _r(m.pos)
            if by is not None and by is not m:
                by.kills += 1
                by.events.append({"type": "kill", "target": m.id})
        m.hp -= amount

    def _deaths(self):
        dead = [m for m in self.alive() if m.hp <= 0]
        if not dead:
            return
        n = len(self.alive())
        for m in dead:
            m.alive, m.death_tick, m.hp = False, self.tick, 0.0
            self.alive_before[m.id] = n
            self.sounds.append((self.t, "death", m.pos[0], m.pos[1], m.id))
        left = self.alive()
        if self.hp_at_3 is None and len(left) <= 3:
            self.hp_at_3 = {m.id: m.hp / m.max_hp for m in left}
        if len(left) <= 1:
            self.over = True

    def places(self):
        return placements({m.id: m.death_tick for m in self.mechs}, {m.id: m.hp for m in self.mechs}, self.alive_before)

    # ---- observations (§6, §8) ----

    def observe(self, m):
        cfg, t = self.cfg, self.t
        vc, mc, sc = cfg["vision"], cfg["mech"], cfg["sound"]
        eye = (m.pos[0], m.pos[1], m.pos[2] + mc["eye_height"])
        near, rng_ = vc["near_range"] + mc["near_range_bonus"], vc["range"] + mc["vision_bonus"]
        half = math.radians(vc["fov_deg"]) / 2

        def in_view(p):
            dx, dy, dz = p[0] - eye[0], p[1] - eye[1], p[2] - eye[2]
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            return d <= near or (d <= rng_ and abs(wrap(math.atan2(dy, dx) - m.aim[0])) <= half)

        mechs = []
        for o in self.alive():
            if o is m:
                continue
            c = (o.pos[0], o.pos[1], o.pos[2] + mc["height"] / 2)
            # shortcut: trees ignored for sight (canopy/trunks), phase 2
            if in_view(c) and (self.world.los(eye, c) or self.world.los(eye, (o.pos[0], o.pos[1], o.pos[2] + mc["height"]))):
                m.seen[o.id] = t
            if t - m.seen.get(o.id, -1e9) <= vc["memory_s"]:
                mechs.append({"id": o.id, "kind": "mech", "pos": _r(o.pos), "vel": _r(o.vel), "aim": _r(o.aim, 3),
                              "hp": round(o.hp, 1) if vc["show_enemy_hp"] else None, "max_hp": o.max_hp, "cubes": 0,
                              "weapons": ["gun"], "charging": False})
        # shortcut: bullets need no line of sight to be seen, only range/fov
        projectiles = [{"id": b["id"], "kind": "gun", "pos": _r(b["pos"]), "vel": _r(b["vel"])}
                       for b in self.bullets if b["by"] != m.id and in_view(b["pos"])]
        sounds = []
        sigma = math.radians(sc["bearing_noise_deg"] * mc["hearing"])
        for st, kind, x, y, src in self.sounds:
            if src == m.id or t - st > cfg["match"]["decide_every"] * self.dt + 1e-9:
                continue
            d = math.hypot(x - m.pos[0], y - m.pos[1])
            if d > sc["range"][kind]:
                continue
            sounds.append({"kind": kind, "bearing": round(wrap(math.atan2(y - m.pos[1], x - m.pos[0]) + self.rng.gauss(0, sigma)), 3),
                           "dist": "near" if d < sc["near"] else "mid" if d < sc["mid"] else "far", "age": round(t - st, 2)})
        g = cfg["weapons"]["gun"]
        events, m.events = m.events, []
        return {
            "type": "obs", "tick": self.tick, "t": round(t, 2), "alive": len(self.alive()),
            "self": {"id": m.id, "pos": _r(m.pos), "vel": _r(m.vel), "aim": _r(m.aim, 3), "hp": round(m.hp, 1),
                     "max_hp": m.max_hp, "energy": round(m.energy, 1), "max_energy": m.max_energy,
                     "grounded": m.grounded, "cubes": 0, "upgrades": [], "in_zone": m.in_zone,
                     "weapons": [{"kind": "gun", "cooldown": round(max(0.0, m.cooldown), 3), "ammo": m.ammo,
                                  "reload": round(m.reloading, 3), "stats": dict(g)}, None],
                     "stats": dict(mc)},
            "mechs": mechs, "projectiles": projectiles, "crates": [], "cubes": [], "pickups": [],
            "sounds": sounds, "beams": [], "events": events, "drops": [], "zone": self.zone.obs(t), "offer": None,
        }

    def prune_sounds(self):
        keep = self.cfg["match"]["decide_every"] * self.dt + 1e-9
        self.sounds = [s for s in self.sounds if self.t - s[0] <= keep]


def _r(v, n=2):
    return [round(x, n) for x in v]


def _vec(v, n):
    """Validate a list of n finite numbers from a bot (trust boundary); None if bad."""
    if not isinstance(v, list) or len(v) != n:
        return None
    try:
        out = [float(x) for x in v]
    except (TypeError, ValueError):
        return None
    return out if all(math.isfinite(x) for x in out) else None
