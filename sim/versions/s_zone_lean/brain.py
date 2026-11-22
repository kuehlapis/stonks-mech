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
STRAFE_MIN = 0.25             # s between strafe reversals (random, min)
STRAFE_MAX = 0.7             # ... and max
STRAFE_BOOST_E = 999.0        # boost while strafing when energy is above this (999 = off)
STRAFE_JUMP = 0.0             # chance to hop on each strafe reversal (0 = off)
CORNER_DIST = 60.0            # m: a threat this close can't be outrun (same walk speed)
CORNER_ENERGY = 20.0          # below this energy we can't boost away
FIGHT_EDGE = 1.2              # fight if our time-to-kill < this x theirs
DANGER_RANGE = 220.0          # m: hold out of sight of remembered enemies this close (0 = off)
FIGHT_RANGE = 130.0           # m: preferred gun-fight distance (unled shots miss out here; ours lead)
GROUP_EDGE = 1.5              # fight several visible enemies when our ttk on the best target < this x their combined ttk
WEAK_GUN = 0.6                # scale on a gun-only enemy's expected damage rate
OPEN_EDGE = 1.2               # open fire on a lone visible enemy when the time-to-kill ratio is below this
OPEN_RANGE = 180.0            # ... and it is this close
FINISH_FRAC = 0.35            # finish a lone enemy below this fraction of our HP
END_ALIVE = 3                 # alive count at which the endgame starts (more willing to fight)
END_EDGE = 1.15               # endgame fight threshold (time-to-kill ratio)
CLOSE_EDGE = 1.3              # fight at this ratio when the enemy is too close to escape, or evading fails
FIGHT_HYST, FIGHT_STICK_S = 1.4, 2.0   # keep fighting the same enemy unless the ratio worsens by 40%
EVADE_MAX = 1000.0            # m: evade to cover only if it is this close (else fight when the trade is fair)
EVADE_FIGHT = 1.6             # ... "fair" = time-to-kill ratio below this
EVADE_ALL = True             # fire every weapon (not just the gun) while evading
EVADE_GIVEUP_S = 4.0          # still being hit this long after starting to evade: turn and fight
DROP_ON = True                # go for supply drops
DROP_LATE, DROP_CLEAR = 12.0, 100.0   # s after landing we may still arrive; m of enemy-free space around it
CUBE_RANGE, CUBE_CLEAR = 70.0, 50.0   # m: collect visible cubes this close unless a visible enemy is this close to them
FARM_UNTIL = 330.0            # s: no farming after this (phase 5 and later)
FARM_HP = 0.6                 # farm only above this HP fraction
FARM_NPC_RANGE = 120.0        # m: shoot visible drones closer than this
FARM_NPC_MIN, FARM_NPC_MAX = 55.0, 100.0   # m: keep drones in this band (aggro 45 m, their bullets are slow)
FARM_CRATE_RANGE = 80.0       # m: shoot visible crates closer than this
FARM_CRATE_NEAR = 25.0        # m: walk toward a crate until this close
PEEK_AFTER_BEAM = False       # push an enemy during its laser cooldown (after its beam) instead of ducking/backing off
RELOAD_PUSH = False           # push a gun-only enemy during its estimated reload
REAR_TURN = False             # on a rear hit (x1.5 damage), turn the torso to its bearing first
BURN_ENDGAME = False          # from final-zone time - BURN_LEAD s: no fights unless cornered, hold the final center
BURN_LEAD = 40.0              # s before the radius-0 burn
REGEN_BREAK = False           # after a trade, no voluntary fights for regen_delay s (let HP regen)
REGEN_HIDE = False            # with REGEN_BREAK: in the regen window, run to cover from all hunters, then walk quiet, no fire
BURN_QUIET = False            # with BURN_ENDGAME: hold in cover inside the final circle; fire only while exposed
LASER_DUCK = 10.0             # m: duck to cover this close when a fought enemy charges its laser (0 = off)
DODGE = True                  # sidestep visible projectiles that would hit us
DODGE_T, DODGE_MARGIN = 0.9, 0.7   # s look-ahead; m added to our hit radius
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
        self._beam_t = {}   # enemy id -> time of its last laser beam
        self._trade_t = -1e9  # last time we dealt or took mech damage
        zp = (self.cfg.get("zone") or {}).get("phases") or []
        self._burn_t = sum(ph.get("hold_s", 0) + ph.get("shrink_s", 0) for ph in zp) - BURN_LEAD if zp else 375.0
        self._gun = {}      # enemy id -> [burst start, last gun hit, hits in burst]

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
        if DODGE:
            try:
                d = self._dodge(obs, action.get("move"))
                if d is not None:
                    action["move"] = d
            except Exception as e:
                self._log("dodge", e)
        if not self._engaged:  # never swap weapons while engaged
            tk = self._call(self.economy, "take", obs)
            if isinstance(tk, dict):
                action.update(tk)
        if obs.get("offer"):
            p = self._call(self.economy, "pick", obs)
            if p is not None:
                action["pick"] = p
        if REAR_TURN:
            for ev in obs.get("events") or ():
                if ev.get("type") == "damaged" and ev.get("rear") and ev.get("bearing") is not None:
                    action["aim"] = [ev["bearing"], (action.get("aim") or [0, 0])[1]]
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
        if PEEK_AFTER_BEAM or RELOAD_PUSH:
            self._track_shots(obs, t)
        if REGEN_BREAK and any(ev.get("type") in ("damaged", "hit") for ev in obs.get("events") or ()):
            self._trade_t = t
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

        # 1b. Burn endgame: placement is decided at the burn, so keep HP; fight only when cornered
        if BURN_ENDGAME and t >= self._burn_t:
            if engaged and not engaged.get("virtual") and _dist(pos, engaged["pos"]) < CORNER_DIST:
                return self._fight(obs, engaged), "burn-fight"
            hunters = [x for x in threats if not x.get("virtual")]
            if BURN_QUIET and hunters:
                return self._hide(obs, hunters, engaged, "burn-quiet")
            hold = self._call(S, "final_center", obs) or self._next_center(obs)
            aim = self._gun_only(obs, engaged) if engaged and not engaged.get("virtual")                 else self._aim(obs, threats, threatened, hold)
            return {**self._go(obs, hold, quiet=not engaged), **aim}, "burn"

        # 1c. Regen window: break line of sight to every hunter, then stay quiet so regen runs
        hunters = [x for x in threats if not x.get("virtual")]
        if REGEN_HIDE and REGEN_BREAK and hunters and me.get("hp", 0) < me.get("max_hp", 0)                 and t - self._trade_t < (self.cfg.get("mech") or {}).get("regen_delay", 5):
            if engaged and not engaged.get("virtual") and _dist(pos, engaged["pos"]) < CORNER_DIST:
                return self._fight(obs, engaged), "regen-fight"
            return self._hide(obs, hunters, engaged, "regen-hide")

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
                if others and GROUP_EDGE > 0:
                    g = self._group_target(obs, [foe] + others, t)
                    if g is not None:
                        tgt, gr = g
                        if gr < GROUP_EDGE * (FIGHT_HYST if self._fight_id == tgt.get("id") else 1.0):
                            self._fight_id, self._fight_t = tgt.get("id"), t
                            return self._fight(obs, tgt), "group"
            cover = None if self._slow() else self._call(S, "find_cover", obs, [foe] + others)
            if cover and engaged and not foe.get("virtual") and not others and ratio is not None                     and _dist(pos, cover) > EVADE_MAX and ratio < EVADE_FIGHT:
                self._fight_id, self._fight_t = fid, t
                return self._fight(obs, foe), "fight-far"  # cover too far to reach under fire: trade instead
            if cover and engaged and not foe.get("virtual") and not others and self._push_window(obs, foe):
                self._fight_id, self._fight_t = fid, t
                return self._fight(obs, foe), "push"
            if cover:
                lasery = self._lasery(foe)
                hp_frac = me.get("hp", 0) / (me.get("max_hp") or 1)
                at = _dist(pos, cover) < 3
                mv = self._go(obs, cover, boost=(lasery or hp_frac < 0.5 or bool(engaged)) and not at)
                aim = (self._attack(obs, foe) if EVADE_ALL else self._gun_only(obs, foe)) if engaged and not foe.get("virtual")                     else self._face(obs, _bearing(pos, foe["pos"]))
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
        if visible and not (REGEN_BREAK and t - self._trade_t < (self.cfg.get("mech") or {}).get("regen_delay", 5)
                            and me.get("hp", 0) < me.get("max_hp", 0)):
            e = visible[0]
            others = visible[1:]
            if not e.get("virtual") and not others and self._finishable(obs, e, endgame):
                return self._fight(obs, e), "finish"
            if not e.get("virtual") and not others and _dist(pos, e["pos"]) < OPEN_RANGE:
                r = self._ttk_ratio(obs, e)
                if r is not None and r < OPEN_EDGE:
                    self._fight_id, self._fight_t = e.get("id"), t
                    return self._fight(obs, e), "open"

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

        # 5a. Cubes in reach (kills drop the victim's cubes + 2): +HP, +damage, upgrade offers
        cube = self._safe_cube(obs, threats)
        if cube:
            return {**self._go(obs, cube), **self._aim(obs, threats, threatened, cube)}, "cube"

        # 5b. Supply drop: 3 cubes + full HP/energy if we can hold the ring alone
        dr = self._drop_target(obs, threats)
        if dr is not None:
            return {**self._go(obs, dr), **self._aim(obs, threats, threatened, dr)}, "drop"

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

        # 8. Hold quietly: out of sight of every remembered enemy position if we can
        hold = None
        if DANGER_RANGE > 0:
            danger = self._call(P, "danger", t, pos, DANGER_RANGE) or []
            if danger and not self._slow():
                hold = self._call(S, "find_cover", obs, danger)
                if hold:
                    return {**self._go(obs, hold, quiet=_dist(pos, hold) < 25),
                            **self._face(obs, _bearing(pos, danger[0]["pos"]))}, "hide"
        hold = self._call(S, "hold_point", obs) or self._next_center(obs)
        return {**self._go(obs, hold, quiet=True), **self._aim(obs, threats, threatened, hold)}, "hold"

    # --- dodging ---

    def _dodge(self, obs, pref):
        """If a visible enemy projectile will hit us within DODGE_T s, return the move (unit 2D) that
        maximizes the closest miss, preferring `pref`; else None. Ground acceleration model."""
        me = obs["self"]
        if not me.get("grounded", True):
            return None
        projs = obs.get("projectiles") or []
        if not projs:
            return None
        st = me.get("stats") or self.cfg.get("mech") or {}
        p, u = me["pos"], me.get("vel") or [0.0, 0.0, 0.0]
        R = st.get("radius", 2.5) + ((self.cfg.get("projectile") or {}).get("gun_radius", 0.3)) + DODGE_MARGIN
        H = st.get("height", 9.0)
        acc, vmax = st.get("ground_accel", 58.5), st.get("walk_speed", 11.7)
        threats = []
        for q in projs:
            qp, qv = q.get("pos"), q.get("vel")
            if not qp or not qv:
                continue
            rx, ry = qp[0] - p[0], qp[1] - p[1]
            vx, vy = qv[0], qv[1]
            vv = vx * vx + vy * vy
            if vv < 1.0:
                continue
            tca = -(rx * vx + ry * vy) / vv  # closest approach if we stood still
            if tca <= 0 or tca > DODGE_T:
                continue
            z = qp[2] + qv[2] * tca
            if z < p[2] - 0.5 or z > p[2] + H + 0.5:
                continue
            threats.append((qp, qv, tca))
        if not threats:
            return None

        def miss(m):
            tx, ty = m[0] * vmax - u[0], m[1] * vmax - u[1]
            dv = math.hypot(tx, ty)
            ax, ay = (tx / dv * acc, ty / dv * acc) if dv > 1e-6 else (0.0, 0.0)
            ta = dv / acc if dv > 1e-6 else 0.0
            worst = 1e9
            for qp, qv, tca in threats:
                # our average velocity over the approach (accelerating toward m), then exact closest approach
                t1 = min(tca, ta)
                ox = u[0] * tca + 0.5 * ax * t1 * t1 + ax * t1 * (tca - t1)
                oy = u[1] * tca + 0.5 * ay * t1 * t1 + ay * t1 * (tca - t1)
                wx, wy = ox / tca, oy / tca
                rx, ry = qp[0] - p[0], qp[1] - p[1]
                vx, vy = qv[0] - wx, qv[1] - wy
                vv = vx * vx + vy * vy
                ts = max(0.0, min(1.5 * tca, -(rx * vx + ry * vy) / vv)) if vv > 1e-9 else 0.0
                worst = min(worst, math.hypot(rx + vx * ts, ry + vy * ts))
            return worst

        pref = pref if pref and math.hypot(pref[0], pref[1]) > 0.1 else None
        if pref is not None and miss(pref) >= R:
            return None  # current plan already dodges
        best, bm = None, -1.0
        for k in range(8):
            a = k * math.pi / 4
            m = (math.cos(a), math.sin(a))
            if not self._call(self.nav, "free_at", p[0] + 5 * m[0], p[1] + 5 * m[1], default=True):
                continue
            v = miss(m)
            if pref is not None:
                v += 0.3 * (m[0] * pref[0] + m[1] * pref[1])  # tie-break toward the plan
            if v > bm:
                best, bm = m, v
        return [best[0], best[1]] if best else None

    # --- supply drops ---

    def _drop_target(self, obs, threats):
        """Position of a supply drop worth taking now, else None: reachable by landing + DROP_LATE s,
        not held by someone else, no tracked enemy within DROP_CLEAR m of it."""
        if not DROP_ON:
            return None
        me = obs["self"]
        pos = me["pos"]
        walk = (me.get("stats") or {}).get("walk_speed", 11.7) or 11.7
        best = None
        for d in obs.get("drops") or []:
            dp = d.get("pos")
            if not dp:
                continue
            holder = d.get("holder")
            if holder is not None and holder != self.my_id:
                continue
            dist = _dist(pos, dp)
            if dist * 1.3 / walk > (d.get("lands_in") or 0.0) + DROP_LATE:
                continue
            if any(_dist(th["pos"], dp) < DROP_CLEAR for th in threats):
                continue
            if best is None or dist < best[0]:
                best = (dist, dp)
        return best[1] if best else None

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
        if (e.get("weapons") or ["gun"]) == ["gun"]:
            theirs *= WEAK_GUN  # gun-only bots are the weaker tiers (track: weakest hunt first)
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

    def _group_target(self, obs, enemies, t):
        """(target, ratio): the visible enemy we kill fastest, and our time to kill it divided by the time
        all of them together need to kill us. None if HP is unknown for every one."""
        me = obs["self"]
        pos = me["pos"]
        cpc = (self.cfg.get("cubes") or {}).get("damage_per_cube", 0.04)
        cap = (self.cfg.get("cubes") or {}).get("stat_cap", 10)
        mult = 1 + cpc * min(me.get("cubes") or 0, cap)
        total, best = 0.0, None
        for e in enemies:
            if e.get("virtual") or not e.get("pos"):
                continue
            d = _dist(pos, e["pos"])
            th = self._dps(e.get("weapons") or ["gun"], d, 1 + cpc * min(e.get("cubes") or 0, cap))
            if (e.get("weapons") or ["gun"]) == ["gun"]:
                th *= WEAK_GUN
            total += th
            if e.get("hp") is None:
                continue
            ours = self._dps(_kinds(me), d, mult, me.get("energy", 100))
            if ours <= 0:
                continue
            ttk = e["hp"] / ours * (0.85 if e.get("id") == self._fight_id else 1.0)
            if best is None or ttk < best[0]:
                best = (ttk, e)
        if best is None or total <= 0:
            return None
        total *= 1 - ((me.get("stats") or {}).get("armor", 0) or 0)
        return best[1], best[0] / (me.get("hp", 1) / total)

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

    def _exposed(self, obs, hunters):
        """True if any of the 5 nearest hunters has line of sight to us (map-free: any is visible)."""
        w, p = self.world, obs["self"]["pos"]
        if w is None:
            return any(h.get("visible") for h in hunters)
        eh = (self.cfg.get("mech") or {}).get("eye_height", 8)
        me = (p[0], p[1], p[2] + eh)
        near = sorted(hunters, key=lambda h: _dist(p, h["pos"]))[:5]
        return any(w.los((h["pos"][0], h["pos"][1], h["pos"][2] + eh), me) for h in near)

    def _hide(self, obs, hunters, engaged, mode):
        """Full speed to cover while exposed (returning gun fire if shot); once hidden walk quiet, hold fire."""
        p = obs["self"]["pos"]
        near = min(hunters, key=lambda h: _dist(p, h["pos"]))
        cover = None if self._slow() else self._call(self.survival, "find_cover", obs, hunters)
        if self._exposed(obs, hunters):
            aim = self._gun_only(obs, engaged) if engaged and not engaged.get("virtual")                 else self._face(obs, _bearing(p, near["pos"]))
            return {**self._go(obs, cover or self._next_center(obs), boost=True), **aim}, mode
        return {**self._go(obs, cover or p, quiet=True), **self._face(obs, _bearing(p, near["pos"]))}, mode

    def _track_shots(self, obs, t):
        for b in obs.get("beams") or ():
            if b.get("kind") == "laser" and b.get("by") is not None:
                self._beam_t[b["by"]] = t - b.get("age", 0)
        rl = ((self.cfg.get("weapons") or {}).get("gun") or {}).get("reload", 2.4)
        for ev in obs.get("events") or ():
            if ev.get("type") == "damaged" and ev.get("weapon") == "gun" and ev.get("by") is not None:
                g = self._gun.setdefault(ev["by"], [t, -1e9, 0])
                if t - g[1] > rl:
                    g[0], g[2] = t, 0
                g[1] = t
                g[2] += 1

    def _push_window(self, obs, e):
        """True while e can't shoot back well: its laser is on cooldown, or its gun is (estimated) reloading."""
        t, fid = obs.get("t", 0.0), e.get("id")
        W = self.cfg.get("weapons") or {}
        if PEEK_AFTER_BEAM and not e.get("charging") and                 t - self._beam_t.get(fid, -1e9) < (W.get("laser") or {}).get("cooldown", 1.65):
            return True
        g = self._gun.get(fid)
        if RELOAD_PUSH and g and (e.get("weapons") or []) == ["gun"]:
            gw = W.get("gun") or {}
            cd, rl = gw.get("cooldown", 0.24), gw.get("reload", 2.4)
            # shortcut: counts only hits on us (misses are unseen), so a magazine ends by time, not shot count
            mag_out = g[2] >= gw.get("mag", 12) or t - g[0] >= 0.8 * gw.get("mag", 12) * cd
            return mag_out and 3 * cd < t - g[1] < rl
        return False

    def _fight(self, obs, e):
        if (PEEK_AFTER_BEAM or RELOAD_PUSH) and self._push_window(obs, e):
            return {**self._strafe_move(obs, e["pos"], away=min(0.0, self._range_pref(obs, e)) - 0.4),
                    **self._attack(obs, e)}
        if LASER_DUCK > 0 and e.get("charging") and e.get("visible") and not self._slow():
            # a charging laser can't be dodged (hitscan): duck behind cover if it is a few steps away
            cover = self._call(self.survival, "find_cover", obs, [e])
            if cover and _dist(obs["self"]["pos"], cover) <= LASER_DUCK:
                return {**self._go(obs, cover, boost=True), **self._gun_only(obs, e)}
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
        if FIGHT_RANGE > 0:
            return max(-0.6, min(0.8, (FIGHT_RANGE - d) / 40.0))  # kite: hold the fight at our best range
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
        e = me.get("energy", 0)
        boost = (bool(boost) and e > 15) or e > STRAFE_BOOST_E  # boost-strafe: 19.5 vs 11.7 m/s sideways
        boost = boost and me.get("grounded", False)  # boost in the air is a jet (slow, visible climb)
        # a hop on a strafe reversal breaks a shooter's straight-line lead (gravity curve)
        jump = STRAFE_JUMP > 0 and self._strafe_t == t and me.get("grounded", False) and self.rng.random() < STRAFE_JUMP
        return {"move": [mx, my], "boost": boost, "jump": bool(jump)}

    def _safe_cube(self, obs, threats):
        me = obs["self"]
        p = me["pos"]
        best, bd = None, CUBE_RANGE
        for c in obs.get("cubes") or []:
            cp = c.get("pos")
            if not cp or abs(cp[2] - p[2]) > 6:
                continue
            d = _dist(p, cp)
            if d < bd and not any(th.get("visible") and _dist(th["pos"], cp) < CUBE_CLEAR for th in threats):
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
