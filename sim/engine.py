"""mechfight/1 match engine, phase 2: the full rule set of protocol.md.

Movement, aim, HP/regen, rear armor, zone (phase 1) plus all four weapons, weapon loot, crates, cubes, upgrade
offers, supply drops, NPC drones, tree sight blocking and every sound kind.

Pure simulation: no processes, no I/O. `run.py` (and `inproc.py`) drive it. Section numbers refer to protocol.md.
Every balance number comes from hello.config. Readings of ambiguous rules are marked `# assumption:`.
"""
import math
import os
import random
import sys

TAU = 2 * math.pi
KINDS = ("gun", "mortar", "laser", "lightning")
_CANOPY = {}


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


def cyl_dist(p, c, R, z0, z1):
    """Distance from point p to the solid vertical cylinder (0 inside)."""
    h = max(0.0, math.hypot(p[0] - c[0], p[1] - c[1]) - R)
    v = z0 - p[2] if p[2] < z0 else p[2] - z1 if p[2] > z1 else 0.0
    return math.hypot(h, v)


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


def _dir(yaw, pitch):
    cp = math.cos(pitch)
    return (cp * math.cos(yaw), cp * math.sin(yaw), math.sin(pitch))


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


class Weapon:
    """A weapon item: lives in a mech slot or on the ground as a pickup. State travels with it (a dropped gun keeps
    its ammo, §7 Weapon loot). assumption: timers (reload, cooldown) are frozen while it lies on the ground."""
    __slots__ = ("kind", "cooldown", "ammo", "reloading", "charge", "charging", "release", "held")

    def __init__(self, kind, cfg):
        self.kind = kind
        self.cooldown = 0.0
        self.ammo = int(cfg["weapons"]["gun"]["mag"]) if kind == "gun" else 0
        self.reloading = 0.0
        self.charge = 0.0
        self.charging = False
        self.release = False
        self.held = 0.0

    def reset_charge(self):
        self.charge, self.charging, self.release, self.held = 0.0, False, False, 0.0


class Thing:
    """Crate, cube, pickup, NPC or supply drop: anything with an id and a position."""

    def __init__(self, kind, tid, pos, **kw):
        self.kind, self.id, self.pos = kind, tid, list(pos)
        self.__dict__.update(kw)


class Mech:
    kind = "mech"

    def __init__(self, mid, pos, aim_yaw, cfg):
        mc = cfg["mech"]
        self.id = mid
        self.pos = list(pos)
        self.vel = [0.0, 0.0, 0.0]
        self.aim = [aim_yaw, 0.0]
        self.aim_cmd = [aim_yaw, 0.0]
        self.hp = self.max_hp = float(mc["hp"])
        self.energy = self.max_energy = float(mc["energy"])
        self.st = dict(mc)
        self.wst = {k: dict(cfg["weapons"][k]) for k in KINDS}
        self.grounded = True
        self.alive = True
        self.move, self.boost, self.jump, self.fire, self.reload_req = [0.0, 0.0], False, False, [False, False], False
        self.take = self.drop = self.pick = None
        self.slots = [Weapon("gun", cfg), None]
        self.cubes = 0
        self.upg = {}
        self.upgrades = []
        self.offer = None
        self.offers_pending = 0
        self.offer_seq = 0
        self.short_until = -1e9
        self.last_answer_t = 0.0
        self.last_spend_t = -1e9
        self.last_combat_t = -1e9
        self.step_t = 0.0
        self.jet_t = 0.0
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
        self.dmg_dealt_by = {}
        self.dmg_taken_by = {}
        self.drops_captured = 0
        self.kinds_taken = []
        self.npc_kills = self.crates_broken = 0
        self.cubes_final = None
        self.weapons_final = None

    # phase 1 compatibility
    @property
    def ammo(self):
        g = self.weapon("gun")
        return g.ammo if g else 0

    @property
    def cooldown(self):
        g = self.weapon("gun")
        return g.cooldown if g else 0.0

    @property
    def reloading(self):
        g = self.weapon("gun")
        return g.reloading if g else 0.0

    def weapon(self, kind):
        for w in self.slots:
            if w is not None and w.kind == kind:
                return w
        return None

    def held_kinds(self):
        return [w.kind for w in self.slots if w is not None]

    @property
    def charging(self):
        w = self.weapon("laser")
        return bool(w and w.charging)


