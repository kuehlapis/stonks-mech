"""Decision layer: one mode per tick, combining module outputs into one action.

Modes (first that applies): zone (must move for the zone), fight (we win the trade or are cornered),
evade (break line of sight to cover), flee (no cover, open ground), finish (weak lone enemy), center
(final circle), loot, hold. Every module call is wrapped so a module bug never crashes act().
"""
import importlib
import math
import random
import time

import mechfight as mf

SWEEP = math.radians(50)      # look-around half-width while walking
STRAFE_MIN, STRAFE_MAX = 0.5, 1.4   # s between strafe reversals (random)
CORNER_DIST = 60.0            # m: a threat this close can't be outrun (same walk speed)
CORNER_ENERGY = 20.0          # below this energy we can't boost away
FIGHT_EDGE = 0.8              # fight if our time-to-kill < this x theirs
FINISH_FRAC = 0.35            # finish a lone enemy below this fraction of our HP
END_ALIVE = 3                 # alive count at which the endgame starts (more willing to fight)
END_EDGE = 1.15               # endgame fight threshold (time-to-kill ratio)
CLOSE_EDGE = 1.3              # fight at this ratio when the enemy is too close to escape, or evading fails
FIGHT_HYST, FIGHT_STICK_S = 1.4, 2.0   # keep fighting the same enemy unless the ratio worsens by 40%
EVADE_GIVEUP_S = 4.0          # still being hit this long after starting to evade: turn and fight
FARM_UNTIL = 330.0            # s: no farming after this (phase 5 and later)
FARM_HP = 0.6                 # farm only above this HP fraction
FARM_NPC_RANGE = 120.0        # m: shoot visible drones closer than this
FARM_NPC_MIN, FARM_NPC_MAX = 55.0, 100.0   # m: keep drones in this band (aggro 45 m, their bullets are slow)
FARM_CRATE_RANGE = 80.0       # m: shoot visible crates closer than this
FARM_CRATE_NEAR = 25.0        # m: walk toward a crate until this close
SLOW_MS = 30.0                # past this many ms in act(), skip optional work (cover search)
HIT_P = {"gun": (0.75, 0.35, 0.15), "laser": (0.95, 0.85, 0.7), "mortar": (0.6, 0.35, 0.2), "lightning": (1, 0, 0)}


