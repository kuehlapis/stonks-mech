"""Perception: enemy tracks, unseen attackers, damage and sound bearings (notes/interfaces.md, game-plan §1)."""
import math

COMBAT_SOUNDS = {"gun", "laser", "laser_charge", "lightning", "mortar", "explosion"}
VIRTUAL_DIST = {"laser": 150.0, "gun": 100.0}  # game-plan §1 unseen_attacker
WINDOW = 3.0  # s: engaged, virtual threat life, damage/sound bearing age (game-plan §1)
AIM_TOL = math.radians(15)


def _angle(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


class Perception:
    def __init__(self, cfg, my_id):
        self.my_id = my_id
        self.memory_s = cfg.get("vision", {}).get("memory_s", 5)
        mech = cfg.get("mech", {})
        self.eye = mech.get("eye_height", 8)
        self.height = mech.get("height", 9)
        self.size_per_cube = cfg.get("cubes", {}).get("size_per_cube", 0.05)
        self.tracks = {}       # id -> threat dict
        self.hit_by = {}       # mech id -> t of its latest damaged event on us
        self.damage = None     # (t, bearing) of latest damaged event
        self.sound = None      # (t, bearing) of latest near/mid combat sound
        self.threats = []

    def update(self, obs):
        t = obs["t"]
        me = obs.get("self") or {}
        mp = me.get("pos") or [0.0, 0.0, 0.0]
        seen = set()
        for m in obs.get("mechs") or ():
            i = m.get("id")
            if m.get("kind") != "mech" or i == self.my_id or not isinstance(i, int) or not 0 <= i <= 15:
                continue
            seen.add(i)
            self.tracks[i] = {"id": i, "pos": list(m["pos"]), "vel": list(m.get("vel") or [0.0, 0.0, 0.0]),
                              "weapons": list(m.get("weapons") or []), "hp": m.get("hp"), "max_hp": m.get("max_hp"),
                              "aim": m.get("aim"), "charging": bool(m.get("charging")), "visible": True,
                              "last_seen": t, "virtual": False, "cubes": m.get("cubes", 0)}
        for e in obs.get("events") or ():
            if e.get("type") != "damaged" or e.get("bearing") is None:
                continue
            b = e["bearing"]
            self.damage = (t, b)
            by, w = e.get("by"), e.get("weapon")
            if not isinstance(by, int) or not 0 <= by <= 15:
                continue
            self.hit_by[by] = t
            if by not in seen:
                # shortcut: z is our own feet height (update() has no world), fine for bearing-only use
                d = VIRTUAL_DIST.get(w, 100.0)
                self.tracks[by] = {"id": by, "pos": [mp[0] + d * math.cos(b), mp[1] + d * math.sin(b), mp[2]],
                                   "vel": [0.0, 0.0, 0.0], "weapons": ["mortar"] if w == "mortar" else [w],
                                   "hp": None, "max_hp": None, "aim": None, "charging": False, "visible": False,
                                   "last_seen": t, "virtual": True, "cubes": 0}
        for s in obs.get("sounds") or ():
            if s.get("kind") in COMBAT_SOUNDS and s.get("dist") in ("near", "mid"):
                st = t - s.get("age", 0)
                if self.sound is None or st >= self.sound[0]:
                    self.sound = (st, s["bearing"])
        for i, th in list(self.tracks.items()):
            if i not in seen:
                th["visible"] = False
                if t - th["last_seen"] > (WINDOW if th["virtual"] else self.memory_s):
                    del self.tracks[i]
        self.threats = list(self.tracks.values())

    def engaged_by(self, t):
        best = None
        for i, ht in self.hit_by.items():
            if t - ht <= WINDOW and i in self.tracks and (best is None or ht > self.hit_by[best]):
                best = i
        return self.tracks[best] if best is not None else None

    def threatened_by(self, obs, world):
        me = obs.get("self") or {}
        mp = me.get("pos")
        if not mp:
            return None
        size = 1 + self.size_per_cube * (me.get("cubes") or 0)
        center = [mp[0], mp[1], mp[2] + (me.get("stats") or {}).get("height", self.height * size) / 2]
        found = []
        for th in self.threats:
            if not th["visible"] or not th["aim"]:
                continue
            p = th["pos"]
            if _angle(th["aim"][0], math.atan2(mp[1] - p[1], mp[0] - p[0])) > AIM_TOL:
                continue
            eye = [p[0], p[1], p[2] + self.eye * (1 + self.size_per_cube * (th["cubes"] or 0))]
            if world is not None and not world.los(eye, center):
                continue
            found.append((not th["charging"], (p[0] - mp[0]) ** 2 + (p[1] - mp[1]) ** 2, th["id"], th))
        return min(found)[3] if found else None  # charging first, then nearest

    def damage_bearing(self, t):
        return self.damage[1] if self.damage and t - self.damage[0] <= WINDOW else None

    def sound_bearing(self, t):
        return self.sound[1] if self.sound and t - self.sound[0] <= WINDOW else None
