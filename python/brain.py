"""M1 decision layer: one fixed priority list per tick (game-plan §4 M1 simplification, §3, §8)."""
import importlib
import math
import time

import mechfight as mf

COVER_BUDGET_S = 0.030

SWEEP = math.radians(50)  # §8 rule 5: walking direction ±50°


class Brain:
    def __init__(self, cfg: dict, world, my_id: int) -> None:
        self.cfg, self.world, self.my_id = cfg or {}, world, my_id
        self._errors = {}
        self._last_cover = None  # (obs.t, threat positions, point)
        self.perception = self._make("perception", "Perception", self.cfg, my_id)
        self.survival = self._make("survival", "Survival", self.cfg, world)
        self.nav = self._make("nav", "Nav", self.cfg, world)
        self.combat = self._make("combat", "Combat", self.cfg, world)
        self.economy = self._make("economy", "Economy", self.cfg)

    # --- never crash: every module call goes through _call ---

    def _log(self, key, e):
        n = self._errors[key] = self._errors.get(key, 0) + 1
        if n == 1 or n % 200 == 0:
            mf.log(f"brain: {key} failed ({n}x): {e!r}")

    def _make(self, mod, cls, *args):
        try:
            return getattr(importlib.import_module(mod), cls)(*args)
        except Exception as e:
            self._log(f"{mod}.__init__", e)
            return None

    def _call(self, mod, name, *args, default=None, **kw):
        if mod is None:
            return default
        try:
            return getattr(mod, name)(*args, **kw)
        except Exception as e:
            self._log(f"{type(mod).__name__}.{name}", e)
            return default

    # --- the tick ---

    def act(self, obs: dict) -> dict:
        self._engaged = None
        try:
            action, mode = self._decide(obs)
        except Exception as e:  # last resort: brain bug, still return move/aim
            self._log("brain", e)
            try:
                action, mode = self._safe(obs), "safe"
            except Exception:  # obs itself is broken
                action, mode = {"move": [0.0, 0.0], "aim": [0.0, 0.0], "fire": [False, False]}, "safe"
        if not self._engaged:  # L1: never swap weapons while engaged
            tk = self._call(self.economy, "take", obs)
            if isinstance(tk, dict):
                action.update(tk)
        if obs.get("offer"):
            p = self._call(self.economy, "pick", obs)
            if p is not None:
                action["pick"] = p
        mf.draw.label(mode)
        return action

    def _safe(self, obs):
        me = obs.get("self") or {}
        z = obs.get("zone") or {}
        aim = me.get("aim") or [0.0, 0.0]
        return {**self._go(obs, z.get("next_center") or me.get("pos") or [0, 0], quiet=True),
                "aim": [aim[0], 0.0], "fire": [False, False]}

    def _decide(self, obs):
        self._tick_started = time.perf_counter()
        P, S, E = self.perception, self.survival, self.economy
        t = obs.get("t", 0.0)
        me = obs["self"]
        self._call(P, "update", obs)
        threats = getattr(P, "threats", None)
        threats = [x for x in threats if isinstance(x, dict) and x.get("pos")] if isinstance(threats, list) else []
        engaged = self._engaged = self._call(P, "engaged_by", t)
        threatened = self._call(P, "threatened_by", obs, self.world)

        # 1. Zone first (Z1/Z3)
        zg = self._call(S, "zone_goal", obs)
        if zg:
            goal, boost = zg
            return {**self._go(obs, goal, boost=boost), **self._aim(obs, threats, threatened, engaged, goal)}, "zone"

        # 2. Threatened (laser about to hit / aimed at us): hide, never start shooting
        cover = None
        if threatened or engaged:
            cover = self._find_cover(obs, threats)
        if threatened and (cover or not engaged):
            boost = self._lasery(threatened)
            if cover:
                return {**self._go(obs, cover, boost=boost), **self._retreat_aim(obs, threatened, engaged)}, "cover"
            # F3 fallback without cover while not cornered: straight away, boosting
            return {**self._away(me, threatened), **self._retreat_aim(obs, threatened, engaged)}, "flee"

        # 3. Engaged: fire back only under M1 rule (b), else disengage; no cover = cornered (a)
        if engaged:
            if engaged.get("virtual") and (engaged.get("weapons") or []) == ["mortar"]:
                # §1: a mortar bearing points at the blast, not the shooter: step 20 m sideways, don't aim along it
                b = _bearing(me["pos"], engaged["pos"]) + math.pi / 2
                side = [me["pos"][0] + 20 * math.cos(b), me["pos"][1] + 20 * math.sin(b)]
                return {**self._go(obs, side), **self._face(obs, b)}, "dodge"
            cornered = (not cover and
                        (_dist(me["pos"], engaged["pos"]) <= 60.0 or me.get("energy", 0) < 20.0))
            if self._may_fight(obs, engaged, threats) or cornered:
                hold = self._call(S, "hold_point", obs) or self._next_center(obs)
                return {**self._go(obs, hold), **self._attack(obs, engaged)}, "fight"
            if not cover:  # Distant threat and no cover: boost away while facing it.
                return {**self._away(me, engaged), **self._retreat_aim(obs, engaged, engaged)}, "flee"
            return {**self._go(obs, cover, boost=self._lasery(engaged)),
                    **self._retreat_aim(obs, engaged, engaged)}, "disengage"

        # 4. Phase 6: stand on the final center
        fc = self._call(S, "final_center", obs)
        if fc:
            return {**self._go(obs, fc), **self._aim(obs, threats, threatened, engaged, fc)}, "center"

        # 5. Wanted laser pickup
        want = self._call(E, "wanted_pickup", obs, threats)
        if want and want.get("pos"):
            return {**self._go(obs, want["pos"]), **self._aim(obs, threats, threatened, engaged, want["pos"])}, "loot"

        # 6. Hold quietly
        hold = self._call(S, "hold_point", obs) or self._next_center(obs)
        return {**self._go(obs, hold, quiet=True), **self._aim(obs, threats, threatened, engaged, hold)}, "hold"

    def _find_cover(self, obs, threats):
        """Skip optional cover search after 30 ms; reuse a recent point for the same threat layout."""
        tps = [list(th["pos"]) for th in threats if th.get("pos")]
        if time.perf_counter() - getattr(self, "_tick_started", time.perf_counter()) >= COVER_BUDGET_S:
            c = self._last_cover
            if c and 0 <= obs.get("t", 0) - c[0] < 1.0 and len(c[1]) == len(tps) and all(
                    _dist(a, b) <= 10.0 for a, b in zip(c[1], tps)):
                return c[2]
            return None
        cover = self._call(self.survival, "find_cover", obs, threats)
        if cover:
            self._last_cover = (obs.get("t", 0), tps, cover)
        return cover

    # --- rules ---

    def _may_fight(self, obs, e, threats):
        """M1 rule (b), game-plan §4."""
        me = obs["self"]
        mine = _kinds(me)
        theirs = e.get("weapons") or []
        hp, max_hp = me.get("hp", 0), me.get("max_hp") or 1
        if e.get("hp") is None or e["hp"] > 0.8 * hp or hp / max_hp < 0.5:
            return False
        if "laser" in theirs and "laser" not in mine:
            return False
        if any(x is not e and x.get("id") != e.get("id") for x in threats):
            return False
        lr = ((self.cfg.get("weapons") or {}).get("lightning") or {}).get("range", 45)
        if "laser" in mine and "lightning" in theirs and _dist(me["pos"], e["pos"]) <= lr + 10:
            return False
        return True

    @staticmethod
    def _lasery(e):
        return bool(e.get("charging")) or "laser" in (e.get("weapons") or [])

    # --- movement ---

    def _next_center(self, obs):
        z = obs.get("zone") or {}
        return z.get("next_center") or obs["self"]["pos"]

    def _go(self, obs, goal, boost=False, quiet=False):
        r = self._call(self.nav, "step", obs, goal, boost=boost, quiet=quiet)
        if r:
            return r
        p = obs["self"]["pos"]  # map-free fallback: straight line
        dx, dy = goal[0] - p[0], goal[1] - p[1]
        d = math.hypot(dx, dy)
        k = 0.0 if d < 2 else (0.4 if quiet else 1.0) / d
        return {"move": [dx * k, dy * k], "boost": bool(boost) and d >= 2, "jump": False}

    @staticmethod
    def _away(me, e):
        dx, dy = me["pos"][0] - e["pos"][0], me["pos"][1] - e["pos"][1]
        d = math.hypot(dx, dy) or 1.0
        return {"move": [dx / d, dy / d], "boost": True, "jump": False}

    # --- aim ---

    def _face(self, obs, yaw):
        return self._call(self.combat, "face", obs, yaw) or {"aim": [yaw, 0.0], "fire": [False, False]}

    def _attack(self, obs, e):
        return (self._call(self.combat, "attack", obs, e)
                or {"aim": [_bearing(obs["self"]["pos"], e["pos"]), 0.0], "fire": [False, False]})

    def _retreat_aim(self, obs, e, engaged):
        """F3 step 2: torso at the threat; gun only, and only if engaged."""
        if not engaged:
            return self._face(obs, _bearing(obs["self"]["pos"], e["pos"]))
        a = dict(self._attack(obs, e))
        ws = obs["self"].get("weapons") or []
        a["fire"] = [bool(f) and i < len(ws) and bool(ws[i]) and ws[i].get("kind") == "gun"
                     for i, f in enumerate(a.get("fire") or [False, False])]
        return a

    def _aim(self, obs, threats, threatened, engaged, goal):
        """§8 priority, facing only (never fires)."""
        P, me, t = self.perception, obs["self"], obs.get("t", 0.0)
        pos = me["pos"]
        if threatened:
            return self._face(obs, _bearing(pos, threatened["pos"]))
        b = self._call(P, "damage_bearing", t)
        if b is not None:
            return self._face(obs, b)
        vis = [x for x in threats if x.get("visible") and x.get("pos")]
        if vis:
            n = min(vis, key=lambda x: _dist(pos, x["pos"]))
            if _dist(pos, n["pos"]) <= 200:
                return self._face(obs, _bearing(pos, n["pos"]))
        b = self._call(P, "sound_bearing", t)
        if b is not None:
            return self._face(obs, b)
        if _dist(pos, goal) < 5:
            y = self._call(self.survival, "hold_facing", obs)
            if y is not None:
                return self._face(obs, y)
        y = _bearing(pos, goal) if _dist(pos, goal) >= 2 else (me.get("aim") or [0.0])[0]
        return self._face(obs, y + SWEEP * math.sin(t * math.pi / 2))  # 4 s sweep period


def _kinds(me):
    return [w.get("kind") for w in me.get("weapons") or [] if w]


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _bearing(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])