class Match:
    def __init__(self, cfg, world, seed, n=None):
        self.cfg, self.world = cfg, world
        self.rng = random.Random(seed)
        m = cfg["match"]
        self.dt = 1.0 / m["tick_hz"]
        self.tick = 0
        self.zone = Zone(cfg["zone"], self.rng, world.bounds, m["arena_margin"])
        self.mechs = [Mech(i, p, math.atan2(cfg["zone"]["start_center"][1] - p[1], cfg["zone"]["start_center"][0] - p[0]), cfg)
                      for i, p in enumerate(self.spawns(n or m["mechs"]))]
        self.upgrade_defs = {u["id"]: u for u in cfg.get("upgrades", [])}
        self.canopy = self._canopy(world) if cfg["vision"].get("canopy_blocks", True) else None
        self.projectiles = []
        self.sounds = []  # (t, kind, x, y, src)
        self.beams = []  # (t, by, kind, path)
        self.next_proj = 1
        self.alive_before = {}
        self.hp_at_3 = None  # {id: hp/max_hp} when alive first drops to <= 3
        self.hp_at_415 = None  # {id: hp/max_hp} of survivors at 415 s
        self.over = False
        self._ids = {"crate": 1000, "cube": 5000, "pickup": 8000, "drop": 20000, "npc": 100}
        self.crates, self.cubes, self.pickups, self.npcs, self.drops = {}, {}, {}, {}, []
        self.drop_times = sorted(cfg.get("drops", {}).get("times", []))
        self._spawn_loot()
        for mm in self.mechs:
            self._restat(mm)

    # ---- setup ----

    @staticmethod
    def _canopy(world):
        c = getattr(world, "canopy", "auto")
        if c != "auto":
            return c
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "arena")
        if path not in _CANOPY:
            here = os.path.dirname(os.path.abspath(__file__))
            if here not in sys.path:
                sys.path.insert(0, here)
            from trees import load
            _CANOPY[path] = load(path)
        return _CANOPY[path]

    @property
    def t(self):
        return self.tick * self.dt

    @property
    def bullets(self):  # phase 1 name
        return self.projectiles

    def alive(self):
        return [m for m in self.mechs if m.alive]

    def _nid(self, kind):
        self._ids[kind] += 1
        return self._ids[kind] - 1

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

    def _spot(self, roof, cx, cy, rmax, clear=1.0, tries=400):
        """Random point inside the circle and the arena: open ground (nothing overhead, `clear` m free around it) or
        a roof (the highest surface is a prism top >= 3 m above the ground). Falls back to ground if no roof fits."""
        w, b, margin = self.world, self.world.bounds, self.cfg["match"]["arena_margin"]
        for k in range(tries * (2 if roof else 1)):
            a, d = self.rng.uniform(0, TAU), rmax * math.sqrt(self.rng.random())
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if not (b[0] + margin <= x <= b[2] - margin and b[1] + margin <= y <= b[3] - margin):
                continue
            g = w.ground(x, y)
            top = w.top(x, y, 1e4)
            if roof:
                # assumption: roof loot sits on any prism top >= 3 m above the street whose surface has room
                if top < g + 3 or w.blocked(x, y, top, clear, 2.0, 0.3):
                    continue
                return (x, y, top)
            if top > g + 0.01 or w.blocked(x, y, g, clear, 3.0, 0.5):
                continue
            return (x, y, g)
        if roof:
            return self._spot(False, cx, cy, rmax, clear, tries)
        return (cx, cy, w.ground(cx, cy))

    def _rand_kind(self, weights):
        ks = [k for k in KINDS if weights.get(k, 0) > 0]
        return self.rng.choices(ks, [weights[k] for k in ks])[0]

    def _spawn_loot(self):
        cfg = self.cfg
        z = cfg["zone"]
        cx, cy = z["start_center"]
        R = z["start_radius"]
        lc, cc, nc = cfg["loot"], cfg["crates"], cfg["npc"]
        # assumption: floor loot, crates and NPC homes are uniform over the start circle ∩ arena
        n_roof = round(lc["floor_count"] * lc["floor_roof_fraction"])
        for i in range(lc["floor_count"]):
            self._add_pickup(Weapon(self._rand_kind(lc["weights"]), cfg), self._spot(i < n_roof, cx, cy, R))
        n_roof = round(cc["count"] * cc["roof_fraction"])
        for i in range(cc["count"]):
            cid = self._nid("crate")
            self.crates[cid] = Thing("crate", cid, self._spot(i < n_roof, cx, cy, R, cc["radius"]), hp=float(cc["hp"]))
        for _ in range(nc["count"]):
            nid = self._nid("npc")
            home = self._spot(False, cx, cy, R, nc["radius"] + 0.5)
            self.npcs[nid] = Thing("npc", nid, home, home=list(home), vel=[0.0, 0.0, 0.0], aim=[0.0, 0.0],
                                   hp=float(nc["hp"]), max_hp=float(nc["hp"]), target=None, mode="wander",
                                   goal=None, goal_t=0.0, cooldown=0.0, alive=True)

    def _add_pickup(self, w, pos):
        pid = self._nid("pickup")
        self.pickups[pid] = Thing("pickup", pid, pos, w=w)
        return pid

    def _scatter(self, x, y, z, n, r=2.5):
        """Positions for n items dropped around (x, y, z), each on the surface below it."""
        out = []
        for _ in range(n):
            a, d = self.rng.uniform(0, TAU), self.rng.uniform(0.0, r)
            px, py = x + d * math.cos(a), y + d * math.sin(a)
            if self.world.solid(px, py, z + 0.5):
                px, py = x, y
            out.append((px, py, self.world.top(px, py, z + 1.5)))
        return out

    def _add_cubes(self, x, y, z, n):
        for p in self._scatter(x, y, z, n):
            cid = self._nid("cube")
            self.cubes[cid] = Thing("cube", cid, p)

    # ---- stats, cubes, upgrades (§10) ----

    def _restat(self, m, heal=True):
        cfg = self.cfg
        st = dict(cfg["mech"])
        wst = {k: dict(cfg["weapons"][k]) for k in KINDS}
        for uid, n in m.upg.items():
            for e in self.upgrade_defs[uid]["effects"]:
                parts = e["path"].split(".")
                d = st if parts[0] == "mech" else wst.get(parts[1]) if parts[0] == "weapons" else None
                key = parts[-1]
                if d is None or key not in d:
                    continue
                for _ in range(n):
                    if "mul" in e:
                        d[key] *= e["mul"]
                    if "add" in e:
                        d[key] += e["add"]
        cc = cfg["cubes"]
        s = 1 + cc["size_per_cube"] * m.cubes
        for k in ("radius", "height", "eye_height", "muzzle_height"):
            st[k] = st[k] * s
        old = m.max_hp
        m.max_hp = st["hp"] * (1 + cc["hp_per_cube"] * min(m.cubes, cc["stat_cap"]))
        if heal and m.max_hp > old:
            m.hp += m.max_hp - old  # §10 heal the difference; assumption: plating heals its difference too
        m.hp = min(m.hp, m.max_hp)
        m.max_energy = st["energy"]
        m.energy = min(m.energy, m.max_energy)  # assumption: capacitor raises the cap, does not fill it
        m.st, m.wst = st, wst

    def dmg_scale(self, m):
        cc = self.cfg["cubes"]
        return 1 + cc["damage_per_cube"] * min(m.cubes, cc["stat_cap"])

    def _gain_cube(self, m, n=1):
        th = self.cfg["cubes"]["upgrade_thresholds"]
        for _ in range(n):
            m.cubes += 1
            if m.cubes in th:
                m.offers_pending += 1
        self._restat(m)
        if m.offer is None and m.offers_pending > 0:
            self._draw_offer(m)

    def _draw_offer(self, m):
        held = set(m.held_kinds())
        ok = [u for u in self.cfg.get("upgrades", []) if m.upg.get(u["id"], 0) < u["max"]
              and (not u.get("requires") or u["requires"] in held)]
        m.offers_pending -= 1
        if not ok:
            return  # assumption: nothing left to take -> the offer is skipped
        m.offer_seq += 1  # assumption: offer ids count per mech from 1
        ch = self.rng.sample(ok, min(3, len(ok)))
        m.offer = {"id": m.offer_seq, "expires": round(self.t + self.cfg["bot"]["offer_timeout_s"], 2),
                   "choices": [{"id": u["id"], "name": u["name"], "desc": u["desc"]} for u in ch]}

    def _apply_upgrade(self, m, i):
        uid = m.offer["choices"][i]["id"]
        m.offer = None
        m.upg[uid] = m.upg.get(uid, 0) + 1
        m.upgrades.append(uid)
        self._restat(m)  # assumption: a bigger magazine (gun_mag) fills on the next reload
        m.events.append({"type": "upgrade", "id": uid})

    # ---- actions (§6, §2 timing) ----

    def apply_action(self, m, a):
        """a: parsed action dict for this decision, or None when the answer was missing or late."""
        t = self.t
        m.take = m.drop = m.pick = None
        if a is None:
            m.fire, m.jump, m.reload_req = [False, False], False, False  # coast: keep move/boost/aim, drop one-shots
            if t - m.last_answer_t > self.cfg["bot"]["coast_s"]:
                m.move, m.boost, m.aim_cmd = [0.0, 0.0], False, list(m.aim)  # idle
            return
        m.last_answer_t = t
        m.move = _vec(a.get("move"), 2) or [0.0, 0.0]
        m.boost = a.get("boost") is True
        m.jump = a.get("jump") is True
        m.aim_cmd = _vec(a.get("aim"), 2) or m.aim_cmd
        f = a.get("fire")
        m.fire = [isinstance(f, list) and len(f) > i and f[i] is True for i in (0, 1)]
        m.reload_req = a.get("reload") is True
        m.pick = _int(a.get("pick"), 0, 2)
        m.take = _int(a.get("take"), 0, 1 << 31)
        m.drop = _int(a.get("drop"), 0, 1)

    # ---- simulation ----

    def step(self):
        """One sim tick."""
        dt, t = self.dt, self.t
        al = self.alive()
        self._one_shots(al, t)
        for m in al:
            self._offers(m, t)
            self._aim(m, m.st, dt)
            self._move(m, m.st, dt, t)
            self._weapons(m, t)
        self._push_apart(al)
        self._projectiles(t)
        self._npcs(t)
        self._pickup_cubes()
        self._supply(t)
        cx, cy, r, dps = self.zone.circle(t)
        for m in self.alive():
            m.ticks_alive += 1
            m.in_zone = math.hypot(m.pos[0] - cx, m.pos[1] - cy) <= r
            if not m.in_zone:
                m.ticks_out += 1
                if m.id not in getattr(self, "zone_immune", ()):  # track squad bots never die to the zone (user rule)
                    self._hurt(m, dps * dt, "zone", None, None, t)
            elif t - m.last_combat_t >= m.st["regen_delay"] and m.hp > 0:
                m.hp = min(m.max_hp, m.hp + m.st["regen_per_s"] * dt)
        self._deaths()
        if self.hp_at_415 is None and t >= 415:
            self.hp_at_415 = {m.id: m.hp / m.max_hp for m in self.alive()}
        self.tick += 1
        if self.t >= self.cfg["match"]["duration_s"] - 1e-9:
            self.over = True
            for m in self.alive():
                m.cubes_final, m.weapons_final = m.cubes, m.held_kinds()

    def _one_shots(self, al, t):
        """pick, take/drop (closest wins a contested pickup), reload: applied on the first tick of a decision."""
        reqs = []
        for m in al:
            if m.pick is not None and m.offer is not None and m.pick < len(m.offer["choices"]):
                self._apply_upgrade(m, m.pick)
            m.pick = None
            if m.reload_req:
                g = m.weapon("gun")
                if g and g.reloading == 0 and g.ammo < m.wst["gun"]["mag"]:
                    g.reloading = m.wst["gun"]["reload"]
                    self.sounds.append((t, "reload", m.pos[0], m.pos[1], m.id))
                m.reload_req = False
            if m.take is not None:
                p = self.pickups.get(m.take)
                d = math.hypot(p.pos[0] - m.pos[0], p.pos[1] - m.pos[1]) if p else 1e9
                reqs.append((d, m.id, m, m.take, m.drop))
            elif m.drop is not None:
                w = m.slots[m.drop]
                if w is not None and not w.charging:  # §7 can't drop a charging laser
                    m.slots[m.drop] = None
                    self._drop_weapon(m, w, m.drop)
            m.take = m.drop = None
        lc = self.cfg["loot"]
        for d, _, m, pid, drop in sorted(reqs, key=lambda r: (r[0], r[1])):
            p = self.pickups.get(pid)

            def fail(reason):
                m.events.append({"type": "take_failed", "id": pid, "reason": reason})
            if p is None:
                fail("gone")
                continue
            if d > lc["pickup_radius"] or abs(p.pos[2] - m.pos[2]) > 4.0:
                fail("range")
                continue
            kind = p.w.kind
            # assumption: the weapon in the slot being replaced does not count for `have`
            if any(w is not None and w.kind == kind and i != drop for i, w in enumerate(m.slots)):
                fail("have")
                continue
            if drop is None:
                slot = 0 if m.slots[0] is None else 1 if m.slots[1] is None else None
                if slot is None:
                    fail("full")
                    continue
            else:
                slot = drop
            old = m.slots[slot]
            if old is not None and old.charging:
                fail("busy")
                continue
            del self.pickups[pid]
            if old is not None:
                m.slots[slot] = None
                self._drop_weapon(m, old, slot)
            w = p.w
            w.reset_charge()
            w.cooldown = max(w.cooldown, lc["equip_s"], m.wst[kind]["cooldown"])
            m.slots[slot] = w
            m.kinds_taken.append(kind)
            m.events.append({"type": "took", "id": pid, "kind": kind, "slot": slot})

    def _drop_weapon(self, m, w, slot):
        w.reset_charge()
        pid = self._add_pickup(w, m.pos)
        m.events.append({"type": "dropped", "id": pid, "kind": w.kind, "slot": slot})

    def _offers(self, m, t):
        if m.offer is not None and t >= m.offer["expires"] - 1e-9:
            self._apply_upgrade(m, 0)
        if m.offer is None and m.offers_pending > 0:
            self._draw_offer(m)

    def _aim(self, m, st, dt):
        dy = wrap(m.aim_cmd[0] - m.aim[0])
        s = st["turn_rate"] * dt
        m.aim[0] = wrap(m.aim[0] + max(-s, min(s, dy)))
        pc = max(st["min_pitch"], min(st["max_pitch"], m.aim_cmd[1]))
        s = st["pitch_rate"] * dt
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
        spent = jetting = False
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
                spent = jetting = True
        if m.charging:
            speed *= mc["charge_move_mult"]  # §7 laser: half speed while charging
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
            # shortcut: terrain steeper than step_up per tick is a wall; max_slope_deg not modelled
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
            if floor >= z - step and vz <= 0:  # step up / follow slopes down
                z = floor
                vz = 0.0
            else:
                m.grounded = False  # walked off a ledge (or thrown by a blast)
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
            # shortcut: no slide-off (0.6 m/tick) or step-on
            z = max(w.top(nx + r * math.cos(k * TAU / 8), ny + r * math.sin(k * TAU / 8), max(z0, z) + 0.01) for k in range(8))
            vz, m.grounded = 0.0, True
        m.vel = [vx, vy, vz]
        m.pos = [nx, ny, z]
        # §8 steps / boost / jet sounds
        sc = self.cfg["sound"]
        if m.grounded and math.hypot(vx, vy) > sc["step_speed"]:
            m.step_t += dt
            if m.step_t >= sc["step_every"]:
                m.step_t -= sc["step_every"]
                self.sounds.append((t, "boost" if boosting and moving else "step", nx, ny, m.id))
        else:
            m.step_t = 0.0
        if jetting:
            # assumption: a jet sound every step_every while jetting (the first on the first tick)
            if m.jet_t <= 0:
                self.sounds.append((t, "jet", nx, ny, m.id))
                m.jet_t = sc["step_every"]
            m.jet_t -= dt
        else:
            m.jet_t = 0.0

    def _push_apart(self, al):
        for i, a in enumerate(al):
            for b in al[i + 1:]:
                r2 = a.st["radius"] + b.st["radius"]
                dx, dy = b.pos[0] - a.pos[0], b.pos[1] - a.pos[1]
                if abs(dx) >= r2 or abs(dy) >= r2:
                    continue
                d = math.hypot(dx, dy)
                if d >= r2 or abs(a.pos[2] - b.pos[2]) >= max(a.st["height"], b.st["height"]):
                    continue
                if d < 1e-6:
                    dx, dy, d = 1.0, 0.0, 1.0
                push = (r2 - d) / 2
                ux, uy = dx / d * push, dy / d * push
                for m, s in ((a, -1), (b, 1)):
                    px, py = m.pos[0] + s * ux, m.pos[1] + s * uy
                    if not self.world.blocked(px, py, m.pos[2], m.st["radius"], m.st["height"], m.st["step_up"]):
                        m.pos[0], m.pos[1] = px, py

    # ---- weapons (§7) ----

    def _ray(self, a, b):
        """Fraction of a->b that is clear of buildings/terrain (1.0 = clear), by bisection on los (~0.3 m)."""
        los = self.world.los
        if los(a, b):
            return 1.0
        lo, hi = 0.0, 1.0
        L = math.dist(a, b)
        while (hi - lo) * L > 0.25:
            mid = (lo + hi) / 2
            if los(a, (a[0] + (b[0] - a[0]) * mid, a[1] + (b[1] - a[1]) * mid, a[2] + (b[2] - a[2]) * mid)):
                lo = mid
            else:
                hi = mid
        return lo

    def _barrel(self, m, h, d):
        """§5 shot origin: radius + 0.5 out along the aim from the muzzle at height h, less if a wall is closer.
        Returns (muzzle, origin, clear)."""
        mz = (m.pos[0], m.pos[1], m.pos[2] + h)
        off = m.st["radius"] + 0.5
        end = (mz[0] + d[0] * off, mz[1] + d[1] * off, mz[2] + d[2] * off)
        f = self._ray(mz, end)
        if f >= 1.0:
            return mz, end, True
        return mz, (mz[0] + d[0] * off * f, mz[1] + d[1] * off * f, mz[2] + d[2] * off * f), False

    def _weapons(self, m, t):
        dt = self.dt
        for i, w in enumerate(m.slots):
            if w is None:
                continue
            f = m.fire[i]
            if w.kind == "gun":
                self._gun(m, w, f, t)
            elif w.kind == "laser":
                self._laser(m, w, f, t)
            else:
                w.cooldown = _tick_cd(w.cooldown, dt, f)
                if f and w.cooldown <= 1e-9:
                    if w.kind == "mortar":
                        w.cooldown += m.wst["mortar"]["cooldown"]
                        self._mortar(m, t)
                    else:
                        ws = m.wst["lightning"]
                        if m.energy >= ws["energy"]:  # assumption: no shot without the energy for it
                            w.cooldown += ws["cooldown"]
                            m.energy -= ws["energy"]
                            m.last_spend_t = t
                            self._lightning(m, t)
                        else:
                            w.cooldown = 0.0

    def _gun(self, m, w, fire, t):
        g = m.wst["gun"]
        dt = self.dt
        if w.reloading > 0:
            w.reloading -= dt
            if w.reloading <= 1e-9:
                w.reloading, w.ammo = 0.0, int(g["mag"])
        w.cooldown = _tick_cd(w.cooldown, dt, fire)
        if not (fire and w.reloading == 0 and w.ammo > 0 and w.cooldown <= 1e-9):
            return
        w.cooldown += g["cooldown"]
        w.ammo -= 1
        if w.ammo == 0:
            w.reloading = g["reload"]
        sp = math.radians(g["spread_deg"])
        d = _dir(m.aim[0] + self.rng.gauss(0, sp), m.aim[1] + self.rng.gauss(0, sp))
        _, origin, clear = self._barrel(m, m.st["muzzle_height"], d)
        self.sounds.append((t, "gun", m.pos[0], m.pos[1], m.id))
        if not clear:
            return  # the barrel pokes into a wall: the shot stops there
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
        self._spawn_proj("gun", m, origin, (d[0] * g["speed"], d[1] * g["speed"], d[2] * g["speed"]),
                         g["damage"] * self.dmg_scale(m), left=float(g["range"]), mid=tgt)

    def _spawn_proj(self, kind, by, pos, vel, dmg, **kw):
        p = {"id": self.next_proj, "kind": kind, "by": by, "pos": tuple(pos), "vel": tuple(vel), "dmg": dmg, "mid": None,
             "left": 1e9, "ttl": 1e9}
        p.update(kw)
        self.next_proj += 1
        self.projectiles.append(p)

    def _laser(self, m, w, fire, t):
        ws = m.wst["laser"]
        dt = self.dt
        w.cooldown = max(0.0, w.cooldown - dt)
        if t < m.short_until:
            w.reset_charge()  # §7 short: no charge for short_s
            return
        if not w.charging:
            if fire and w.cooldown <= 1e-9:
                w.charging, w.charge, w.held, w.release = True, 0.0, 0.0, False
                self.sounds.append((t, "laser_charge", m.pos[0], m.pos[1], m.id))  # assumption: once, when charging starts
            else:
                return
        full = ws["charge"]
        if not fire:
            w.release = True
        if w.release and w.charge >= ws["min_charge"] - 1e-9:
            self._laser_fire(m, w, t)
            return
        # assumption: the charge accrues dt on every tick it is charging, including the first
        w.charge = min(full, w.charge + dt)
        if w.release:
            if w.charge >= ws["min_charge"] - 1e-9:
                self._laser_fire(m, w, t)
            return
        if w.charge >= full - 1e-9:
            w.held += dt
            if w.held > ws["hold_s"] + 1e-9:
                self._laser_fire(m, w, t)

    def _laser_fire(self, m, w, t):
        ws = m.wst["laser"]
        frac = min(1.0, w.charge / ws["charge"]) if ws["charge"] > 0 else 1.0
        # assumption: damage scales linearly from min_frac at 0 charge to 1 at full charge
        dmg = ws["damage"] * (ws["min_frac"] + (1 - ws["min_frac"]) * frac) * self.dmg_scale(m)
        w.reset_charge()
        w.cooldown = ws["cooldown"]
        d = _dir(m.aim[0], m.aim[1])
        mz, origin, clear = self._barrel(m, m.st["muzzle_height"], d)
        self.sounds.append((t, "laser", m.pos[0], m.pos[1], m.id))
        rng_ = ws["range"]
        end = (origin[0] + d[0] * rng_, origin[1] + d[1] * rng_, origin[2] + d[2] * rng_)
        fw = self._ray(origin, end) if clear else 0.0
        hits = []
        for o in self._targets(m):
            r, hgt = self._dims(o)
            s = seg_cyl(origin, end, o.pos, r, o.pos[2], o.pos[2] + hgt)
            if s is not None and s <= fw:
                hits.append((s, o))
        hits.sort(key=lambda h: h[0])
        hits = hits[:1 + int(ws["pierce"])]
        stop = hits[-1][0] if hits and len(hits) > int(ws["pierce"]) else fw
        for s, o in hits:
            eff = None
            mult = 1.0
            if o.kind == "mech" and o.weapon("mortar") is not None:
                mult, eff = 1 + ws["cookoff"], "cookoff"  # §7 cook-off vs a mortar holder
            self._hurt(o, dmg * mult, "laser", origin, m, t, effect=eff)
        p_end = (origin[0] + (end[0] - origin[0]) * stop, origin[1] + (end[1] - origin[1]) * stop,
                 origin[2] + (end[2] - origin[2]) * stop)
        self.beams.append((t, m.id, "laser", [mz, p_end]))

    def _targets(self, m):
        """Everything a shot by m can damage: other live mechs, NPCs, crates."""
        out = [o for o in self.mechs if o.alive and o is not m]
        out += list(self.npcs.values())
        out += list(self.crates.values())
        return out

    def _dims(self, o):
        if o.kind == "mech":
            return o.st["radius"], o.st["height"]
        if o.kind == "npc":
            return self.cfg["npc"]["radius"], self.cfg["npc"]["height"]
        return self.cfg["crates"]["radius"], self.cfg["crates"]["height"]

    def _center(self, o):
        return (o.pos[0], o.pos[1], o.pos[2] + self._dims(o)[1] / 2)

    def _lightning(self, m, t):
        ws = m.wst["lightning"]
        mz = (m.pos[0], m.pos[1], m.pos[2] + m.st["muzzle_height"])
        cone = math.radians(ws["cone_deg"])  # assumption: within cone_deg of the aim yaw on either side
        los = self.world.los
        best, bd = None, ws["range"]
        cands = self._targets(m)
        for o in cands:
            c = self._center(o)
            d = math.dist(mz, c)  # assumption: 3D distance from the muzzle to the target's center
            if d > bd or abs(wrap(math.atan2(c[1] - mz[1], c[0] - mz[0]) - m.aim[0])) > cone:
                continue
            if los(mz, c):
                best, bd = o, d
        self.sounds.append((t, "lightning", m.pos[0], m.pos[1], m.id))
        if best is None:
            d = _dir(m.aim[0], m.aim[1])
            end = (mz[0] + d[0] * ws["range"], mz[1] + d[1] * ws["range"], mz[2] + d[2] * ws["range"])
            f = self._ray(mz, end)
            self.beams.append((t, m.id, "lightning", [mz, tuple(mz[k] + (end[k] - mz[k]) * f for k in range(3))]))
            return
        path = [mz]
        hit = []
        cur, src, dmg = best, mz, ws["damage"] * self.dmg_scale(m)
        for k in range(1 + int(ws["chain"])):
            hit.append(cur)
            c = self._center(cur)
            path.append(c)
            eff = None
            if cur.kind == "mech" and cur.weapon("laser") is not None:
                eff = "short"
                cur.weapon("laser").reset_charge()
                cur.short_until = t + ws["short_s"]
            self._hurt(cur, dmg, "lightning", src, m, t, effect=eff)
            dmg *= ws["chain_falloff"]
            nxt, nd = None, ws["chain_range"]
            for o in cands:
                if o in hit or o.hp <= 0 or (o.kind == "npc" and o.id not in self.npcs)                         or (o.kind == "crate" and o.id not in self.crates):
                    continue
                oc = self._center(o)
                dd = math.dist(c, oc)
                if dd <= nd and los(c, oc):
                    nxt, nd = o, dd
            if nxt is None:
                break
            src, cur = c, nxt
        self.beams.append((t, m.id, "lightning", path))

    def _mortar(self, m, t):
        ws = m.wst["mortar"]
        d = _dir(m.aim[0], m.aim[1])
        _, origin, clear = self._barrel(m, m.st["height"] + 0.5, d)
        self.sounds.append((t, "mortar", m.pos[0], m.pos[1], m.id))
        if not clear:
            self._explode(origin, m, None, t, (d[0], d[1], d[2]))
            return
        self._spawn_proj("mortar", m, origin, (d[0] * ws["speed"], d[1] * ws["speed"], d[2] * ws["speed"]),
                         ws["damage"] * self.dmg_scale(m), ttl=float(ws["ttl"]), splash=ws["splash"] * self.dmg_scale(m),
                         R=ws["splash_radius"], g=ws["gravity"])

    def _explode(self, pt, m, direct, t, vel):
        """Mortar blast at pt by mech m; `direct` took the direct hit. Splash and concussion fall off linearly to
        splash_edge at splash_radius, blocked by walls; own splash x self_damage_mult (§7)."""
        ws = self.cfg["weapons"]["mortar"]
        R = m.wst["mortar"]["splash_radius"]
        sc = self.dmg_scale(m)
        self.sounds.append((t, "explosion", pt[0], pt[1], m.id))
        vl = math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2) or 1.0
        bp = (pt[0] - vel[0] / vl * 0.3, pt[1] - vel[1] / vl * 0.3, pt[2] - vel[2] / vl * 0.3)  # just off the wall
        los = self.world.los
        if direct is not None:
            # assumption: the direct target takes `damage` only (not damage + splash); it is still concussed fully
            self._hurt(direct, ws["damage"] * sc, "mortar", pt, m, t, effect="concuss" if direct.kind == "mech" else None)
            if direct.kind == "mech":
                self._concuss(direct, pt, 1.0, m, vel)
        everyone = [o for o in self.mechs if o.alive] + list(self.npcs.values()) + list(self.crates.values())
        for o in everyone:
            if o is direct:
                continue
            r, h = self._dims(o)
            d = cyl_dist(pt, o.pos, r, o.pos[2], o.pos[2] + h)
            if d > R:
                continue
            c = self._center(o)
            if not (los(bp, c) or los(bp, (o.pos[0], o.pos[1], o.pos[2] + h))):
                continue  # walls block splash
            f = 1 - (1 - ws["splash_edge"]) * (d / R if R > 0 else 0)
            amt = ws["splash"] * sc * f
            if o is m:
                amt *= m.st["self_damage_mult"]
            self._hurt(o, amt, "mortar", pt, m, t, effect="concuss" if o.kind == "mech" and o is not m else None)
            if o.kind == "mech":
                self._concuss(o, pt, f, m, vel)

    def _concuss(self, o, pt, f, by, vel):
        ws = self.cfg["weapons"]["mortar"]
        if not o.alive:
            return
        dx, dy = o.pos[0] - pt[0], o.pos[1] - pt[1]
        d = math.hypot(dx, dy)
        if d < 1e-3:
            dx, dy = vel[0], vel[1]
            d = math.hypot(dx, dy) or 1.0
        o.vel[0] += ws["knock"] * f * dx / d
        o.vel[1] += ws["knock"] * f * dy / d
        o.vel[2] = max(o.vel[2], 0.0) + ws["knock_up"] * f  # assumption: knock_up adds to any upward speed
        o.grounded = False
        o.energy = max(0.0, o.energy - ws["drain"] * f)
        o.events.append({"type": "effect", "effect": "concuss", "by": by.id})

    def _projectiles(self, t):
        dt = self.dt
        cfg = self.cfg
        gr, nr = cfg["projectile"]["gun_radius"], cfg["projectile"]["npc_radius"]
        los = self.world.los
        keep = []
        for p in self.projectiles:
            pos, v = p["pos"], p["vel"]
            kind = p["kind"]
            by = p["by"]
            if kind == "mortar":
                v = (v[0], v[1], v[2] - p["g"] * dt)
                q = (pos[0] + v[0] * dt, pos[1] + v[1] * dt, pos[2] + v[2] * dt)
                p["ttl"] -= dt
            else:
                sp = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
                f = min(1.0, p["left"] / (sp * dt))
                q = (pos[0] + v[0] * dt * f, pos[1] + v[1] * dt * f, pos[2] + v[2] * dt * f)
            pad = nr if kind == "npc" else gr if kind == "gun" else 0.0
            hit, hs = None, 2.0
            cands = [o for o in self.mechs if o.alive and o is not by]  # assumption: never your own shot (shell incl.)
            if kind != "npc":
                cands += [o for o in self.npcs.values() if o is not by]
                cands += list(self.crates.values())
            x0, x1 = min(pos[0], q[0]) - 6, max(pos[0], q[0]) + 6
            y0, y1 = min(pos[1], q[1]) - 6, max(pos[1], q[1]) + 6
            for o in cands:
                ox, oy = o.pos[0], o.pos[1]
                if ox < x0 or ox > x1 or oy < y0 or oy > y1:
                    continue
                r, h = self._dims(o)
                s = seg_cyl(pos, q, o.pos, r + pad, o.pos[2] - pad, o.pos[2] + h + pad)
                if s is not None and s < hs:
                    hit, hs = o, s
            wall = los(pos, q) is False
            if wall:
                ws_ = self._ray(pos, q)
                if hit is not None and hs > ws_:
                    hit = None
                if hit is None:
                    hs = ws_
            if hit is not None or wall:
                hp_ = (pos[0] + (q[0] - pos[0]) * hs, pos[1] + (q[1] - pos[1]) * hs, pos[2] + (q[2] - pos[2]) * hs)
                if kind == "mortar":
                    self._explode(hp_, by, hit, t, v)
                elif hit is not None:
                    if kind == "gun" and hit.kind == "mech" and p["mid"] == hit.id:
                        by.hits_mid += 1
                    self._hurt(hit, p["dmg"], "npc" if kind == "npc" else "gun", None, by, t,
                               bearing=math.atan2(-v[1], -v[0]))
                continue
            if kind == "mortar":
                if p["ttl"] <= 0:
                    self._explode(q, by, None, t, v)  # assumption: a shell explodes where its ttl runs out
                    continue
            else:
                p["left"] -= math.dist(pos, q)
                if p["left"] <= 1e-6:
                    continue
            p["pos"], p["vel"] = q, v
            keep.append(p)
        self.projectiles = keep

    def _hurt(self, o, amount, weapon, src, by, t, effect=None, bearing=None):
        """Apply weapon/zone damage to a mech, NPC or crate. src: point the damage came from (or pass bearing)."""
        if o.kind != "mech":
            self._hurt_thing(o, amount, weapon, by, t, effect)
            return
        m = o
        if not m.alive:
            return
        ev = {"type": "damaged", "amount": 0, "weapon": weapon, "bearing": None, "by": None}
        if by is not None:
            if bearing is None:
                bearing = math.atan2(src[1] - m.pos[1], src[0] - m.pos[0])
            rear = is_rear(bearing, m.aim[0], m.st["front_arc_deg"])
            amount *= (m.st["rear_mult"] if rear else 1.0) * max(0.0, 1 - m.st["armor"])
            ev.update(bearing=round(bearing, 3), by=by.id)
            if rear:
                ev["rear"] = True
                m.dmg_rear += amount
            if by is not m and by.kind == "mech":
                hit = {"type": "hit", "target": m.id, "amount": round(amount, 2), "weapon": weapon}
                if effect:
                    hit["effect"] = effect
                if rear:
                    hit["rear"] = True
                by.events.append(hit)
                by.dmg_dealt_by[weapon] = by.dmg_dealt_by.get(weapon, 0.0) + amount
                by.last_combat_t = t
            if effect in ("cookoff", "short"):
                m.events.append({"type": "effect", "effect": effect, "by": by.id})  # concuss: see _concuss
            m.dmg_taken += amount
        ev["amount"] = round(amount, 2)
        m.events.append(ev)
        m.dmg_taken_by[weapon] = m.dmg_taken_by.get(weapon, 0.0) + amount
        m.last_combat_t = t
        if m.hp - amount <= 0 and m.death_cause is None:
            m.death_cause, m.hp_before_death = weapon, round(m.hp, 1)
            m.killed_by = by.id if by is not None else None
            m.death_pos = _r(m.pos)
            if by is not None and by is not m and by.kind == "mech":
                by.kills += 1
                by.events.append({"type": "kill", "target": m.id})
        m.hp -= amount

    def _hurt_thing(self, o, amount, weapon, by, t, effect):
        live = self.npcs if o.kind == "npc" else self.crates
        if o.id not in live:
            return
        if by is not None and by.kind == "mech":
            # assumption: no rear armor or armor on NPCs and crates; damaging them resets your regen timer
            hit = {"type": "hit", "target": o.id, "amount": round(amount, 2), "weapon": weapon}
            if effect:
                hit["effect"] = effect
            by.events.append(hit)
            by.dmg_dealt_by[weapon] = by.dmg_dealt_by.get(weapon, 0.0) + amount
            by.last_combat_t = t
            if o.kind == "npc":
                o.target = by  # §7 NPCs shoot at whoever attacks them
                o.mode = "chase"
        elif by is not None:
            return  # assumption: NPC bullets do not hurt crates or NPCs
        o.hp -= amount
        if o.hp > 0:
            return
        del live[o.id]
        if o.kind == "npc":
            o.alive = False
            self._add_cubes(o.pos[0], o.pos[1], o.pos[2], int(self.cfg["npc"]["cubes"]))
            if by is not None and by.kind == "mech":
                by.npc_kills += 1
        else:
            self.sounds.append((t, "crate", o.pos[0], o.pos[1], None))  # assumption: the crate sound is its breaking
            self._add_cubes(o.pos[0], o.pos[1], o.pos[2], int(self.cfg["crates"]["cubes"]))
            if self.rng.random() < self.cfg["loot"]["crate_weapon_chance"]:
                p = self._scatter(o.pos[0], o.pos[1], o.pos[2], 1, 1.0)[0]
                self._add_pickup(Weapon(self._rand_kind(self.cfg["loot"]["weights"]), self.cfg), p)
            if by is not None and by.kind == "mech":
                by.crates_broken += 1

    # ---- NPC drones (§7) ----

    def _npcs(self, t):
        nc = self.cfg["npc"]
        dt = self.dt
        w = self.world
        los = w.los
        for n in list(self.npcs.values()):
            hx, hy = n.home[0], n.home[1]
            dh = math.hypot(n.pos[0] - hx, n.pos[1] - hy)
            eye = (n.pos[0], n.pos[1], n.pos[2] + nc["height"] * 0.8)
            tg = n.target
            if tg is not None and (not tg.alive or math.dist(tg.pos[:2], n.pos[:2]) > nc["deaggro_range"]
                                   or dh > nc["chase_leash"]):
                n.target, tg, n.mode = None, None, "return"
            if tg is None and n.mode != "return" and dh <= nc["leash"]:
                best, bd = None, nc["aggro_range"]
                for m in self.mechs:
                    if not m.alive:
                        continue
                    dx, dy = m.pos[0] - n.pos[0], m.pos[1] - n.pos[1]
                    if abs(dx) > bd or abs(dy) > bd:
                        continue
                    d = math.hypot(dx, dy)
                    if d <= bd and los(eye, (m.pos[0], m.pos[1], m.pos[2] + m.st["height"] / 2)):
                        best, bd = m, d
                if best is not None:
                    n.target, tg, n.mode = best, best, "chase"
            # movement goal
            if tg is not None:
                d = math.dist(tg.pos[:2], n.pos[:2])
                # assumption: drones close to 20 m and hold there
                goal = (tg.pos[0], tg.pos[1]) if d > 20 else None
            elif n.mode == "return":
                goal = (hx, hy)
                if dh < nc["leash"] * 0.5:
                    n.mode = "wander"
            else:
                if n.goal is None or t >= n.goal_t or math.dist(n.goal, n.pos[:2]) < 1.5:
                    a, r = self.rng.uniform(0, TAU), nc["leash"] * math.sqrt(self.rng.random())
                    n.goal, n.goal_t = (hx + r * math.cos(a), hy + r * math.sin(a)), t + 8.0
                goal = n.goal
            vx = vy = 0.0
            if goal is not None:
                dx, dy = goal[0] - n.pos[0], goal[1] - n.pos[1]
                d = math.hypot(dx, dy)
                if d > 0.2:
                    sp = nc["speed"] * (0.5 if tg is None and n.mode == "wander" else 1.0)  # assumption: amble when wandering
                    vx, vy = dx / d * sp, dy / d * sp
                    nx, ny = n.pos[0] + vx * dt, n.pos[1] + vy * dt
                    z = n.pos[2]
                    if w.blocked(nx, ny, z, nc["radius"], nc["height"], 1.2) or w.ground(nx, ny) > z + 1.2:
                        n.goal = None
                        vx = vy = 0.0
                    else:
                        n.pos = [nx, ny, w.top(nx, ny, z + 1.2)]
            n.vel = [vx, vy, 0.0]
            n.cooldown = max(0.0, n.cooldown - dt)
            if tg is not None:
                c = (tg.pos[0], tg.pos[1], tg.pos[2] + tg.st["height"] / 2)
                dx, dy, dz = c[0] - eye[0], c[1] - eye[1], c[2] - eye[2]
                n.aim = [math.atan2(dy, dx), math.atan2(dz, math.hypot(dx, dy))]
                if n.cooldown <= 1e-9 and math.hypot(dx, dy) <= nc["deaggro_range"] and los(eye, c):
                    n.cooldown = nc["cooldown"]
                    sp = math.radians(nc["spread_deg"])
                    d = _dir(n.aim[0] + self.rng.gauss(0, sp), n.aim[1] + self.rng.gauss(0, sp))
                    off = nc["radius"] + 0.5
                    o = (eye[0] + d[0] * off, eye[1] + d[1] * off, eye[2] + d[2] * off)
                    v = nc["projectile_speed"]
                    # assumption: aimed at the target's center without lead; bullets fly deaggro_range * 1.5
                    self._spawn_proj("npc", n, o, (d[0] * v, d[1] * v, d[2] * v), nc["damage"],
                                     left=nc["deaggro_range"] * 1.5)
                    self.sounds.append((t, "npc_gun", n.pos[0], n.pos[1], n.id))
            elif vx or vy:
                n.aim = [math.atan2(vy, vx), 0.0]

    # ---- cubes, supply drops ----

    def _pickup_cubes(self):
        if not self.cubes:
            return
        R = self.cfg["cubes"]["pickup_radius"]
        al = self.alive()
        for cid, c in list(self.cubes.items()):
            best, bd = None, R
            for m in al:
                dx, dy = m.pos[0] - c.pos[0], m.pos[1] - c.pos[1]
                if abs(dx) > R or abs(dy) > R or abs(m.pos[2] - c.pos[2]) > 4.0:
                    continue
                d = math.hypot(dx, dy)
                if d < bd or (d == bd and best is not None and m.id < best.id):
                    best, bd = m, d
            if best is not None:
                del self.cubes[cid]
                self._gain_cube(best)
                best.events.append({"type": "pickup", "cubes": best.cubes})

    def _supply(self, t):
        dc = self.cfg.get("drops")
        if not dc:
            return
        while self.drop_times and t >= self.drop_times[0] - 1e-9:
            self.drop_times.pop(0)
            _, _, _, _, _, nc, nr, _ = self.zone.phase(t)
            # assumption: lands uniformly within drops.spread x the radius of the circle the zone is closing to
            pos = self._spot(False, nc[0], nc[1], max(1.0, nr * dc.get("spread", 1.0)), 3.0)
            did = self._nid("drop")
            self.drops.append(Thing("drop", did, pos, land_t=t + dc["fall_s"], holder=None, progress=0.0, landed=False))
        dt = self.dt
        for d in list(self.drops):
            if t < d.land_t - 1e-9:
                continue
            if not d.landed:
                d.landed = True
                self.sounds.append((t, "drop", d.pos[0], d.pos[1], None))
            inside = [m for m in self.alive() if math.hypot(m.pos[0] - d.pos[0], m.pos[1] - d.pos[1]) <= dc["radius"]
                      and abs(m.pos[2] - d.pos[2]) <= m.st["height"]]  # assumption: vertical reach = mech height
            if not inside:
                d.holder, d.progress = None, 0.0
            elif len(inside) == 1:
                m = inside[0]
                if d.holder is not m.id:
                    d.holder, d.progress = m.id, 0.0
                d.progress += dt
                if d.progress >= dc["capture_s"] - 1e-9:
                    self.drops.remove(d)
                    self._gain_cube(m, int(dc["cubes"]))
                    if dc.get("repair", 1):
                        m.hp = m.max_hp
                    m.energy = m.max_energy
                    m.drops_captured += 1
                    m.events.append({"type": "drop", "id": d.id, "cubes": m.cubes})
            # two or more inside: the clock freezes

    # ---- deaths ----

    def _deaths(self):
        dead = [m for m in self.alive() if m.hp <= 0]
        if not dead:
            return
        n = len(self.alive())
        for m in dead:
            m.alive, m.death_tick, m.hp = False, self.tick, 0.0
            m.cubes_final, m.weapons_final = m.cubes, m.held_kinds()
            self.alive_before[m.id] = n
            self.sounds.append((self.t, "death", m.pos[0], m.pos[1], m.id))
            # §7 dead mechs drop every weapon except the gun, §10 and all their cubes plus death_drop_extra
            for w in m.slots:
                if w is not None and w.kind != "gun" and self.cfg["loot"].get("death_drop", 1):
                    w.reset_charge()
                    self._add_pickup(w, self._scatter(m.pos[0], m.pos[1], m.pos[2], 1, 1.5)[0])
            m.slots = [None, None]
            self._add_cubes(m.pos[0], m.pos[1], m.pos[2], m.cubes + int(self.cfg["cubes"]["death_drop_extra"]))
            for nn in self.npcs.values():
                if nn.target is m:
                    nn.target, nn.mode = None, "return"
        left = self.alive()
        if self.hp_at_3 is None and len(left) <= 3:
            self.hp_at_3 = {m.id: m.hp / m.max_hp for m in left}
        if len(left) <= 1:
            self.over = True
            for m in left:
                m.cubes_final, m.weapons_final = m.cubes, m.held_kinds()

    def places(self):
        return placements({m.id: m.death_tick for m in self.mechs}, {m.id: m.hp for m in self.mechs}, self.alive_before)

    # ---- observations (§6, §8) ----

    def observe(self, m):
        cfg, t = self.cfg, self.t
        vc, sc, st = cfg["vision"], cfg["sound"], m.st
        eye = (m.pos[0], m.pos[1], m.pos[2] + st["eye_height"])
        near, rng_ = vc["near_range"] + st["near_range_bonus"], vc["range"] + st["vision_bonus"]
        half = math.radians(vc["fov_deg"]) / 2
        aimy = m.aim[0]
        los = self.world.los
        canopy = self.canopy
        near2, rng2 = near * near, rng_ * rng_

        def sees(c, top=None):
            """§8: in near range (buildings block, canopy not) or in the fov wedge within range (trees block too).
            assumption: inside near range trunks don't block either; trees use the same test for beams/items."""
            dx, dy, dz = c[0] - eye[0], c[1] - eye[1], c[2] - eye[2]
            d2 = dx * dx + dy * dy + dz * dz
            if d2 > rng2:
                return False
            close = d2 <= near2
            if not close and abs(wrap(math.atan2(dy, dx) - aimy)) > half:
                return False
            for p in (c, top) if top is not None else (c,):
                if los(eye, p) and (close or canopy is None or not canopy.blocks(eye, p)):
                    return True
            return False

        mechs = []
        for o in self.mechs:
            if o is m or not o.alive:
                continue
            h = o.st["height"]
            if sees((o.pos[0], o.pos[1], o.pos[2] + h / 2), (o.pos[0], o.pos[1], o.pos[2] + h)):
                m.seen[o.id] = t
            if t - m.seen.get(o.id, -1e9) <= vc["memory_s"]:
                e = {"id": o.id, "kind": "mech", "pos": _r(o.pos), "vel": _r(o.vel), "aim": _r(o.aim, 3)}
                if vc["show_enemy_hp"]:
                    e["hp"] = round(o.hp, 1)
                e.update(max_hp=round(o.max_hp, 2), cubes=o.cubes, weapons=o.held_kinds(), charging=o.charging)
                mechs.append(e)
        nh = cfg["npc"]["height"]
        for n in self.npcs.values():
            if sees((n.pos[0], n.pos[1], n.pos[2] + nh / 2), (n.pos[0], n.pos[1], n.pos[2] + nh)):
                m.seen[n.id] = t
            if t - m.seen.get(n.id, -1e9) <= vc["memory_s"]:
                e = {"id": n.id, "kind": "npc", "pos": _r(n.pos), "vel": _r(n.vel), "aim": _r(n.aim, 3)}
                if vc["show_enemy_hp"]:
                    e["hp"] = round(n.hp, 1)
                e["max_hp"] = n.max_hp
                mechs.append(e)
        projectiles = [{"id": p["id"], "kind": p["kind"], "pos": _r(p["pos"]), "vel": _r(p["vel"])}
                       for p in self.projectiles if p["by"] is not m and sees(p["pos"])]
        ch = cfg["crates"]["height"]
        crates = [{"id": c.id, "pos": _r(c.pos), "hp": round(c.hp, 1)} for c in self.crates.values()
                  if sees((c.pos[0], c.pos[1], c.pos[2] + ch / 2), (c.pos[0], c.pos[1], c.pos[2] + ch))]
        # assumption: cubes and pickups are seen at their position or 0.6 m above it
        cubes = [{"id": c.id, "pos": _r(c.pos)} for c in self.cubes.values()
                 if sees((c.pos[0], c.pos[1], c.pos[2] + 0.3), (c.pos[0], c.pos[1], c.pos[2] + 0.6))]
        pickups = [{"id": p.id, "kind": p.w.kind, "pos": _r(p.pos)} for p in self.pickups.values()
                   if sees((p.pos[0], p.pos[1], p.pos[2] + 0.3), (p.pos[0], p.pos[1], p.pos[2] + 0.6))]
        win = cfg["match"]["decide_every"] * self.dt + 1e-9
        beams = []
        for bt, by, kind, path in self.beams:
            if by == m.id or t - bt > win:
                continue
            a, b = path[0], path[-1]
            mid = tuple((a[k] + b[k]) / 2 for k in range(3))
            if sees(a) or sees(b) or sees(mid) or any(sees(p) for p in path[1:-1]):
                beams.append({"by": by, "kind": kind, "path": [_r(p) for p in path], "age": round(t - bt, 2)})
        sounds = []
        sigma = math.radians(sc["bearing_noise_deg"] * st["hearing"])
        for s_t, kind, x, y, src in self.sounds:
            if src == m.id or t - s_t > win:
                continue
            d = math.hypot(x - m.pos[0], y - m.pos[1])
            if d > sc["range"][kind]:
                continue
            sounds.append({"kind": kind, "bearing": round(wrap(math.atan2(y - m.pos[1], x - m.pos[0]) + self.rng.gauss(0, sigma)), 3),
                           "dist": "near" if d < sc["near"] else "mid" if d < sc["mid"] else "far", "age": round(t - s_t, 2)})
        dc = cfg.get("drops", {})
        drops = [{"id": d.id, "pos": _r(d.pos), "radius": dc["radius"], "lands_in": round(max(0.0, d.land_t - t), 2),
                  "capture_s": dc["capture_s"], "progress": round(d.progress, 2), "holder": d.holder} for d in self.drops]
        events, m.events = m.events, []
        weapons = []
        for w in m.slots:
            if w is None:
                weapons.append(None)
                continue
            e = {"kind": w.kind, "cooldown": round(max(0.0, w.cooldown), 3)}
            if w.kind == "gun":
                e.update(ammo=w.ammo, reload=round(max(0.0, w.reloading), 3))
            elif w.kind == "laser":
                e["charge"] = round(w.charge, 3)
            e["stats"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in m.wst[w.kind].items()}
            weapons.append(e)
        return {
            "type": "obs", "tick": self.tick, "t": round(t, 2), "alive": len(self.alive()),
            "self": {"id": m.id, "pos": _r(m.pos), "vel": _r(m.vel), "aim": _r(m.aim, 3), "hp": round(m.hp, 2),
                     "max_hp": round(m.max_hp, 2), "energy": round(m.energy, 1), "max_energy": round(m.max_energy, 2),
                     "grounded": m.grounded, "cubes": m.cubes, "upgrades": list(m.upgrades), "in_zone": m.in_zone,
                     "weapons": weapons,
                     "stats": {k: round(v, 4) if isinstance(v, float) else v for k, v in st.items()}},
            "mechs": mechs, "projectiles": projectiles, "crates": crates, "cubes": cubes, "pickups": pickups,
            "sounds": sounds, "beams": beams, "events": events, "drops": drops, "zone": self.zone.obs(t),
            "offer": None if m.offer is None else {"id": m.offer["id"], "choices": [dict(c) for c in m.offer["choices"]],
                                                   "expires": m.offer["expires"]},
        }

    def prune_sounds(self):
        keep = self.cfg["match"]["decide_every"] * self.dt + 1e-9
        self.sounds = [s for s in self.sounds if self.t - s[0] <= keep]
        self.beams = [b for b in self.beams if self.t - b[0] <= keep]


def _tick_cd(cd, dt, held):
    """Count a cooldown down one tick. While the trigger is held the overshoot below 0 (less than one tick) is kept
    so the next shot comes exactly `cooldown` after the last on average (§7 gun: "held down, exactly that rate");
    a weapon that was already ready banks nothing (phase 1 banked a tick: first interval 0.2 s instead of 0.24 s)."""
    if cd > 0:
        cd -= dt
        return cd if held else max(cd, 0.0)
    return 0.0


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


def _int(v, lo, hi):
    """An integer field from a bot in [lo, hi], else None (bools and floats with a fraction are rejected)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return v if isinstance(v, int) and lo <= v <= hi else None
