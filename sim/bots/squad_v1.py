"""Opponent model of the track's house bots (sim only, never shipped).

Track page: "15 house bots (4 easy, 4 medium, 4 hard, 3 expert) acting as one squad: they share vision,
never fight each other, and hunt you weakest first (one early, more as you thin them out, all of them late)."

Model (guesses where the page is silent, marked):
- Squad membership: every mech running this file in the same match (registry keyed by the shared config dict).
  Enemies = every other mech.
- Tiers by squad order: 4 easy, 4 medium, 4 hard, 3 expert. Tier sets aim noise, lead, reaction time,
  strafing, and weapon pickups.
- Shared vision: what any member sees of an enemy is known to all (position, velocity, time).
- Hunters: the weakest alive members, count = 1 + squad deaths, plus more over time (guess: +1 at 150 s,
  +2 at 240 s), all at HUNT_ALL_T. Hunters walk to the enemy's last known position and attack.
- Non-hunters roam/hold inside the next circle; they shoot an enemy they can see within DEFEND_RANGE (guess).
"""
import math
import random

import mechfight as mf

TIERS = ["easy"] * 4 + ["medium"] * 4 + ["hard"] * 4 + ["expert"] * 3
# aim noise (rad), lead factor, reaction (s), strafe, wants laser, crate/NPC farming
TIER = {
    "easy": (0.060, 0.0, 0.8, False, False, False),
    "medium": (0.030, 0.6, 0.5, False, True, True),
    "hard": (0.015, 0.9, 0.3, True, True, True),
    "expert": (0.008, 1.0, 0.2, True, True, True),
}
HUNT_ALL_T = 300.0       # guess: "all of them late"
DEFEND_RANGE = 60.0     # guess: non-hunters shoot visible enemies this close
ZONE_SMART = True        # user directive: house bots stay inside the next circle and regen before the end
ZONE_MARGIN = 15.0
RETALIATE_S = 10.0      # a member hit by an enemy hunts it this long (track: house bots shoot back)
PREF = ["plating", "gun_damage", "laser_damage", "gun_rate", "armor", "laser_charge", "nanites", "gun_velocity"]
_REG = {}


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def intercept(d, v, s, r0):
    a = v[0] ** 2 + v[1] ** 2 + v[2] ** 2 - s * s
    b = 2 * (d[0] * v[0] + d[1] * v[1] + d[2] * v[2] - r0 * s)
    c = d[0] ** 2 + d[1] ** 2 + d[2] ** 2 - r0 * r0
    disc = b * b - 4 * a * c
    if abs(a) < 1e-9 or disc < 0:
        return 0.0
    q = math.sqrt(disc)
    ts = [t for t in ((-b - q) / (2 * a), (-b + q) / (2 * a)) if t > 0]
    return min(ts) if ts else 0.0


