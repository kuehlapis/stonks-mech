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
RUN_MODE = False              # never start a fight: on contact break LOS / run to the far side of the next circle
SQ_SURVIVE_T = 0.0            # squad mode: from this time on, switch to RUN_MODE survival (let drones/zone thin the squad) (0 = off)
RUN_HIT_S = 3.0               # RUN_MODE yields to the normal fight/evade logic for this long after any hit on us
RUN_ENERGY = 40.0             # ... boost only above this energy (escape reserve)
RUN_FINISH = 0.35             # ... but finish a lone visible enemy below this fraction of its max HP
RUN_HIDE_S = 30.0             # s: in RUN_MODE stay in cover this long after the last sighting (squad shared memory)
FIRE_POLICY = False           # only fire at a mech that is engaging us (and we're exposed), or that we can one-shot alone
FIRE_MEMORY = 10.0            # s: a mech that damaged us this recently counts as engaging us
LADDER = False                # before LADDER_END_T: fight weak-looking (gun-only) hunters, else run
LADDER_END_T = 150.0          # after this, hunters include mediums
LADDER_MAX_SEEN = 3           # ... only while this many or fewer enemies are visible
LADDER_ABORT_HITS = 2         # drop a ladder target that lands this many hits on us ...
LADDER_ABORT_S = 3.0          # ... within this many seconds (it can aim)
LADDER_CUBE_S = 5.0           # s after a kill: go for the drop even while run-waiting
LADDER_HP = 0.5               # ... and our HP fraction is above this
LADDER_KILLS_MAX = 2          # kill cap while LADDER is on (replaces RUN_KILLS_MAX)
RUN_KILLS_MAX = 2             # RUN_MODE: at most this many run-finish kills per match
DROP_SEEN_S = 0.0             # s: skip drops if a real enemy was seen this recently (0 = off)
DROP_SAFE_R = 0.0             # m: skip a drop with any remembered enemy this close (0 = off)
LASER_DUCK = 10.0             # m: duck to cover this close when a fought enemy charges its laser (0 = off)
SQUAD_MODE = True  # practice vs the house squad: giddy-style rules (_decide_squad)
SQ_ENGAGE = 90.0  # m: engage anything this close
SQ_MAXT = 240.0               # m: farthest target
SQ_LASER_RANGE = 120.0        # m: fight range with a laser
SQ_GUN_RANGE = 85.0           # m: ... with only the gun
SQ_LIGHT_RANGE = 28.0         # m: ... with lightning (no laser)
SQ_LASER_HUNT = 150.0  # squad mode, no laser: target score bonus for laser holders and engage them within 150 m (kill, take its laser) (0 = off)
SQ_LH_RANGE = 150.0           # ... engage laser holders this close
SQ_LH_HP = 0.5                # ... while our HP fraction is above this
NOLASER_ENGAGE = 0.0          # squad mode, no laser yet: engage only within this many m (or when hit / laser carrier / finishing); no pokes (0 = off)
NOLASER_FARM_HP = 0.0         # ... and farm crates above this HP fraction even with threats around (0 = off)
SQ_STICK = 120.0              # squad target score bonus for the current target
SQ_LOWB = 100.0               # ... bonus for a target at or below 30% HP
SQ_HPW = 0.2                  # ... score per enemy HP point
SQ_FINISH = 26.0              # m: close in to finish a low target
SQ_LOOT = 150.0               # m: loot radius (cubes x0.7, remembered crates)
SQ_FARM_HP = 0.5              # farm crates above this HP fraction
SQ_PRECHARGE = 6.0  # s: keep the laser charged this long after the last threat (0 = off)
SQ_SKILL_W = 0.0              # squad mode: target score penalty per observed enemy dps on us (0 = off)
SQ_SKILL_DANGER = 0.0         # squad mode: observed dps above this + our HP < 60% = losing (0 = off)
SQ_HULL = True                # squad mode: fight from hull-down spots (our muzzle sees them, their eye can't see our center)
HULL_M = 8.0                  # m: search radius for a hull-down spot
SQ_FIGHTMOVE = False          # squad mode: candidate-scored fight steps (range, LOS to target, hidden from others)
SQ_FM_EXPOSE = 30.0           # ... penalty per other visible enemy that could see a candidate step
SQ_LASER_AVOID = False        # squad mode, no laser: skip laser holders that aren't attacking us; prefer gun-only targets
SQ_NO_POKE = False            # squad mode: don't open on bots merely closing/aiming from afar (they retaliate 30 s)
SQ_DRONE_FIRST = 0.0          # squad mode: farm visible NPC drones (2 cubes each) before crates while our HP fraction is above this (0 = off)
SITU_LOOT = True  # squad mode: take drops / drones / rooftops only when the live situation makes them worth it (see _loot_worth)
SQ_DROPS = False              # squad mode: take supply drops (3 cubes + full HP) when reachable and clear
CHECK6_T = 0.0                # s: until then, glance behind every CHECK6_P s while looting/travelling with no visible threat (0 = off)
CHECK6_P = 6.0                # s: glance period
CHECK6_D = 1.6                # s: glance length (180 deg out and back at 4 rad/s)
SQ_SCAN = 0.0                 # rad/s: spin-scan rate while we hold no laser and see no enemy (0 = off)
SQ_HUNT_T = 25.0  # s: until then, explore new ground for a laser instead of roaming (0 = off)
EXPLORE_BOOST = 999.0         # boost while exploring/looting for a laser when energy is above this (999 = off)
ROOF_T = 90.0  # s: until then (no laser), explore by touring reachable rooftops (a quarter of loot and crates are up there) (0 = off)
ROOF_MAX_H = 40.0             # m: roofs this high above the ground or lower (jet reach)
ROOF_R = 170.0                # m: only roofs this close
EXPLORE_M = 110.0             # m: explore waypoint distance
SQ_BACKSTAB = 0.0             # m: squad mode opens on enemies facing away (rear x1.5) this close when healthy (0 = off)
SQ_BACK_OFF = 1.75            # rad: "facing away" = its aim this far off the bearing to us
SQ_RESET_HP = 0.0             # squad mode: with no target and HP below this fraction, heal in cover from remembered enemies (0 = off)
SQ_LOSE2 = 0.55               # squad mode: two enemies within 160 m and HP below this fraction = losing (retreat)
FFA_DEAD = 5                  # mechs dead without our kill that prove a free-for-all (squad mode off)
PEEK_LASER = False            # squad mode: charge the laser in cover, swing out to fire, duck again
PEEK_COVER_M = 15.0           # m: only use cover this close for the peek cycle
PEEK_MAX_CROWD = 2            # ... and only with this many or fewer enemies in the fight
MESH_MULTI_HP = 0.0           # tactic mesh: 2+ distinct enemies hit us in MESH_HIT_S and HP below this = break contact (0 = off)
MESH_HIT_S = 4.0              # ... "recent hit" window (s)
MESH_EDGE = 0.0               # tactic mesh: live duel forecast; our time-to-die < this x target's = break contact (0 = off)
MESH_COMMIT = 0.0             # ... target's time-to-die < this x ours (and <=1 hitter) = commit, ignore crowd retreat (0 = off)
MESH_ISO_W = 0.0              # tactic mesh: target score penalty per other known enemy within MESH_ISO_R of it (0 = off)
MESH_ISO_R = 80.0             # m
MESH_ISO_SKIP = 0             # ... don't open on a target with this many+ friends near it unless it hit us / is close (0 = off)
MESH_W = 5.0                  # s: trade-rate window
SQ_OUTGUN = False             # count "they have a laser and we don't" (beyond 55 m) as losing
LASER_JUKE = True            # boost-sidestep a visible laser charging at us (giddy-style; real bots may lead or lag)
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
        self._crates = {}
        self._myhp, self._ehp = [], {}  # (t, hp) histories for the live trade forecast
        self._fm_until = -1e9
        self._visited, self._explore_wp, self._explore_t = [], None, -1e9
        self._roofs, self._roof_done = [], set()
        if ROOF_T > 0:
            try:
                for (base, top, x0, y0, x1, y1, _) in world._p:
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    g = world.ground(cx, cy)
                    if (x1 - x0) * (y1 - y0) >= 300 and abs(world.top(cx, cy, 1e4) - top) < 0.6 and 4 < top - g <= ROOF_MAX_H:
                        self._roofs.append((cx, cy))
            except Exception as e:
                self._log("roofs", e)
                self._roofs = []
        self._start_alive, self._is_ffa = None, False
        self._stick_id, self._stick_t = None, -1e9
        self._hurt_t = self._threat_t = self._lose_t = -1e9
        self._fight_id, self._fight_t = None, -1e9
        self._evade_id, self._evade_t = None, 0.0
        self._beam_t = {}   # enemy id -> time of its last laser beam
        self._seen_t = -1e9   # last time a real enemy was visible
        self._runm = RUN_MODE
        self._run_spot = None # (t, point) RUN_MODE walks to after breaking line of sight
        self._kills = 0
        self._kill_t = -1e9
        self._dmg_t = -1e9      # last mech damage on us
        self._hits_on_us = []   # times of mech damage on us (ladder skill check)
        self._ladder_bad = set()  # ids that proved they can aim
        self._revealed_t, self._revealed_pos = -1e9, None  # last time/place we fired
        self._hunters = []
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
        self._tgt = None
        self._ladder = False
        try:
            action, mode = self._decide(obs)
        except Exception as e:  # last resort: brain bug, still return move/aim
            self._log("brain", e)
            try:
                action, mode = self._safe(obs), "safe"
            except Exception:  # obs itself is broken
                action, mode = {"move": [0.0, 0.0], "aim": [0.0, 0.0], "fire": [False, False]}, "safe"
        self._mode = mode
        if FIRE_POLICY and self._tgt is not None and any((action.get("fire") or [])):
            try:
                ok = self._ladder or self._may_fire(obs, self._tgt)
                if not ok:
                    action["fire"] = [False, False]
                elif ok == "return":
                    action["fire"] = self._prefer_gun(obs, self._tgt, action["fire"])
            except Exception as e:
                self._log("fire", e)
        if (self._runm or FIRE_POLICY) and isinstance(action, dict):
            try:
                me = obs["self"]
                if any(action.get("fire") or []):  # a shot is heard 320-420 m away: count it as being seen
                    self._revealed_t, self._revealed_pos = obs.get("t", 0.0), list(me["pos"])
                    self._seen_t = max(self._seen_t, self._revealed_t)
                if FIRE_POLICY and not self._ladder and action.get("reload") and self._hunters and self._exposed(obs, self._hunters):
                    action["reload"] = False  # reload out of sight
            except Exception as e:
                self._log("reveal", e)
        if DODGE:
            try:
                d = self._dodge(obs, action.get("move"))
                if d is not None:
                    action["move"] = d
            except Exception as e:
                self._log("dodge", e)
        if LASER_JUKE:
            try:
                me = obs["self"]
                p = me["pos"]
                jx = jy = 0.0
                for m in obs.get("mechs") or []:
                    if m.get("kind") != "mech" or not m.get("charging") or not m.get("aim") or not m.get("pos"):
                        continue
                    to_me = math.atan2(p[1] - m["pos"][1], p[0] - m["pos"][0])
                    if abs(_wrap(m["aim"][0] - to_me)) > 0.15:
                        continue
                    a = to_me + math.pi / 2 * self._strafe  # sidestep a laser charging at us
                    jx += math.cos(a)
                    jy += math.sin(a)
                L = math.hypot(jx, jy)
                if L > 0.01 and self._call(self.nav, "free_at", p[0] + 5 * jx / L, p[1] + 5 * jy / L, default=True):
                    mv = action.get("move") or [0.0, 0.0]
                    bx, by = 0.4 * mv[0] + jx / L, 0.4 * mv[1] + jy / L
                    bl = math.hypot(bx, by) or 1.0
                    action["move"] = [bx / bl, by / bl]
                    if me.get("energy", 0) > 25:
                        action["boost"] = True
            except Exception as e:
                self._log("laser_juke", e)
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
        survive = SQ_SURVIVE_T > 0 and t >= SQ_SURVIVE_T
        self._runm = RUN_MODE or survive
        me = obs["self"]
        pos = me["pos"]
        self._call(P, "update", obs)
        if PEEK_AFTER_BEAM or RELOAD_PUSH or LADDER:
            self._track_shots(obs, t)
        if REGEN_BREAK and any(ev.get("type") in ("damaged", "hit") for ev in obs.get("events") or ()):
            self._trade_t = t
        threats = getattr(P, "threats", None)
        threats = [x for x in threats if isinstance(x, dict) and x.get("pos")] if isinstance(threats, list) else []
        engaged = self._engaged = self._call(P, "engaged_by", t)
        threatened = self._call(P, "threatened_by", obs, self.world)
        visible = sorted((x for x in threats if x.get("visible")), key=lambda x: _dist(pos, x["pos"]))
        endgame = obs.get("alive", 16) <= END_ALIVE
        evs = obs.get("events") or ()
        if any(ev.get("type") == "damaged" and ev.get("weapon") != "zone" for ev in evs):
            self._dmg_t = t
        k = sum(ev.get("type") == "kill" for ev in evs)
        if k:
            self._kills, self._kill_t = self._kills + k, t
        if LADDER:
            self._hits_on_us = [x for x in self._hits_on_us if t - x < LADDER_ABORT_S] +                 [t for ev in evs if ev.get("type") == "damaged" and ev.get("by") is not None]
            if self._fight_id is not None and len(self._hits_on_us) >= LADDER_ABORT_HITS and self._mode == "ladder":
                self._ladder_bad.add(self._fight_id)
        if any(not x.get("virtual") for x in visible):
            self._seen_t = t
        foe = engaged or threatened
        if SQUAD_MODE and not survive and not self._ffa(obs):
            return self._decide_squad(obs, threats, t)

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
            hunters = self._hunters = [x for x in threats if not x.get("virtual")]
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

        # 1d'. Ladder: early on, kill hunters that look easy (gun only, few in view, no laser seen)
        if LADDER and t < LADDER_END_T and visible and self._kills < self._kill_cap():
            real = [x for x in visible if not x.get("virtual")]
            if real and len(visible) <= LADDER_MAX_SEEN and me.get("hp", 0) > LADDER_HP * (me.get("max_hp") or 1)                     and all((x.get("weapons") or []) == ["gun"] and not x.get("charging")
                            and x.get("id") not in self._beam_t and x.get("id") not in self._ladder_bad for x in real):
                self._ladder = True
                self._fight_id, self._fight_t = real[0].get("id"), t
                return self._fight(obs, real[0]), "ladder"

        # 1d. Run mode: never start a fight; fire back only when cornered or to finish a lone weak enemy
        # trace (r_run, seed 3): running under fire = few shots back, rear hits, death; so under fire fight/evade as usual
        if self._runm and t - self._dmg_t >= RUN_HIT_S and (hunters or (foe and not foe.get("virtual"))):
            if engaged and not engaged.get("virtual") and _dist(pos, engaged["pos"]) < CORNER_DIST:
                return self._fight(obs, engaged), "run-fight"
            v = visible[0] if len(visible) == 1 else None
            if v and not v.get("virtual") and v.get("hp") is not None and self._kills < self._kill_cap()                     and v["hp"] < RUN_FINISH * (v.get("max_hp") or 1e9)                     and not any(d.get("id") != v.get("id") for d in self._call(P, "danger", t, v["pos"], 150.0) or []):
                return self._fight(obs, v), "run-finish"
            hs = hunters or [foe]
            return self._hide(obs, hs, engaged, "run", fallback=self._far_point(obs, hs), reserve=RUN_ENERGY)
        if self._runm and t - self._seen_t < RUN_HIDE_S and not foe and t - self._dmg_t >= RUN_HIT_S:
            # nobody in view but the squad still remembers us: stay put, quiet, facing the last sighting
            cube = LADDER and t - self._kill_t < LADDER_CUBE_S and self._safe_cube(obs, threats)
            if cube:  # a ladder kill's drop
                return {**self._go(obs, cube), **self._aim(obs, threats, threatened, cube)}, "run-cube"
            if zg:  # zone travel wanted: go now, quietly
                return {**self._go(obs, zg[0], quiet=True), **self._aim(obs, threats, threatened, zg[0])}, "run-wait"
            rs = self._run_spot
            spot = rs[1] if rs and t - rs[0] < RUN_HIDE_S else pos
            rp = self._revealed_pos
            if rp and t - self._revealed_t < RUN_HIDE_S and _dist(spot, rp) < 40:
                spot = self._far_point(obs, [])  # never rest where we fired from
            dg = self._call(P, "danger", t, pos, 1e9) or []
            face = self._face(obs, _bearing(pos, dg[0]["pos"])) if dg else self._aim(obs, threats, threatened, spot)
            return {**self._go(obs, spot, quiet=True), **face}, "run-wait"

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
        farm = None if self._runm and t - self._seen_t < RUN_HIDE_S else self._farm_target(obs, threats, endgame)
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
            if DROP_SEEN_S > 0 and obs.get("t", 0.0) - self._seen_t < DROP_SEEN_S:
                continue
            if DROP_SAFE_R > 0 and self._call(self.perception, "danger", obs.get("t", 0.0), dp, DROP_SAFE_R):
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

    # --- squad mode (rules after giddygiddyboy's MIT bot, squadParams; our own implementation) ---

    def _decide_squad(self, obs, threats, t):
        act, mode = self._decide_squad_core(obs, threats, t)
        if SQ_SCAN > 0 and mode in ("roam", "explore", "crate-walk", "loot", "travel", "cube") \
                and "laser" not in _kinds(obs["self"]) and not any(x.get("visible") for x in threats):
            act["aim"] = [_wrap(t * SQ_SCAN), 0.0]  # our aim is our eyes: sweep 360 deg to find pickups
            act["fire"] = [False, False]
        if CHECK6_T > 0 and t < CHECK6_T and (t % CHECK6_P) < CHECK6_D                 and mode in ("roam", "explore", "crate-walk", "loot", "travel", "cube", "zone")                 and not any(x.get("visible") for x in threats) and act.get("aim"):
            act["aim"] = [_wrap(act["aim"][0] + math.pi), act["aim"][1] if len(act["aim"]) > 1 else 0.0]
        if SQ_PRECHARGE > 0 and mode not in ("fight", "fight:cube", "cornered", "npc", "farm", "crate")                 and t - self._threat_t < SQ_PRECHARGE:
            pre = self._call(self.combat, "precharge", obs)
            if pre:
                f = list(act.get("fire") or [False, False])
                act["fire"] = [bool(a) or bool(b) for a, b in zip(f, pre)]
        return act, mode

    def _decide_squad_core(self, obs, threats, t):
        """Practice vs the house squad: laser first, farm crates all match, engage hunters at our weapon's range,
        pick targets by distance and HP, retreat only while losing."""
        P, S, E = self.perception, self.survival, self.economy
        me = obs["self"]
        pos = me["pos"]
        hp, mhp = me.get("hp", 0.0), me.get("max_hp") or 1.0
        hf = hp / mhp
        self._call(E, "remember", obs)
        for c in obs.get("crates") or []:
            if c.get("id") is not None and c.get("pos"):
                self._crates[c["id"]] = (list(c["pos"]), t)
        vis_crates = {c.get("id") for c in obs.get("crates") or []}
        for i, (cp, ts) in list(self._crates.items()):
            if i not in vis_crates and (t - ts > 120 or _dist(cp, pos) < 35):
                del self._crates[i]
        for ev in obs.get("events") or ():
            if ev.get("type") == "damaged" and ev.get("weapon") != "zone":
                self._hurt_t = t
        kinds = _kinds(me)
        z = obs.get("zone") or {}
        late = (z.get("next_radius", 999) <= 70) or obs.get("alive", 16) <= 3
        hit_by = getattr(P, "hit_by", None)
        hit_by = hit_by if isinstance(hit_by, dict) else {}
        target, best, crowd, near, danger = None, 1e18, 0, 0, False
        visible = []
        for th in threats:
            if th.get("virtual") or t - th.get("last_seen", t) > 2.5:
                continue
            d = _dist(pos, th["pos"])
            vis = th.get("visible")
            if vis:
                visible.append(th)
                if d < 160:
                    near += 1
            ux, uy = pos[0] - th["pos"][0], pos[1] - th["pos"][1]
            L = math.hypot(ux, uy) or 1.0
            v = th.get("vel") or [0.0, 0.0, 0.0]
            closing = (v[0] * ux + v[1] * uy) / L
            aim = th.get("aim")
            aimed = bool(aim) and abs(_wrap(aim[0] - math.atan2(uy, ux))) < 0.22
            hitme = t - hit_by.get(th.get("id"), -1e9)
            thp, tmax = th.get("hp"), th.get("max_hp") or 1400.0
            low = thp is not None and thp < 0.4 * tmax
            back = bool(aim) and abs(_wrap(aim[0] - math.atan2(uy, ux))) > SQ_BACK_OFF
            scav = NOLASER_ENGAGE > 0 and "laser" not in kinds and not late
            engage = (d < (NOLASER_ENGAGE if scav else SQ_ENGAGE) or hitme < 6 or late or (low and d < 160)
                      or (not SQ_NO_POKE and not scav and ((closing > 3 and d < 180) or (aimed and d < 190)))
                      or (SQ_BACKSTAB > 0 and back and d < SQ_BACKSTAB and hf > 0.7))
            if engage or hitme < 4:
                danger = True
            if vis and (engage or d < 150):
                crowd += 1
            lz = "laser" in (th.get("weapons") or []) and "laser" not in kinds
            if SQ_LASER_HUNT > 0 and lz and vis and d < SQ_LH_RANGE and hf > SQ_LH_HP:
                engage = True  # it carries what we need: kill it and take the laser
            if SQ_LASER_AVOID and lz and hitme > 6 and d > SQ_ENGAGE and not low:
                engage = False  # no laser of our own: don't open on a laser holder that isn't on us
            friends = 0
            if MESH_ISO_W > 0 or MESH_ISO_SKIP > 0:
                friends = sum(1 for o in threats if o is not th and not o.get("virtual")
                              and t - o.get("last_seen", t) < 5 and _dist(o["pos"], th["pos"]) < MESH_ISO_R)
                if MESH_ISO_SKIP > 0 and friends >= MESH_ISO_SKIP and hitme > 6 and d > SQ_ENGAGE and not late and not low:
                    engage = False  # grouped: opening here pulls the whole group onto us
            if not (engage and vis and d < SQ_MAXT):
                continue
            sc = d + SQ_HPW * (thp if thp is not None else 1400.0)
            if thp is not None and thp <= 0.3 * tmax:
                sc -= SQ_LOWB
            if th.get("id") == self._stick_id and t - self._stick_t < 2:
                sc -= SQ_STICK
            if hitme < 4:
                sc -= 40
            if closing > 3:
                sc -= 15
            if SQ_LASER_AVOID and lz:
                sc += 80
            if SQ_LASER_HUNT > 0 and lz:
                sc -= SQ_LASER_HUNT  # prefer gun-only hunters while we have no laser
            if SQ_BACKSTAB > 0 and back:
                sc -= 60
            sc += MESH_ISO_W * friends  # its rear arc takes x1.5 and it hasn't reacted yet
            sk = self._call(P, "skill", th.get("id"), default=0.0) or 0.0
            if SQ_SKILL_W > 0:
                sc += SQ_SKILL_W * min(sk, 150.0)  # learned in-match: hunt the inaccurate ones first
            if sc < best:
                best, target = sc, th
        if target is not None:
            self._stick_id, self._stick_t = target.get("id"), t
        if danger or t - self._hurt_t < 3:
            self._threat_t = t
        td = _dist(pos, target["pos"]) if target else 1e9
        thp = target.get("hp") if target else None
        tmax = (target.get("max_hp") or 1400.0) if target else 1400.0
        finishing = target is not None and td < 120 and thp is not None and (thp < 200 or thp < 0.5 * hp)
        losing = (near >= 2 and hf < SQ_LOSE2) or (near >= 3 and hf < 0.8)
        if target is not None and thp is not None:
            tf = thp / tmax
            if hf < 0.35 and tf > hf + 0.1:
                losing = True
            if tf < 0.25 and hf > 0.2 and near <= 2:
                losing = False
        if (target is not None and "laser" in (target.get("weapons") or []) and "laser" not in kinds
                and td > 55 and hf < 0.8):
            losing = losing or SQ_OUTGUN
        if SQ_SKILL_DANGER > 0 and hf < 0.6 and not losing:
            for th in visible:
                if _dist(pos, th["pos"]) < 160 and (self._call(P, "skill", th.get("id"), default=0.0) or 0.0) > SQ_SKILL_DANGER:
                    losing = True  # an accurate (hard/expert) enemy and we're hurt: break contact
                    break
        if MESH_MULTI_HP > 0 or MESH_EDGE > 0 or MESH_COMMIT > 0:
            m = self._mesh(obs, t, target, hp, hf, hit_by, finishing)
            if m == "break":
                losing = True
            elif m == "commit":
                losing = False
        if losing:
            self._lose_t = t
        retreat = t - self._lose_t < 1.5

        # zone when it must happen now
        zg = self._call(S, "zone_goal", obs)
        urgent = bool(zg) and self._call(S, "zone_urgent", obs, zg[0], default=True)
        if zg and urgent:
            aim = self._attack(obs, target) if target else self._aim(obs, threats, None, zg[0])
            return {**self._go(obs, zg[0], boost=zg[1]), **aim}, "zone"
        if retreat and not finishing and not late:
            against = visible if visible else ([target] if target else [])
            cover = None if (self._slow() or not against) else self._call(S, "find_cover", obs, against)
            if cover:
                aim = self._attack(obs, target) if target else self._face(obs, _bearing(pos, cover))
                return {**self._go(obs, cover, boost=me.get("energy", 0) > 10), **aim}, "cover"
            if target is not None:
                return self._fight_at(obs, target, self._pref_range(kinds)), "cornered"
        if target is not None:
            rng = self._pref_range(kinds)
            if thp is not None and thp < 0.38 * tmax and hf > 0.42 and crowd <= 2:
                rng = SQ_FINISH
            if PEEK_LASER and not finishing and crowd <= PEEK_MAX_CROWD:
                pk = self._peek(obs, target, visible)
                if pk is not None:
                    return pk
            act = self._fight_at(obs, target, rng)
            r = 70.0 if hf > 0.5 else 40.0
            cube = self._nearest_cube(obs, r)
            if cube is not None:
                act.update(self._go(obs, cube))
                return act, "fight:cube"
            return act, "fight"
        npc = self._call(P, "npc_attacker", t)
        if npc and npc.get("pos"):
            return self._fight_at(obs, self._npc_target(npc), 60.0), "npc"
        if SQ_RESET_HP > 0 and hf < SQ_RESET_HP and not self._slow():
            # reset: hunters remember where we were; heal out of their sight before the next fight
            danger = self._call(P, "danger", t, pos, 220.0) or []
            if danger:
                cover = self._call(S, "find_cover", obs, danger)
                if cover:
                    quiet = _dist(pos, cover) < 3
                    return {**self._go(obs, cover, quiet=quiet),
                            **self._face(obs, _bearing(pos, danger[0]["pos"]))}, "reset"
        if zg:
            return {**self._go(obs, zg[0], boost=zg[1]), **self._aim(obs, threats, None, zg[0])}, "travel"
        if (SQ_DROPS and hf > 0.4) or (SITU_LOOT and self._loot_worth(obs, "drop", hf, threats, t)):
            dr = self._drop_target(obs, threats)
            if dr is not None and SITU_LOOT and not SQ_DROPS and (_dist(pos, dr) > 150
                    or self._call(P, "danger", t, dr, 120.0)):
                dr = None
            if dr is not None:
                return {**self._go(obs, dr), **self._aim(obs, threats, None, dr)}, "drop"
        # loot: a laser first, then wanted weapons, cubes, crates, drones
        want = self._call(E, "seek_laser", obs) or self._call(E, "wanted_pickup", obs, threats)
        if want and want.get("pos"):
            return {**self._go(obs, want["pos"], boost="laser" not in kinds and me.get("energy", 0) > EXPLORE_BOOST),
                    **self._aim(obs, threats, None, want["pos"])}, "loot"
        cube = self._nearest_cube(obs, SQ_LOOT * 0.7)
        if cube is not None:
            return {**self._go(obs, cube), **self._aim(obs, threats, None, cube)}, "cube"
        if ((SQ_DRONE_FIRST > 0 and hf > SQ_DRONE_FIRST) or (SITU_LOOT and self._loot_worth(obs, "drone", hf, threats, t)))                 and not danger:
            farm = self._farm_target(obs, threats, False)
            if farm and farm[1] == "npc":
                return self._fight_at(obs, farm[0], 70.0), "farm"
        scav_farm = NOLASER_FARM_HP > 0 and "laser" not in kinds and hf > NOLASER_FARM_HP and not late
        if (hf > SQ_FARM_HP and not danger) or scav_farm:
            cr = self.cfg.get("crates") or {}
            bc = None
            for i, (cp, ts) in self._crates.items():
                d = _dist(pos, cp)
                if d < SQ_LOOT and abs(cp[2] - pos[2]) < 4 and (bc is None or d < bc[0]):
                    bc = (d, cp, i)
            if bc is not None:
                d, cp, i = bc
                tgt = {"id": i, "pos": cp, "vel": [0.0, 0.0, 0.0], "center_h": cr.get("height", 2.4) / 2,
                       "radius": cr.get("radius", 1.4), "weapons": []}
                if i in vis_crates and d < 50:
                    if d < 12:
                        mv = {"move": [(pos[0] - cp[0]) / max(d, 0.1), (pos[1] - cp[1]) / max(d, 0.1)],
                              "boost": False, "jump": False}
                    elif d < 25:
                        mv = {"move": [0.0, 0.0], "boost": False, "jump": False}
                    else:
                        mv = self._go(obs, cp)
                    return {**mv, **self._attack(obs, tgt)}, "crate"
                return {**self._go(obs, cp), **self._aim(obs, threats, None, cp)}, "crate-walk"
        farm = self._farm_target(obs, threats, False)
        if farm and farm[1] == "npc" and hf > 0.6:
            return self._fight_at(obs, farm[0], 70.0), "farm"
        if ROOF_T > 0 and t < ROOF_T and "laser" not in kinds and self._roofs                 and (not SITU_LOOT or self._loot_worth(obs, "roof", hf, threats, t)):
            wp = self._roof_point(obs, t)
            if wp is not None and SITU_LOOT and _dist(pos, wp) > 60:
                wp = None
            if wp is not None:
                return {**self._go(obs, wp), **self._aim(obs, threats, None, wp)}, "roof"
        if SQ_HUNT_T > 0 and t < SQ_HUNT_T and "laser" not in kinds:
            wp = self._explore_point(obs, t)
            if wp is not None:
                return {**self._go(obs, wp, boost=me.get("energy", 0) > EXPLORE_BOOST), **self._aim(obs, threats, None, wp)}, "explore"
        hold = self._call(S, "hold_point", obs) or self._next_center(obs)
        return {**self._go(obs, hold), **self._aim(obs, threats, None, hold)}, "roam"

    def _mesh(self, obs, t, target, hp, hf, hit_by, finishing):
        """Live tactic switch from what the last few seconds showed: 'break', 'commit' or None."""
        h = self._myhp
        h.append((t, hp))
        while h and t - h[0][0] > MESH_W:
            h.pop(0)
        for th in obs.get("mechs") or ():
            i = th.get("id")
            if th.get("kind") == "mech" and th.get("hp") is not None:
                e = self._ehp.setdefault(i, [])
                e.append((t, th["hp"]))
                while e and t - e[0][0] > MESH_W:
                    e.pop(0)
        if finishing:
            return None
        hitters = sum(1 for ht in hit_by.values() if t - ht < MESH_HIT_S)
        if MESH_MULTI_HP > 0 and hitters >= 2 and hf < MESH_MULTI_HP:
            return "break"
        if target is None or not target.get("visible") or target.get("hp") is None:
            return None
        e = self._ehp.get(target.get("id")) or []
        if not e or t - e[0][0] < 2.0 or t - h[0][0] < 2.0:
            return None
        w = t - max(e[0][0], h[0][0])
        taken = h[0][1] - hp
        dealt = e[0][1] - target["hp"]
        if taken <= 0:
            return "commit" if MESH_COMMIT > 0 and dealt > 0 and hitters <= 1 else None
        my_ttd = hp * w / taken
        their_ttd = target["hp"] * w / max(dealt, 1.0)
        if MESH_EDGE > 0 and my_ttd < MESH_EDGE * their_ttd and hf < 0.8:
            return "break"
        if MESH_COMMIT > 0 and hitters <= 1 and their_ttd < MESH_COMMIT * my_ttd:
            return "commit"
        return None

    def _loot_worth(self, obs, kind, hf, threats, t):
        """Is this loot errand worth it right now? Value (HP need, an upgrade within reach, no laser yet)
        against risk (enemies in view, HP)."""
        me = obs["self"]
        cubes = me.get("cubes", 0) or 0
        th = [x for x in (getattr(self.economy, "thresholds", None) or [1, 3, 6, 10]) if x > cubes]
        need = (th[0] - cubes) if th else 99
        seen = any(x.get("visible") and not x.get("virtual") for x in threats)
        if kind == "drop":
            return hf < 0.6 or need <= 3
        if kind == "drone":
            return need <= 2 and hf > 0.6 and not seen
        if kind == "roof":
            return not seen and hf > 0.5
        return False

    def _roof_point(self, obs, t):
        """Nearest unvisited reachable roof inside the live circle; a roof counts as visited once we stand within 6 m."""
        pos = obs["self"]["pos"]
        wp = self._explore_wp
        if wp is not None and t - self._explore_t >= 30:
            self._roof_done.add((round(wp[0]), round(wp[1])))  # unreachable or too slow: skip it
        elif wp is not None:
            if _dist(pos, wp) < 6 or (pos[2] - (self.world.ground(pos[0], pos[1]) if self.world else 0)) > 3 and _dist(pos, wp) < 25:
                self._roof_done.add((round(wp[0]), round(wp[1])))
            elif (round(wp[0]), round(wp[1])) not in self._roof_done:
                return wp
        circle = self._call(self.survival, "live_circle", obs)
        best, bd = None, ROOF_R
        for cx, cy in self._roofs:
            if (round(cx), round(cy)) in self._roof_done:
                continue
            if circle and math.hypot(cx - circle[0][0], cy - circle[0][1]) > circle[1] - 30:
                continue
            d = math.hypot(cx - pos[0], cy - pos[1])
            if d < bd:
                best, bd = [cx, cy], d
        self._explore_wp, self._explore_t = best, t
        return best

    def _explore_point(self, obs, t):
        """A waypoint ~EXPLORE_M away, inside the current circle, far from where we've already been."""
        me = obs["self"]
        pos = me["pos"]
        if not self._visited or _dist(self._visited[-1], pos) > 25:
            self._visited.append([pos[0], pos[1]])
            self._visited = self._visited[-40:]
        wp = self._explore_wp
        if wp is not None and _dist(pos, wp) > 8 and t - self._explore_t < 25:
            return wp
        circle = self._call(self.survival, "live_circle", obs)
        best, bs = None, -1.0
        for k in range(12):
            a = k * math.pi / 6
            x, y = pos[0] + EXPLORE_M * math.cos(a), pos[1] + EXPLORE_M * math.sin(a)
            if circle:
                c, r = circle
                if math.hypot(x - c[0], y - c[1]) > r - 30:
                    continue
            if not self._call(self.nav, "free_at", x, y, default=True):
                continue
            sc = min((_dist(v, (x, y)) for v in self._visited), default=999.0)
            if sc > bs:
                best, bs = [x, y], sc
        self._explore_wp, self._explore_t = best, t
        return best

    def _peek(self, obs, target, visible):
        """Peek-laser cycle: while our laser is not ready, stand in cover from the target and charge; when it is
        full, return None so the normal fight steps out and fires. None also when there's no laser or no cover."""
        me = obs["self"]
        pos = me["pos"]
        las = next((w for w in me.get("weapons") or [] if w and w.get("kind") == "laser"), None)
        if las is None:
            return None
        st = las.get("stats") or (self.cfg.get("weapons") or {}).get("laser") or {}
        full = st.get("charge", 0.75)
        if las.get("charge", 0) >= full - 0.05 and las.get("cooldown", 0) <= 0.05:
            return None  # ready: swing out (normal fight) and fire
        if self._slow():
            return None
        cover = self._call(self.survival, "find_cover", obs, visible or [target])
        if not cover or _dist(pos, cover) > PEEK_COVER_M:
            return None
        act = {**self._go(obs, cover, boost=me.get("energy", 0) > 20 and _dist(pos, cover) > 4),
               **self._face(obs, _bearing(pos, target["pos"]))}
        pre = self._call(self.combat, "precharge", obs)
        if pre:
            act["fire"] = pre
        return act, "peek-hide"

    def _ffa(self, obs):
        """True once the match proves it is not squad practice: FFA_DEAD or more mechs died without us killing
        them (house-squad bots never fight each other, so in practice only we and drones remove them)."""
        if self._is_ffa:
            return True
        alive = obs.get("alive")
        if not isinstance(alive, int):
            return False
        if self._start_alive is None:
            self._start_alive = alive
        if self._start_alive - alive - self._kills >= FFA_DEAD:
            self._is_ffa = True
            mf.log("brain: free-for-all detected, squad mode off")
        return self._is_ffa

    def _pref_range(self, kinds):
        if "laser" in kinds:
            return SQ_LASER_RANGE
        if "lightning" in kinds:
            return SQ_LIGHT_RANGE
        return SQ_GUN_RANGE

    def _fight_at(self, obs, e, rng):
        d = _dist(obs["self"]["pos"], e["pos"])
        away = max(-0.7, min(0.8, (rng - d) / 30.0))
        if LASER_DUCK > 0 and e.get("charging") and e.get("visible") and not self._slow():
            cover = self._call(self.survival, "find_cover", obs, [e])
            if cover and _dist(obs["self"]["pos"], cover) <= LASER_DUCK:
                return {**self._go(obs, cover, boost=True), **self._gun_only(obs, e)}
        if SQ_HULL and self.world is not None and not self._slow():
            hd = self._hull_down(obs, e)
            if hd is not None:
                return {**hd, **self._attack(obs, e)}
        if SQ_FIGHTMOVE and self.world is not None and not self._slow():
            mv = self._fight_move(obs, e, rng)
            if mv is not None:
                return {**mv, **self._attack(obs, e)}
        return {**self._strafe_move(obs, e["pos"], away=away), **self._attack(obs, e)}

    def _hull_down(self, obs, tg):
        """Hull-down (reverse-slope) step: a spot within HULL_M where our muzzle sees the target's center but
        its eye can't see our center (shots aimed at our center hit the crest). Move there / hold; else None."""
        me = obs["self"]
        p = me["pos"]
        st = me.get("stats") or self.cfg.get("mech") or {}
        mh, eh, hh = st.get("muzzle_height", 7.0), st.get("eye_height", 8.0), st.get("height", 9.0)
        tp = tg["pos"]
        scale = 1 + ((self.cfg.get("cubes") or {}).get("size_per_cube", 0.05)) * (tg.get("cubes") or 0)
        tc = (tp[0], tp[1], tp[2] + hh * scale / 2)
        te = (tp[0], tp[1], tp[2] + eh * scale)
        w, nav = self.world, self.nav

        def good(x, y, z):
            return w.los((x, y, z + mh), tc) and not w.los(te, (x, y, z + hh / 2))

        if good(p[0], p[1], p[2]):
            return {"move": [0.0, 0.0], "boost": False, "jump": False}
        best = None
        for k in range(12):
            a = k * math.pi / 6
            for r in (4.0, HULL_M):
                x, y = p[0] + r * math.cos(a), p[1] + r * math.sin(a)
                if not self._call(nav, "free_at", x, y, default=True):
                    continue
                z = self._call(nav, "surface", x, y)
                z = p[2] if z is None else z
                if abs(z - p[2]) > 2.5:
                    continue
                if good(x, y, z):
                    if best is None or r < best[0]:
                        best = (r, x, y)
                    break
        if best is None:
            return None
        r, x, y = best
        return {"move": [(x - p[0]) / r, (y - p[1]) / r], "boost": False, "jump": False}

    def _fight_move(self, obs, tg, rng):
        """Score 16 steps of 6 m (and standing): keep the preferred range, keep line of sight to the target,
        stay out of sight of every other enemy, stay in the zone, drift toward cubes; strafe on ties.
        (Scoring after giddygiddyboy's MIT bot fightMove; our implementation.)"""
        me, t = obs["self"], obs.get("t", 0.0)
        p = me["pos"]
        st = me.get("stats") or self.cfg.get("mech") or {}
        mh, eh, hh = st.get("muzzle_height", 7.0), st.get("eye_height", 8.0), st.get("height", 9.0)
        w, nav = self.world, self.nav
        if t >= self._fm_until:
            if self.rng.random() < 0.6:
                self._strafe = -self._strafe
            self._fm_until = t + 0.3 + self.rng.random() * 0.7
        bx, by = tg["pos"][0] - p[0], tg["pos"][1] - p[1]
        bd = math.hypot(bx, by) or 1e-9
        ux, uy = bx / bd, by / bd
        sx, sy = -uy * self._strafe, ux * self._strafe
        tc = (tg["pos"][0], tg["pos"][1], tg["pos"][2] + hh / 2)
        others = [x for x in (getattr(self.perception, "threats", None) or [])
                  if isinstance(x, dict) and x.get("visible") and not x.get("virtual") and x.get("id") != tg.get("id")
                  and x.get("pos") and _dist(x["pos"], p) < 170]
        circle = self._call(self.survival, "live_circle", obs)
        cubes = [c["pos"] for c in obs.get("cubes") or [] if c.get("pos") and _dist(c["pos"], p) < 40
                 and abs(c["pos"][2] - p[2]) < 4]
        cube = min(cubes, key=lambda c: _dist(c, p)) if cubes else None
        best, bm, blocked = -1e18, None, False
        for k in range(-1, 16):
            if k >= 0:
                a = k * math.pi / 8
                dx, dy, r = math.cos(a), math.sin(a), 6.0
                cx, cy = p[0] + dx * r, p[1] + dy * r
                if not self._call(nav, "free_at", cx, cy, default=True) or \
                        not self._call(nav, "clear_line", (p[0], p[1]), (cx, cy), default=True):
                    if dx * sx + dy * sy > 0.9:
                        blocked = True
                    continue
            else:
                dx = dy = r = 0.0
                cx, cy = p[0], p[1]
            cz = self._call(nav, "surface", cx, cy) if k >= 0 else p[2]
            cz = p[2] if cz is None else cz
            d = math.hypot(tc[0] - cx, tc[1] - cy)
            sc = -1.1 * abs(d - rng) - r * 0.4
            if w.los((cx, cy, cz + mh), tc):
                sc += 45
            body = (cx, cy, cz + hh * 0.6)
            for e in others:
                if w.los((e["pos"][0], e["pos"][1], e["pos"][2] + eh), body):
                    sc -= SQ_FM_EXPOSE
            if circle:
                c, rr = circle
                out = math.hypot(cx - c[0], cy - c[1]) - (rr - 5)
                if out > 0:
                    sc -= 10 * out
            if cube is not None:
                sc += 1.5 * (_dist(cube, p) - math.hypot(cube[0] - cx, cube[1] - cy))
            sc += 9 * (dx * sx + dy * sy)
            if k < 0:
                sc -= 8
            if sc > best:
                best, bm = sc, (dx, dy)
        if blocked:
            self._strafe = -self._strafe
            self._fm_until = t + 0.5
        if bm is None:
            return None
        return {"move": [bm[0], bm[1]], "boost": False, "jump": False}

    def _nearest_cube(self, obs, r):
        p = obs["self"]["pos"]
        best, bd = None, r
        for c in obs.get("cubes") or []:
            cp = c.get("pos")
            if cp and abs(cp[2] - p[2]) < 6 and _dist(p, cp) < bd:
                best, bd = cp, _dist(p, cp)
        return best

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
        our_hp = me.get("hp")
        if not isinstance(our_hp, (int, float)) or our_hp <= 0:
            return 99.0
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
        our_hp = me.get("hp")
        if not isinstance(our_hp, (int, float)) or our_hp <= 0:
            return None
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

    def _may_fire(self, obs, e):
        """FIRE_POLICY: may we shoot mech e? Drones and crates (no weapons field) are always allowed."""
        if "weapons" not in e or e.get("virtual"):
            return "weapons" not in e
        t, fid = obs.get("t", 0.0), e.get("id")
        if t - self._dmg_t < RUN_HIT_S:
            return "return"  # under fire we're already found: shooting back costs no extra exposure
        if t - self._hit_t(fid) < FIRE_MEMORY or (e.get("visible") and e.get("charging")):
            return self._exposed(obs, [e]) and "return"  # return fire, unless we already broke its line of sight
        W, kinds = self.cfg.get("weapons") or {}, _kinds(obs["self"])
        g = W.get("gun") or {}
        shot = max((W.get("laser") or {}).get("damage", 315) if "laser" in kinds else 0,
                   g.get("damage", 45) * g.get("mag", 12) if "gun" in kinds else 0)
        return e.get("hp") is not None and e["hp"] <= shot and self._kills < self._kill_cap() and             not any(d.get("id") != fid for d in self._call(self.perception, "danger", t, e["pos"], 150.0) or [])

    def _prefer_gun(self, obs, e, fire):
        """Return fire with the gun only (no beam pointing back at us) unless the laser kills e."""
        ws = obs["self"].get("weapons") or []
        k = [w.get("kind") if w else None for w in ws]
        lz = ((self.cfg.get("weapons") or {}).get("laser") or {}).get("damage", 315)
        if "gun" not in k or (e.get("hp") is not None and e["hp"] <= lz):
            return fire
        return [bool(f) and i < len(k) and k[i] != "laser" for i, f in enumerate(fire)]

    def _exposed(self, obs, hunters):
        """True if any of the 5 nearest hunters has line of sight to us (map-free: any is visible)."""
        w, p = self.world, obs["self"]["pos"]
        if w is None:
            return any(h.get("visible") for h in hunters)
        eh = (self.cfg.get("mech") or {}).get("eye_height", 8)
        me = (p[0], p[1], p[2] + eh)
        near = sorted(hunters, key=lambda h: _dist(p, h["pos"]))[:5]
        return any(w.los((h["pos"][0], h["pos"][1], h["pos"][2] + eh), me) for h in near)

    def _far_point(self, obs, hunters):
        """Point at 0.6 x next radius around the next center, farthest from every known enemy."""
        z = obs.get("zone") or {}
        c, r = z.get("next_center") or obs["self"]["pos"][:2], 0.6 * (z.get("next_radius") or 0.0)
        ps = [h["pos"] for h in hunters] + ([self._revealed_pos] if self._revealed_pos else []) + [h["pos"] for h in self._call(self.perception, "danger", obs.get("t", 0.0),
                                                                          obs["self"]["pos"], 1e9) or []]
        pts = [[c[0] + r * math.cos(k * math.pi / 6), c[1] + r * math.sin(k * math.pi / 6)] for k in range(12)]
        return max(pts, key=lambda q: min((_dist(q, h) for h in ps), default=0.0))

    def _hide(self, obs, hunters, engaged, mode, fallback=None, reserve=-1.0):
        """Full speed to cover while exposed (returning gun fire if shot); once hidden walk quiet, hold fire."""
        p = obs["self"]["pos"]
        near = min(hunters, key=lambda h: _dist(p, h["pos"]))
        cover = None if self._slow() else self._call(self.survival, "find_cover", obs, hunters)
        if self._exposed(obs, hunters):
            aim = self._gun_only(obs, engaged) if engaged and not engaged.get("virtual")                 else self._face(obs, _bearing(p, near["pos"]))
            boost = obs["self"].get("energy", 0) > reserve
            return {**self._go(obs, cover or fallback or self._next_center(obs), boost=boost), **aim}, mode
        # hidden: walk quietly away (hunters head for our last known spot), else stay in cover
        goal = fallback or cover or p
        self._run_spot = (obs.get("t", 0.0), goal)
        return {**self._go(obs, goal, quiet=True), **self._face(obs, _bearing(p, near["pos"]))}, mode

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

    def _kill_cap(self):
        return LADDER_KILLS_MAX if LADDER else RUN_KILLS_MAX

    def _safe_cube(self, obs, threats):
        if self._call(self.economy, "cube_ok", obs) is False:
            return None
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
        self._tgt = e
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


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def _kinds(me):
    return [w.get("kind") for w in me.get("weapons") or [] if w]


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _bearing(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])