class Brain:
    def __init__(self, cfg: dict, world, my_id: int) -> None:
        self.cfg, self.world, self.my_id = cfg or {}, world, my_id
        self._errors = {}
        self.rng = random.Random(my_id * 7919 + 17)
        self.perception = self._make("perception", "Perception", self.cfg, my_id)
        self.survival = self._make("survival", "Survival", self.cfg, world)
        self.nav = self._make("nav", "Nav", self.cfg, world)
        self.combat = self._make("combat", "Combat", self.cfg, world)
        self.economy = self._make("economy", "Economy", self.cfg)
        if self.survival is not None and self.nav is not None and getattr(self.nav, "world", None) is not None:
            self.survival.nav = self.nav
        self._strafe = 1
        self._strafe_t = -1.0
        self._strafe_dt = 1.0
        self._mode = None
        self._fight_id, self._fight_t = None, -1e9
        self._evade_id, self._evade_t = None, 0.0

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
        self._t0 = time.perf_counter()
        self._engaged = None
        try:
            action, mode = self._decide(obs)
        except Exception as e:  # last resort: brain bug, still return move/aim
            self._log("brain", e)
            try:
                action, mode = self._safe(obs), "safe"
            except Exception:  # obs itself is broken
                action, mode = {"move": [0.0, 0.0], "aim": [0.0, 0.0], "fire": [False, False]}, "safe"
        self._mode = mode
        if not self._engaged:  # never swap weapons while engaged
            tk = self._call(self.economy, "take", obs)
            if isinstance(tk, dict):
                action.update(tk)
        if obs.get("offer"):
            p = self._call(self.economy, "pick", obs)
            if p is not None:
                action["pick"] = p
        mf.draw.label(mode)
        return action

    def _hit_t(self, fid):
        hb = getattr(self.perception, "hit_by", None)
        return hb.get(fid, -1e9) if isinstance(hb, dict) else -1e9

    def _slow(self):
        return (time.perf_counter() - self._t0) * 1000 > SLOW_MS

    def _safe(self, obs):
        me = obs.get("self") or {}
        z = obs.get("zone") or {}
        aim = me.get("aim") or [0.0, 0.0]
        return {**self._go(obs, z.get("next_center") or me.get("pos") or [0, 0], quiet=True),
                "aim": [aim[0], 0.0], "fire": [False, False]}

    def _decide(self, obs):
        P, S, E = self.perception, self.survival, self.economy
        t = obs.get("t", 0.0)
        me = obs["self"]
        pos = me["pos"]
        self._call(P, "update", obs)
        threats = getattr(P, "threats", None)
        threats = [x for x in threats if isinstance(x, dict) and x.get("pos")] if isinstance(threats, list) else []
        engaged = self._engaged = self._call(P, "engaged_by", t)
        threatened = self._call(P, "threatened_by", obs, self.world)
        visible = sorted((x for x in threats if x.get("visible")), key=lambda x: _dist(pos, x["pos"]))
        endgame = obs.get("alive", 16) <= END_ALIVE
        foe = engaged or threatened

        # 1. Zone first when urgent: travel, but shoot back with the gun if someone is on us
        zg = self._call(S, "zone_goal", obs)
        urgent = bool(zg) and self._call(S, "zone_urgent", obs, zg[0], default=True)
        if zg and urgent:
            goal, boost = zg
            if foe and not foe.get("virtual"):
                return {**self._go(obs, goal, boost=boost), **self._gun_only(obs, foe)}, "zone"
            return {**self._go(obs, goal, boost=boost), **self._aim(obs, threats, threatened, goal)}, "zone"

        # 2. Under fire or in someone's sights
        if foe:
            if foe.get("virtual") and (foe.get("weapons") or []) == ["mortar"]:
                # a mortar bearing points at the blast, not the shooter: step sideways, don't aim along it
                b = _bearing(pos, foe["pos"]) + math.pi / 2 * self._strafe
                side = [pos[0] + 20 * math.cos(b), pos[1] + 20 * math.sin(b)]
                return {**self._go(obs, side, boost=True), **self._face(obs, _bearing(pos, foe["pos"]))}, "dodge"
            others = [x for x in visible if x.get("id") != foe.get("id")]
            ratio = self._ttk_ratio(obs, foe)
            edge = END_EDGE if endgame else FIGHT_EDGE
            fid = foe.get("id")
            if self._fight_id == fid and t - self._fight_t < FIGHT_STICK_S:
                edge *= FIGHT_HYST  # already fighting it: don't flip-flop
            d = _dist(pos, foe["pos"])
            if engaged and not foe.get("virtual"):
                if self._evade_id != fid:
                    self._evade_id, self._evade_t = fid, t
                stuck = t - self._evade_t > EVADE_GIVEUP_S and t - self._hit_t(fid) < 1.5
                if ratio is not None and not others and (ratio < edge or (d < CORNER_DIST and ratio < CLOSE_EDGE)
                                                          or (stuck and ratio < CLOSE_EDGE)):
                    self._fight_id, self._fight_t = fid, t
                    return self._fight(obs, foe), "fight"
            cover = None if self._slow() else self._call(S, "find_cover", obs, [foe] + others)
            if cover:
                lasery = self._lasery(foe)
                hp_frac = me.get("hp", 0) / (me.get("max_hp") or 1)
                at = _dist(pos, cover) < 3
                mv = self._go(obs, cover, boost=(lasery or hp_frac < 0.5 or bool(engaged)) and not at)
                aim = self._gun_only(obs, foe) if engaged and not foe.get("virtual") else self._face(obs, _bearing(pos, foe["pos"]))
                return {**mv, **aim}, "evade"
            if engaged and (d < CORNER_DIST or me.get("energy", 0) < CORNER_ENERGY or foe.get("virtual") is False and not others and ratio is not None and ratio < 1.3):
                return self._fight(obs, foe), "cornered"
            if not engaged:
                # seen but not shot yet: slip out of its view sideways, quietly facing it
                return {**self._strafe_move(obs, foe["pos"], away=0.5), **self._face(obs, _bearing(pos, foe["pos"]))}, "slip"
            return {**self._strafe_move(obs, foe["pos"], away=1.0, boost=True), **self._gun_only(obs, foe)}, "flee"

        self._evade_id = None

        # 2b. A drone shooting at us: kill it (350 HP, 2 cubes) rather than drag it along
        npc = self._call(P, "npc_attacker", t)
        if npc and npc.get("pos"):
            return self._fight(obs, self._npc_target(npc)), "npc"

        # 3. A lone, weak enemy in view: finish it (its cubes and weapons drop)
        if visible:
            e = visible[0]
            others = visible[1:]
            if not e.get("virtual") and not others and self._finishable(obs, e, endgame):
                return self._fight(obs, e), "finish"

        # 4. Final circle: stand on its center
        fc = self._call(S, "final_center", obs)
        if fc:
            if visible and endgame:
                e = visible[0]
                if _dist(pos, e["pos"]) < 200:
                    return {**self._go(obs, fc), **self._attack(obs, e)}, "center-fight"
            return {**self._go(obs, fc), **self._aim(obs, threats, threatened, fc)}, "center"

        # 5. Zone travel that isn't urgent yet
        if zg:
            goal, boost = zg
            return {**self._go(obs, goal, boost=boost), **self._aim(obs, threats, threatened, goal)}, "travel"

        # 6. Farm drones and crates while nobody is around
        farm = self._farm_target(obs, threats, endgame)
        if farm:
            tgt, kind = farm
            d = _dist(pos, tgt["pos"])
            if kind == "npc":
                away = 0.7 if d < FARM_NPC_MIN else (-0.6 if d > FARM_NPC_MAX else 0.0)
                return {**self._strafe_move(obs, tgt["pos"], away=away), **self._attack(obs, tgt)}, "farm"
            mv = self._go(obs, tgt["pos"]) if d > FARM_CRATE_NEAR else {"move": [0.0, 0.0], "boost": False, "jump": False}
            return {**mv, **self._attack(obs, tgt)}, "crate"

        # 7. Loot
        want = self._call(E, "wanted_pickup", obs, threats)
        if want and want.get("pos"):
            return {**self._go(obs, want["pos"]), **self._aim(obs, threats, threatened, want["pos"])}, "loot"
        cube = self._safe_cube(obs, threats)
        if cube:
            return {**self._go(obs, cube), **self._aim(obs, threats, threatened, cube)}, "cube"

        # 8. Hold quietly
        hold = self._call(S, "hold_point", obs) or self._next_center(obs)
        return {**self._go(obs, hold, quiet=True), **self._aim(obs, threats, threatened, hold)}, "hold"

    # --- farming ---

    def _npc_target(self, n):
        nc = self.cfg.get("npc") or {}
        return {"id": n.get("id"), "pos": n["pos"], "vel": n.get("vel") or [0.0, 0.0, 0.0],
                "center_h": nc.get("height", 3.5) / 2, "radius": nc.get("radius", 1.8), "weapons": [], "hp": n.get("hp")}

    def _farm_target(self, obs, threats, endgame):
        """(target, "npc" | "crate") worth shooting now: nobody tracked, healthy, not late, else None."""
        me, t = obs["self"], obs.get("t", 0.0)
        if endgame or t > FARM_UNTIL or threats or me.get("hp", 0) < FARM_HP * (me.get("max_hp") or 1):
            return None
        pos = me["pos"]
        best = None
        npcs = getattr(self.perception, "npcs", None)
        for n in (npcs.values() if isinstance(npcs, dict) else ()):
            if n.get("visible") and n.get("pos"):
                d = _dist(pos, n["pos"])
                if d < FARM_NPC_RANGE and (best is None or d < best[0]):
                    best = (d, self._npc_target(n), "npc")
        if best:
            return best[1], best[2]
        cr = self.cfg.get("crates") or {}
        for c in obs.get("crates") or []:
            cp = c.get("pos")
            if not cp:
                continue
            d = _dist(pos, cp)
            if d < FARM_CRATE_RANGE and abs(cp[2] - pos[2]) < 8 and (best is None or d < best[0]):
                best = (d, {"id": c.get("id"), "pos": cp, "vel": [0.0, 0.0, 0.0], "center_h": cr.get("height", 2.4) / 2,
                            "radius": cr.get("radius", 1.4), "weapons": [], "hp": c.get("hp")}, "crate")
        return (best[1], best[2]) if best else None

    # --- fight model ---

    def _dps(self, kinds, dist, mult=1.0, energy=100.0):
        """Rough expected damage per second of a weapon set at a range (sum over weapons)."""
        W = self.cfg.get("weapons") or {}
        band = 0 if dist < 60 else 1 if dist < 150 else 2
        total = 0.0
        for k in kinds:
            w = W.get(k) or {}
            if k == "gun" and dist <= w.get("range", 230):
                cyc = w.get("mag", 12) * w.get("cooldown", 0.24) + w.get("reload", 2.4)
                total += w.get("damage", 45) * w.get("mag", 12) / cyc * HIT_P["gun"][band]
            elif k == "laser" and dist <= w.get("range", 280):
                total += w.get("damage", 315) / (w.get("charge", 0.75) + w.get("cooldown", 1.65)) * HIT_P["laser"][band]
            elif k == "mortar" and 20 < dist <= 230:
                total += (w.get("damage", 200) + 0.5 * w.get("splash", 160)) / w.get("cooldown", 2.6) * HIT_P["mortar"][band]
            elif k == "lightning" and dist <= w.get("range", 45) and energy > 10:
                total += w.get("damage", 60) / w.get("cooldown", 0.25)
        return total * mult

    def _ttk_ratio(self, obs, e):
        """Our time to kill e divided by its time to kill us (< 1 means we win). None if e's HP is unknown."""
        me = obs["self"]
        if e.get("hp") is None:
            return None
        d = _dist(me["pos"], e["pos"])
        cpc = (self.cfg.get("cubes") or {}).get("damage_per_cube", 0.04)
        cap = (self.cfg.get("cubes") or {}).get("stat_cap", 10)
        ours = self._dps(_kinds(me), d, 1 + cpc * min(me.get("cubes") or 0, cap), me.get("energy", 100))
        theirs = self._dps(e.get("weapons") or ["gun"], d, 1 + cpc * min(e.get("cubes") or 0, cap))
        # cook-off: lasers do +60% to a mortar holder; armor from our stats
        lz = ((self.cfg.get("weapons") or {}).get("laser") or {}).get("cookoff", 0.6)
        if "mortar" in _kinds(me) and "laser" in (e.get("weapons") or []):
            theirs *= 1 + lz * 0.5
        theirs *= 1 - ((me.get("stats") or {}).get("armor", 0) or 0)
        if ours <= 0:
            return 99.0
        if theirs <= 0:
            return 0.0
        return (e["hp"] / ours) / (me.get("hp", 1) / theirs)

    def _finishable(self, obs, e, endgame):
        me = obs["self"]
        if e.get("hp") is None or _dist(me["pos"], e["pos"]) > 180:
            return False
        r = self._ttk_ratio(obs, e)
        if r is None:
            return False
        if endgame:
            return r < END_EDGE
        return e["hp"] <= FINISH_FRAC * me.get("hp", 0) and r < 0.5

    @staticmethod
    def _lasery(e):
        return bool(e.get("charging")) or "laser" in (e.get("weapons") or [])

    def _fight(self, obs, e):
        return {**self._strafe_move(obs, e["pos"], away=self._range_pref(obs, e)), **self._attack(obs, e)}

    def _range_pref(self, obs, e):
        """>0 back off, <0 close in, from the weapon matchup at this range."""
        me = obs["self"]
        d = _dist(me["pos"], e["pos"])
        mine, theirs = _kinds(me), e.get("weapons") or []
        lr = ((self.cfg.get("weapons") or {}).get("lightning") or {}).get("range", 45)
        if "lightning" in theirs and "lightning" not in mine and d < lr + 25:
            return 0.6
        if "lightning" in mine and "lightning" not in theirs and d > lr - 10:
            return -0.6
        if d < 25:
            return 0.3
        return 0.0

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

    def _strafe_move(self, obs, tp, away=0.0, boost=False):
        """Move perpendicular to the threat, reversing at random; `away` > 0 adds a component away from it.
        Stays on walkable ground and inside the zone."""
        me, t = obs["self"], obs.get("t", 0.0)
        p = me["pos"]
        if t - self._strafe_t > self._strafe_dt:
            self._strafe = -self._strafe
            self._strafe_t = t
            self._strafe_dt = self.rng.uniform(STRAFE_MIN, STRAFE_MAX)
        b = _bearing(p, tp)
        z = obs.get("zone") or {}
        S = self.survival
        circle = self._call(S, "live_circle", obs) if S else None
        for attempt in range(2):
            s = self._strafe
            mx = -math.sin(b) * s - away * math.cos(b)
            my = math.cos(b) * s - away * math.sin(b)
            L = math.hypot(mx, my) or 1.0
            mx, my = mx / L, my / L
            ahead = (p[0] + 6 * mx, p[1] + 6 * my)
            ok = self._call(self.nav, "free_at", ahead[0], ahead[1], default=True)
            if ok and circle:
                c, r = circle
                ok = math.hypot(ahead[0] - c[0], ahead[1] - c[1]) <= r - 8 or \
                    math.hypot(ahead[0] - c[0], ahead[1] - c[1]) < math.hypot(p[0] - c[0], p[1] - c[1])
            if ok:
                break
            self._strafe = -self._strafe
            self._strafe_t = t
        else:
            # both sides blocked: head for the zone center
            nc = z.get("next_center") or p
            dx, dy = nc[0] - p[0], nc[1] - p[1]
            L = math.hypot(dx, dy) or 1.0
            mx, my = dx / L, dy / L
        return {"move": [mx, my], "boost": bool(boost) and me.get("energy", 0) > 15, "jump": False}

    def _safe_cube(self, obs, threats):
        me = obs["self"]
        p = me["pos"]
        best, bd = None, 45.0
        for c in obs.get("cubes") or []:
            cp = c.get("pos")
            if not cp or abs(cp[2] - p[2]) > 6:
                continue
            d = _dist(p, cp)
            if d < bd and not any(_dist(th["pos"], cp) < 80 for th in threats):
                best, bd = cp, d
        return best

    # --- aim ---

    def _face(self, obs, yaw):
        return self._call(self.combat, "face", obs, yaw) or {"aim": [yaw, 0.0], "fire": [False, False]}

    def _attack(self, obs, e):
        return (self._call(self.combat, "attack", obs, e)
                or {"aim": [_bearing(obs["self"]["pos"], e["pos"]), 0.0], "fire": [False, False]})

    def _gun_only(self, obs, e):
        """Torso on the threat; fire only the gun (a laser charge halves move speed)."""
        a = dict(self._attack(obs, e))
        ws = obs["self"].get("weapons") or []
        a["fire"] = [bool(f) and i < len(ws) and bool(ws[i]) and ws[i].get("kind") == "gun"
                     for i, f in enumerate(a.get("fire") or [False, False])]
        return a

    def _aim(self, obs, threats, threatened, goal):
        """Facing only (never fires): threat, damage bearing, nearest visible, sound, hold facing, sweep."""
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