class Bot:
    name = "squad"

    def __init__(self, hello):
        self.cfg = hello["config"]
        self.slot = hello["slot"]
        key = id(self.cfg)
        reg = _REG.get(key)
        if reg is None or self.slot in reg["members"]:
            reg = _REG[key] = {"members": [], "seen": {}, "alive": {}, "dead": set()}
            for k in list(_REG):
                if k != key:
                    del _REG[k]
        self.reg = reg
        reg["members"].append(self.slot)
        self.tier = TIERS[min(len(reg["members"]) - 1, len(TIERS) - 1)]
        self.noise, self.lead_k, self.react, self.strafes, self.wants_laser, self.farms = TIER[self.tier]
        self.rank = list(TIER).index(self.tier) * 100 + len(reg["members"])
        reg["alive"][self.slot] = (self.rank, 0.0)
        self.rng = random.Random(hello.get("seed", 0))
        self.goal, self.goal_for = None, None
        self.strafe, self.strafe_t = 1, 0.0
        self.first_seen = {}
        self.aim_err = 0.0
        self.last_pos, self.stuck_t = None, 0.0
        self.hit_t = -1e9

    def _hunters(self, t):
        reg = self.reg
        alive = sorted((v[0], s) for s, v in reg["alive"].items() if t - v[1] < 1.0)
        dead = len(reg["members"]) - len(alive)
        n = 1 + dead + (1 if t > 150 else 0) + (2 if t > 240 else 0)
        if t >= HUNT_ALL_T:
            n = len(alive)
        hit = t - self.hit_t < RETALIATE_S
        return {s for _, s in alive[:n]} | ({self.slot} if hit else set())

    def pick_goal(self, z):
        nc, nr = z["next_center"], z["next_radius"]
        r = max(0.0, nr - 15) * math.sqrt(self.rng.random())
        a = self.rng.uniform(0, 2 * math.pi)
        return [nc[0] + r * math.cos(a), nc[1] + r * math.sin(a)]

    def act(self, obs):
        me, z, t = obs["self"], obs["zone"], obs["t"]
        x, y, zz = me["pos"]
        reg = self.reg
        reg["alive"][self.slot] = (self.rank, t)
        members = set(reg["members"])
        act = {}
        if obs.get("offer"):
            ch = obs["offer"]["choices"]
            act["pick"] = min(range(len(ch)), key=lambda i: PREF.index(ch[i]["id"]) if ch[i]["id"] in PREF else 99)
        ws = me.get("weapons") or [None, None]
        kinds = [w and w["kind"] for w in ws]
        for e in obs.get("events") or []:
            if e.get("type") == "damaged" and e.get("by") is not None and e["by"] < 100 and e["by"] not in members:
                self.hit_t = t
                if e["by"] not in reg["seen"] and e.get("bearing") is not None:  # shared guess: 80 m along the bearing
                    reg["seen"][e["by"]] = {"t": t, "pos": [x + 80 * math.cos(e["bearing"]), y + 80 * math.sin(e["bearing"]), zz], "vel": [0, 0, 0], "hp": None}
        # shared vision
        for m in obs.get("mechs") or []:
            if m.get("kind") == "mech" and m["id"] not in members:
                reg["seen"][m["id"]] = {"t": t, "pos": m["pos"], "vel": m.get("vel") or [0, 0, 0], "hp": m.get("hp")}
                self.first_seen.setdefault(m["id"], t)
        for i in list(self.first_seen):
            if not any(m["id"] == i for m in obs.get("mechs") or []):
                del self.first_seen[i]
        hunting = self.slot in self._hunters(t)
        key = (tuple(z["next_center"]), z["next_radius"])
        if self.goal_for != key or self.goal is None:
            self.goal_for, self.goal = key, self.pick_goal(z)
        visible = [m for m in obs.get("mechs") or [] if m.get("kind") == "mech" and m["id"] not in members]
        visible.sort(key=lambda m: math.dist(m["pos"], me["pos"]))
        known = [(i, s) for i, s in reg["seen"].items() if t - s["t"] < 30]
        goal = self.goal
        tgt = visible[0] if visible else None
        if tgt is not None and not hunting and math.dist(tgt["pos"], me["pos"]) > DEFEND_RANGE:
            tgt = None
        if ZONE_SMART and not hunting and z["next_radius"] <= 25 and me.get("hp", 0) < (me.get("stats") or self.cfg["mech"]).get("hp", 1400):
            tgt = None  # regen to full before the final burn
        if hunting and known:
            i, s = min(known, key=lambda kv: math.dist(kv[1]["pos"][:2], (x, y)))
            age = t - s["t"]
            v = s["vel"]
            goal = [s["pos"][0] + v[0] * min(age, 3), s["pos"][1] + v[1] * min(age, 3)]
        elif tgt is None:
            # loot on the way
            for p in obs.get("pickups") or []:
                if self.wants_laser and p["kind"] == "laser" and "laser" not in kinds and math.dist(p["pos"][:2], (x, y)) < 60:
                    goal = p["pos"][:2]
                    if math.dist(p["pos"][:2], (x, y)) < self.cfg["loot"]["pickup_radius"] - 0.5:
                        act["take"] = p["id"]
                        if ws[0] and ws[1]:
                            act["drop"] = 1 if ws[0]["kind"] == "gun" else 0
                    break
            cubes = obs.get("cubes") or []
            if cubes:
                c = min(cubes, key=lambda c: math.dist(c["pos"][:2], (x, y)))
                if math.dist(c["pos"][:2], (x, y)) < 50:
                    goal = c["pos"][:2]
        nc, nrm = z["next_center"], max(0.0, z["next_radius"] - ZONE_MARGIN)
        if ZONE_SMART and math.dist(goal[:2], nc) > nrm:  # clamp the goal into the next circle
            gd = math.dist(goal[:2], nc)
            goal = [nc[0] + (goal[0] - nc[0]) * nrm / gd, nc[1] + (goal[1] - nc[1]) * nrm / gd]
        if not me.get("in_zone", True):
            goal = z["next_center"]
        dx, dy = goal[0] - x, goal[1] - y
        d = math.hypot(dx, dy)
        mv = [dx / d, dy / d] if d > 3 else [0.0, 0.0]
        aim = [math.atan2(dy, dx) if d > 3 else me["aim"][0] + 0.5, 0.0]
        fire = [False, False]
        shoot = tgt
        npcs = [m for m in obs.get("mechs") or [] if m.get("kind") == "npc"]
        if shoot is None and self.farms and not hunting:
            crates = [c for c in obs.get("crates") or [] if math.dist(c["pos"], me["pos"]) < 50]
            if crates:
                c = crates[0]
                shoot = {"pos": c["pos"], "vel": [0, 0, 0], "h": 1.2}
        if shoot is None:
            hit_npc = [e.get("by") for e in obs.get("events") or [] if e.get("type") == "damaged" and (e.get("by") or 0) >= 100]
            if hit_npc:
                n = next((m for m in npcs if m["id"] in hit_npc), None)
                if n:
                    shoot = dict(n, h=1.75)
        if shoot is not None:
            st = me.get("stats") or self.cfg["mech"]
            tp = shoot["pos"]
            h = shoot.get("h", 4.5)
            mz = zz + st.get("muzzle_height", 7)
            dvec = [tp[0] - x, tp[1] - y, tp[2] + h - mz]
            dist = math.sqrt(sum(c * c for c in dvec))
            v = shoot.get("vel") or [0, 0, 0]
            gun = next((w for w in ws if w and w["kind"] == "gun"), None)
            gs = (gun.get("stats") or {}).get("speed", 252) if gun else 252
            tt = intercept(dvec, v, gs, 3.0) * self.lead_k
            charging = any(w and w["kind"] == "laser" and w.get("charge", 0) > 0 for w in ws)
            use = dvec if charging else [dvec[0] + v[0] * tt, dvec[1] + v[1] * tt, dvec[2] + v[2] * tt]
            self.aim_err = 0.8 * self.aim_err + 0.2 * self.rng.gauss(0, self.noise * 2.2)
            aim = [math.atan2(use[1], use[0]) + self.aim_err, math.atan2(use[2], math.hypot(use[0], use[1]))]
            err = abs(wrap(aim[0] - me["aim"][0]))
            ready = "id" not in shoot or t - self.first_seen.get(shoot["id"], t) >= self.react or shoot.get("kind") != "mech"
            for i, w in enumerate(ws):
                if not w or not ready:
                    continue
                k = w["kind"]
                if k == "gun":
                    fire[i] = dist < 230 and err < 0.06 and w.get("ammo", 0) > 0
                elif k == "laser":
                    ch = w.get("charge", 0)
                    full = (w.get("stats") or {}).get("charge", 0.75)
                    fire[i] = (not (ch >= full and err < 0.04)) if ch > 0 else (dist < 280 and w.get("cooldown", 0) <= 0.1)
                elif k == "lightning":
                    fire[i] = dist < 45 and err < 0.25 and me.get("energy", 0) > 10
            if shoot.get("kind") == "mech":
                b = math.atan2(dvec[1], dvec[0])
                if self.strafes:
                    if t - self.strafe_t > self.rng.uniform(0.6, 1.6):
                        self.strafe, self.strafe_t = -self.strafe, t
                    px, py = -math.sin(b) * self.strafe, math.cos(b) * self.strafe
                else:
                    px = py = 0.0
                fwd = 0.7 if (hunting and dist > 60) else (-0.3 if dist < 30 else 0.0)
                if me.get("in_zone", True):
                    mv = [px + fwd * math.cos(b), py + fwd * math.sin(b)]
            if gun and gun.get("ammo", 1) == 0:
                act["reload"] = True
        if ZONE_SMART and math.dist((x, y), nc) > nrm + 5:  # never let fighting pull us out of the next circle
            d = math.dist((x, y), nc)
            mv = [(nc[0] - x) / d, (nc[1] - y) / d]
        jump = False
        if self.last_pos and math.dist(self.last_pos, (x, y)) < 0.3 and (mv[0] or mv[1]):
            self.stuck_t += 0.1
        else:
            self.stuck_t = 0.0
        self.last_pos = (x, y)
        boost = (not me.get("in_zone", True)) or (self.stuck_t > 0.5 and not me.get("grounded", True))
        if self.stuck_t > 0.5 and me.get("grounded", True):
            jump = True
        if self.stuck_t > 3:
            self.goal = self.pick_goal(z)
            self.stuck_t = 0.0
        act.update(move=mv, aim=aim, fire=fire, boost=boost, jump=jump)
        return act


if __name__ not in ("squad", "squad_v1"):
    mf.run(Bot)
