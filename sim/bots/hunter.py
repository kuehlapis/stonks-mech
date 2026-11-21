"""Opponent model of a competent built-in bot (sim only, never shipped).

Styles: subclasses in camper.py / rusher.py set `style`.
- hunter: walks a random route inside the next circle, grabs weapons (laser first) and crates it sees,
  engages any visible mech within 200 m with a led gun, full-charge laser, lightning up close; strafes in fights.
- camper: like hunter but stops at a point inside the next circle and only moves when the zone forces it.
- rusher: walks toward the last heard combat sound or visible enemy and chases.
Upgrades: plating > gun_damage > gun_rate > armor > laser_damage > ...
"""
import math
import os
import random

import mechfight as mf

PREF = ["plating", "laser_damage", "gun_damage", "gun_rate", "armor", "laser_charge", "nanites", "gun_velocity",
        "gun_mag", "servos", "sensors"]
WANT = {"laser": 3, "lightning": 2, "mortar": 1}


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
    style = "hunter"
    name = "hunter"

    def __init__(self, hello):
        self.cfg = hello["config"]
        self.rng = random.Random(hello.get("seed", 0))
        self.goal = None
        self.goal_for = None
        self.strafe = 1
        self.strafe_t = 0.0
        self.last_pos = None
        self.stuck_t = 0.0
        self.sound = None
        self.target = None
        self.lead_k = 0.85 + 0.3 * self.rng.random()  # imperfect lead
        self.aggro = 200.0

    def pick_goal(self, z):
        nc, nr = z["next_center"], z["next_radius"]
        r = max(0.0, nr - 15) * math.sqrt(self.rng.random()) * (0.5 if self.style == "camper" else 1.0)
        a = self.rng.uniform(0, 2 * math.pi)
        return [nc[0] + r * math.cos(a), nc[1] + r * math.sin(a)]

    def act(self, obs):
        me, z, t = obs["self"], obs["zone"], obs["t"]
        x, y, zz = me["pos"]
        act = {}
        if obs.get("offer"):
            ch = obs["offer"]["choices"]
            act["pick"] = min(range(len(ch)), key=lambda i: PREF.index(ch[i]["id"]) if ch[i]["id"] in PREF else 99)
        ws = me.get("weapons") or [None, None]
        kinds = [w and w["kind"] for w in ws]
        # goal management
        key = (tuple(z["next_center"]), z["next_radius"])
        if self.goal_for != key or self.goal is None:
            self.goal_for, self.goal = key, self.pick_goal(z)
        if self.style == "hunter" and math.dist(self.goal, (x, y)) < 6:
            self.goal = self.pick_goal(z)
        for s in obs.get("sounds") or []:
            if s["kind"] in ("gun", "laser", "explosion", "lightning") and s["dist"] != "far":
                self.sound = (t, s["bearing"])
        enemies = [m for m in obs.get("mechs") or [] if m.get("kind") == "mech"]
        npcs = [m for m in obs.get("mechs") or [] if m.get("kind") == "npc"]
        enemies.sort(key=lambda m: math.dist(m["pos"], me["pos"]))
        tgt = enemies[0] if enemies and math.dist(enemies[0]["pos"], me["pos"]) <= self.aggro else None
        goal = self.goal
        # loot: weapons we want, crates
        if tgt is None:
            best = None
            for p in obs.get("pickups") or []:
                v = WANT.get(p["kind"], 0)
                have = max([WANT.get(k, 0) for k in kinds if k] + [0])
                if v > 0 and p["kind"] not in kinds and (ws[1] is None or v > have) and math.dist(p["pos"][:2], (x, y)) < 60:
                    best = p
                    break
            if best:
                goal = best["pos"][:2]
                if math.dist(best["pos"][:2], (x, y)) < self.cfg["loot"]["pickup_radius"] - 0.5:
                    act["take"] = best["id"]
                    if ws[0] and ws[1]:
                        act["drop"] = 1 if ws[0]["kind"] == "gun" else 0
            cubes = obs.get("cubes") or []
            if cubes:
                c = min(cubes, key=lambda c: math.dist(c["pos"][:2], (x, y)))
                if math.dist(c["pos"][:2], (x, y)) < 50:
                    goal = c["pos"][:2]
        if self.style == "rusher" and tgt is None and self.sound and t - self.sound[0] < 4:
            b = self.sound[1]
            goal = [x + 40 * math.cos(b), y + 40 * math.sin(b)]
        if not me.get("in_zone", True):
            goal = z["next_center"]
        dx, dy = goal[0] - x, goal[1] - y
        d = math.hypot(dx, dy)
        mv = [dx / d, dy / d] if d > 2 else [0.0, 0.0]
        if self.style == "camper" and tgt is None and me.get("in_zone", True) and math.dist(self.goal, (x, y)) < 8:
            mv = [0.0, 0.0]
        aim_yaw = math.atan2(dy, dx) if d > 2 else me["aim"][0] + 0.6
        aim = [aim_yaw, 0.0]
        fire = [False, False]
        shoot = tgt
        if shoot is None:
            crates = obs.get("crates") or []
            near = [c for c in crates if math.dist(c["pos"], me["pos"]) < 60]
            if near and not npcs:
                shoot = min(near, key=lambda c: math.dist(c["pos"], me["pos"]))
                shoot = {"pos": shoot["pos"], "vel": [0, 0, 0], "crate": True}
            elif npcs and self.style != "camper" and math.dist(npcs[0]["pos"], me["pos"]) < 110:
                shoot = npcs[0]
        if shoot is not None:
            st = me.get("stats") or self.cfg["mech"]
            tp = shoot["pos"]
            h = 1.2 if shoot.get("crate") else (1.75 if shoot.get("kind") == "npc" else 4.5)
            mz = zz + st.get("muzzle_height", 7)
            dvec = [tp[0] - x, tp[1] - y, tp[2] + h - mz]
            dist = math.sqrt(sum(c * c for c in dvec))
            v = shoot.get("vel") or [0, 0, 0]
            gun = next((w for w in ws if w and w["kind"] == "gun"), None)
            gs = (gun.get("stats") or {}).get("speed", 252) if gun else 252
            tt = intercept(dvec, v, gs, 3.0) * self.lead_k
            lead = [dvec[0] + v[0] * tt, dvec[1] + v[1] * tt, dvec[2] + v[2] * tt]
            laser_charging = any(w and w["kind"] == "laser" and w.get("charge", 0) > 0 for w in ws)
            use = dvec if laser_charging else lead
            aim = [math.atan2(use[1], use[0]), math.atan2(use[2], math.hypot(use[0], use[1]))]
            err = abs(wrap(aim[0] - me["aim"][0]))
            for i, w in enumerate(ws):
                if not w:
                    continue
                k = w["kind"]
                if k == "gun":
                    fire[i] = dist < 230 and err < 0.05 and w.get("ammo", 0) > 0
                elif k == "laser":
                    ch = w.get("charge", 0)
                    full = (w.get("stats") or {}).get("charge", 0.75)
                    if ch > 0:
                        fire[i] = not (ch >= full and err < 0.03)
                    else:
                        fire[i] = dist < 280 and w.get("cooldown", 0) <= 0.1
                elif k == "lightning":
                    fire[i] = dist < 45 and err < 0.25 and me.get("energy", 0) > 10
                elif k == "mortar":
                    if 30 < dist < 220:
                        g, s = 22.0, 72.0
                        hd = math.hypot(dvec[0], dvec[1])
                        disc = s ** 4 - g * (g * hd * hd + 2 * dvec[2] * s * s)
                        if disc >= 0:
                            aim[1] = math.atan2(s * s - math.sqrt(disc), g * hd)
                            fire[i] = err < 0.05 and w.get("cooldown", 0) <= 0.1
            if not shoot.get("crate") and shoot.get("kind") == "mech":
                # strafe in fights; rusher closes in, others keep range
                if t - self.strafe_t > self.rng.uniform(0.6, 1.6):
                    self.strafe, self.strafe_t = -self.strafe, t
                b = math.atan2(dvec[1], dvec[0])
                px, py = -math.sin(b) * self.strafe, math.cos(b) * self.strafe
                fwd = 0.6 if (self.style == "rusher" or dist > 120) else (-0.4 if dist < 50 else 0.0)
                if me.get("in_zone", True):
                    mv = [px + fwd * math.cos(b), py + fwd * math.sin(b)]
            if gun and gun.get("ammo", 1) == 0:
                act["reload"] = True
        elif self.sound and t - self.sound[0] < 3:
            aim = [self.sound[1], 0.0]
        # stuck: jump
        jump = False
        if self.last_pos and math.dist(self.last_pos, (x, y)) < 0.3 and (mv[0] or mv[1]):
            self.stuck_t += 0.1
        else:
            self.stuck_t = 0.0
        self.last_pos = (x, y)
        boost = not me.get("in_zone", True) or (self.stuck_t > 0.5 and not me.get("grounded", True))
        if self.stuck_t > 0.5 and me.get("grounded", True):
            jump = True
        if self.stuck_t > 3:
            self.goal = self.pick_goal(z)
            self.stuck_t = 0.0
        act.update(move=mv, aim=aim, fire=fire, boost=boost, jump=jump)
        return act


if __name__ != "hunter":
    mf.run(Bot)
