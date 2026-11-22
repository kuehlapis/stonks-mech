"""Economy (M1): upgrade picks (game-plan U1) and laser pickups (L1). See notes/interfaces.md."""
import math

# U1 pick order (game-plan §5); "mortar_*" expanded to the three real ids (notes/research/upgrades.md).
ORDER = ["plating", "nanites", "armor", "laser_damage", "sensors", "laser_charge", "servos",
         "gun_damage", "gun_rate", "gun_mag", "gyros", "jets", "reactor", "capacitor", "gun_velocity",
         "lightning_efficiency", "lightning_range", "lightning_chain",
         "mortar_splash", "mortar_reload", "mortar_velocity", "laser_pierce"]
TAKE_MORTAR = False  # A/B switch: also take a mortar into an empty special slot (ranked last)
WANT = ["laser", "lightning"]   # weapon pickups worth taking, best first (the gun is always kept)
# L1 tuning constants (game-plan §5).
ETA_EARLY_S = 15.0       # s: walk this far for a laser before LATE_T
ETA_LATE_S = 10.0       # s: ... and after
LATE_T = 70.0
DETOUR = 1.3            # straight distance × this ≈ walked distance
THREAT_RADIUS = 120.0   # m around the pickup
THREAT_MEMORY_S = 5.0
FAIL_BACKOFF_S = 5.0
CUBE_CAP = 10  # ZS2: past this many cubes, skip cubes (each makes us 5% bigger) unless one completes an upgrade (0 = off)
TAKE_DZ = 4.0           # protocol §6: vertical take reach is fixed, not in config


class Economy:
    def __init__(self, cfg: dict) -> None:
        # Fallback for ids not in ORDER: their order in config.upgrades, then anything unknown last.
        extra = [u.get("id") for u in (cfg.get("upgrades") or []) if u.get("id") not in ORDER]
        self.rank = {u: i for i, u in enumerate(ORDER + extra)}
        self.reach = float((cfg.get("loot") or {}).get("pickup_radius", 4))
        self.thresholds = (cfg.get("cubes") or {}).get("upgrade_thresholds") or []
        self.skip = {}  # pickup id -> t until which we don't try it again

    def cube_ok(self, obs: dict) -> bool:
        """Is one more cube worth picking up?"""
        n = (obs.get("self") or {}).get("cubes", 0) or 0
        return CUBE_CAP <= 0 or n < CUBE_CAP or (n + 1) in self.thresholds

    def pick(self, obs: dict) -> int | None:
        offer = obs.get("offer")
        if not offer or not offer.get("choices"):
            return None
        ch = offer["choices"]
        return min(range(len(ch)), key=lambda i: (self.rank.get(ch[i].get("id"), len(self.rank)), i))

    def _rank(self, kind):
        want = WANT + ["mortar"] if TAKE_MORTAR else WANT
        return want.index(kind) if kind in want else None

    def _lasers(self, obs):
        """Weapon pickups we would take now (better than our non-gun weapon, not in backoff), or []."""
        t = obs.get("t", 0.0)
        for e in obs.get("events") or []:
            if e.get("type") == "take_failed":
                self.skip[e.get("id")] = t + FAIL_BACKOFF_S
        weapons = [w for w in obs["self"].get("weapons") or [] if w]
        held = [w.get("kind") for w in weapons]
        cur = [self._rank(k) for k in held if k != "gun" and self._rank(k) is not None]
        best_held = min(cur) if cur else None
        out = []
        for p in obs.get("pickups") or []:
            r = self._rank(p.get("kind"))
            if r is None or p.get("kind") in held or self.skip.get(p.get("id"), -1.0) > t:
                continue
            if best_held is not None and r >= best_held:
                continue
            out.append(p)
        return out

    def wanted_pickup(self, obs: dict, threats: list) -> dict | None:
        t, me = obs.get("t", 0.0), obs["self"]
        limit = ETA_EARLY_S if t < LATE_T else ETA_LATE_S
        speed = (me.get("stats") or {}).get("walk_speed") or 1.0
        x, y = me["pos"][0], me["pos"][1]
        best, best_eta = None, limit
        for p in self._lasers(obs):
            px, py = p["pos"][0], p["pos"][1]
            eta = math.hypot(px - x, py - y) * DETOUR / speed
            if eta > best_eta:
                continue
            if any(t - th.get("last_seen", t) <= THREAT_MEMORY_S
                   and math.hypot(th["pos"][0] - px, th["pos"][1] - py) <= THREAT_RADIUS
                   for th in threats):
                continue
            best, best_eta = p, eta
        return best

    def take(self, obs: dict) -> dict:
        me = obs["self"]
        slots = me.get("weapons") or [None, None]
        if any(w and w.get("kind") == "laser" and w.get("charge", 0) > 0 for w in slots):
            return {}  # protocol §7: can't swap while a laser charges (take_failed "busy")
        x, y, z = me["pos"]
        for p in self._lasers(obs):
            px, py, pz = p["pos"]
            if math.hypot(px - x, py - y) <= self.reach and abs(pz - z) <= TAKE_DZ:
                act = {"take": p["id"]}
                if len(slots) >= 2 and slots[0] and slots[1]:
                    act["drop"] = 0 if slots[1].get("kind") == "gun" else 1  # replace the special, keep the gun
                return act
        return {}
