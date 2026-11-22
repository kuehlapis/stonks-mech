import copy
import gzip
import json
import math
import statistics
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
from brain import Brain  # noqa: E402

STREAM = ROOT / "check" / "stream.jsonl.gz"


def load_stream():
    with gzip.open(STREAM, "rt") as f:
        msgs = [json.loads(line) for line in f if line.strip()]
    return msgs[0], [m for m in msgs if m.get("type") == "obs"]


HELLO, OBS = load_stream()
CFG = HELLO["config"]


class Fake:
    """Module double: attributes given as kwargs become methods returning that value."""
    def __init__(self, **ret):
        self.threats = ret.pop("threats", [])
        self._ret = ret

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a, **k: self._ret.get(name)


class Boom:
    def __getattr__(self, name):
        def f(*a, **k):
            raise RuntimeError("boom")
        return f


ENEMY = {"id": 7, "pos": [100.0, 0.0, 0.0], "vel": [0, 0, 0], "weapons": ["gun", "laser"], "hp": 500.0,
         "max_hp": 1400.0, "aim": [3.14, 0.0], "charging": False, "visible": True, "last_seen": 10.0, "virtual": False}


def obs0():
    o = copy.deepcopy(OBS[0])
    o["self"]["pos"] = [0.0, 0.0, 0.0]
    o["t"] = 10.0
    return o


def brain(perception=None, survival=None, economy=None):
    b = Brain(CFG, None, 3)
    b.perception = perception or Fake()
    b.survival = survival or Fake(hold_point=[50.0, 0.0])
    b.economy = economy or Fake()
    b.nav = Fake(step={"move": [1.0, 0.0], "boost": False, "jump": False})
    b.combat = Fake(attack={"aim": [0.0, 0.0], "fire": [True, True], "reload": False},
                    face={"aim": [0.5, 0.0], "fire": [False, False]})
    return b


class TestPriority(unittest.TestCase):
    def mode(self, b, o):
        import mechfight as mf
        mf.draw.clear()
        a = b.act(o)
        return a, mf.draw.take()["label"]

    def test_zero_hp_does_not_divide_in_ttk_ratio(self):
        b = brain(perception=Fake(threats=[ENEMY], engaged_by=ENEMY))
        o = obs0()
        o["self"]["hp"] = 0
        a = b.act(o)
        self.assertIn("move", a)
        self.assertIn("aim", a)

    def test_zone_outranks_loot(self):
        b = brain(survival=Fake(zone_goal=([0.0, 300.0], True), zone_urgent=True, hold_point=[50.0, 0.0]),
                  economy=Fake(wanted_pickup={"id": 1, "kind": "laser", "pos": [5.0, 0.0, 0.0]}))
        self.assertEqual(self.mode(b, obs0())[1], "zone")

    def test_loot_outranks_hold(self):
        b = brain(economy=Fake(wanted_pickup={"id": 1, "kind": "laser", "pos": [5.0, 0.0, 0.0]}, take={"take": 1}))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "loot")
        self.assertEqual(a["take"], 1)

    def test_threatened_goes_to_cover_without_firing(self):
        b = brain(perception=Fake(threats=[ENEMY], threatened_by=ENEMY),
                  survival=Fake(find_cover=[-20.0, 0.0], hold_point=[50.0, 0.0]))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "evade")
        self.assertEqual(a["fire"], [False, False])

    def test_laser_holder_engaged_evades_firing_back(self):
        b = brain(perception=Fake(threats=[ENEMY], engaged_by=ENEMY),
                  survival=Fake(find_cover=[-20.0, 0.0], hold_point=[50.0, 0.0]))
        o = obs0()
        a, m = self.mode(b, o)
        self.assertEqual(m, "evade")  # we lose the trade (gun vs gun + laser): break line of sight
        self.assertEqual(a["fire"], [True, True])  # EVADE_ALL: return fire with every weapon combat allows

    def test_engaged_no_cover_close_is_cornered_fight(self):
        e = dict(ENEMY, pos=[40.0, 0.0, 0.0])
        b = brain(perception=Fake(threats=[e], engaged_by=e))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "fight")  # too close to escape and the trade is near even: fight
        self.assertEqual(a["fire"], [True, True])

    def test_engaged_no_cover_far_flees(self):
        b = brain(perception=Fake(threats=[ENEMY], engaged_by=ENEMY))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "flee")
        self.assertTrue(a["boost"])
        self.assertEqual(a["fire"][1], False)

    def test_rule_b_fights_weak_gun_only_enemy(self):
        e = dict(ENEMY, weapons=["gun"])
        b = brain(perception=Fake(threats=[e], engaged_by=e), survival=Fake(find_cover=[-20.0, 0.0]))
        self.assertEqual(self.mode(b, obs0())[1], "fight")

    def test_no_take_while_engaged(self):
        b = brain(perception=Fake(threats=[ENEMY], engaged_by=ENEMY), economy=Fake(take={"take": 1}))
        self.assertNotIn("take", b.act(obs0()))

    def test_virtual_mortar_dodges_without_firing(self):
        e = dict(ENEMY, weapons=["mortar"], virtual=True, visible=False)
        b = brain(perception=Fake(threats=[e], engaged_by=e))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "dodge")
        self.assertEqual(a["fire"], [False, False])

    def test_zone_not_urgent_fights_first(self):
        e = dict(ENEMY, weapons=["gun"])
        b = brain(perception=Fake(threats=[e], engaged_by=e),
                  survival=Fake(zone_goal=([0.0, 300.0], False), zone_urgent=False, hold_point=[50.0, 0.0]))
        self.assertEqual(self.mode(b, obs0())[1], "fight")

    def test_offer_pick_merged(self):
        o = obs0()
        o["offer"] = {"id": 1, "choices": [], "expires": 15}
        a, _ = self.mode(brain(economy=Fake(pick=2)), o)
        self.assertEqual(a["pick"], 2)


class TestMoves(unittest.TestCase):
    mode = TestPriority.mode

    def setUp(self):
        import brain as B
        self.B = B
        self.saved = {k: getattr(B, k) for k in ("PEEK_AFTER_BEAM", "RELOAD_PUSH", "REAR_TURN", "BURN_ENDGAME", "REGEN_BREAK", "REGEN_HIDE", "BURN_QUIET", "RUN_MODE", "DROP_SAFE_R", "DROP_SEEN_S", "FIRE_POLICY", "LADDER")}

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(self.B, k, v)

    def test_peek_after_beam_pushes_instead_of_evading(self):
        self.B.PEEK_AFTER_BEAM = True
        b = brain(perception=Fake(threats=[ENEMY], engaged_by=ENEMY), survival=Fake(find_cover=[-20.0, 0.0]))
        o = obs0()
        o["beams"] = [{"by": 7, "kind": "laser", "path": [[100, 0, 7], [0, 0, 7]], "age": 0.05}]
        self.assertEqual(self.mode(b, o)[1], "push")
        o["t"] = 12.0  # cooldown 1.65 s over
        o["beams"] = []
        self.assertEqual(self.mode(b, o)[1], "evade")

    def test_reload_push_after_gun_burst(self):
        self.B.RELOAD_PUSH = True
        e = dict(ENEMY, weapons=["gun"])
        b = brain(perception=Fake(threats=[e], engaged_by=e))
        o = obs0()
        for i in range(12):
            o["t"] = 10.0 + 0.24 * i
            o["events"] = [{"type": "damaged", "amount": 45, "weapon": "gun", "bearing": 0.0, "by": 7}]
            b._track_shots(o, o["t"])
        o["events"] = []
        o["t"] += 0.3
        self.assertFalse(b._push_window(o, e))  # could still be firing
        o["t"] += 0.8
        self.assertTrue(b._push_window(o, e))
        o["t"] += 2.0
        self.assertFalse(b._push_window(o, e))  # reload over

    def test_rear_turn_faces_bearing(self):
        self.B.REAR_TURN = True
        o = obs0()
        o["events"] = [{"type": "damaged", "amount": 45, "weapon": "gun", "bearing": 2.5, "by": 9, "rear": True}]
        a, _ = self.mode(brain(), o)
        self.assertEqual(a["aim"][0], 2.5)

    def test_burn_endgame_holds_center(self):
        self.B.BURN_ENDGAME = True
        e = dict(ENEMY, weapons=["gun"])
        b = brain(perception=Fake(threats=[e], engaged_by=e))
        o = obs0()
        o["t"] = 380.0
        a, m = self.mode(b, o)
        self.assertEqual(m, "burn")
        self.assertFalse(a["fire"][1])  # gun only

    def test_regen_break_skips_open_fight(self):
        self.B.REGEN_BREAK = True
        e = dict(ENEMY, weapons=["gun"], pos=[60.0, 0.0, 0.0], hp=100.0)
        b = brain(perception=Fake(threats=[e]))
        o = obs0()
        o["self"]["hp"] = 900
        o["events"] = [{"type": "hit", "target": 7, "amount": 45, "weapon": "gun"}]
        self.assertNotIn(self.mode(b, o)[1], ("finish", "open"))
        o["events"] = []
        o["t"] = 16.0
        self.assertIn(self.mode(b, o)[1], ("finish", "open"))

    def test_regen_hide_runs_then_goes_quiet(self):
        self.B.REGEN_BREAK = self.B.REGEN_HIDE = True
        e = dict(ENEMY, weapons=["gun"])
        b = brain(perception=Fake(threats=[e]), survival=Fake(find_cover=[-20.0, 0.0]))
        o = obs0()
        o["self"]["hp"] = 900
        o["events"] = [{"type": "hit", "target": 7, "amount": 45, "weapon": "gun"}]
        a, m = self.mode(b, o)
        self.assertEqual(m, "regen-hide")
        self.assertEqual(a["fire"], [False, False])  # seen but not shot: run, don't fire
        o["events"] = []
        e["visible"] = False  # out of its sight now
        a, m = self.mode(b, o)
        self.assertEqual(m, "regen-hide")
        self.assertEqual(a["fire"], [False, False])

    def test_burn_quiet_fires_only_when_exposed(self):
        self.B.BURN_ENDGAME = self.B.BURN_QUIET = True
        e = dict(ENEMY, weapons=["gun"])
        b = brain(perception=Fake(threats=[e], engaged_by=e), survival=Fake(find_cover=[-20.0, 0.0]))
        o = obs0()
        o["t"] = 380.0
        a, m = self.mode(b, o)
        self.assertEqual(m, "burn-quiet")
        self.assertTrue(a["fire"][0])  # exposed and shot at: return gun fire
        e["visible"] = False
        b.perception = Fake(threats=[e])
        a, m = self.mode(b, o)
        self.assertEqual(a["fire"], [False, False])

    def test_run_mode_runs_unless_weak(self):
        self.B.RUN_MODE = True
        e = dict(ENEMY, weapons=["gun"], pos=[90.0, 0.0, 0.0], hp=1000.0)
        b = brain(perception=Fake(threats=[e]))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "run")
        self.assertEqual(a["fire"], [False, False])
        e["hp"] = 300.0  # < 35% of 1400
        self.assertEqual(self.mode(b, obs0())[1], "run-finish")

    def test_drop_safe_r_skips_remembered_enemy(self):
        o = obs0()
        o["drops"] = [{"id": 1, "pos": [30.0, 0.0, 0.0], "radius": 8, "lands_in": 10, "capture_s": 4, "progress": 0, "holder": None}]
        b = brain(perception=Fake(danger=[{"id": 9, "pos": [60.0, 0.0, 0.0]}]))
        self.assertIsNotNone(b._drop_target(o, []))
        self.B.DROP_SAFE_R = 80.0
        self.assertIsNone(b._drop_target(o, []))

    def test_run_mode_waits_hidden_and_skips_farm(self):
        self.B.RUN_MODE = True
        b = brain(perception=Fake(threats=[dict(ENEMY, weapons=["gun"], hp=1000.0)]))
        self.assertEqual(self.mode(b, obs0())[1], "run")
        b.perception = Fake(threats=[])  # lost sight of it
        o = obs0()
        o["t"] = 30.0
        a, m = self.mode(b, o)
        self.assertEqual(m, "run-wait")
        self.assertEqual(a["fire"], [False, False])
        o["t"] = 41.0  # 31 s after the sighting: free again
        self.assertNotEqual(self.mode(b, o)[1], "run-wait")
        b._seen_t = 40.0
        self.B.DROP_SEEN_S = 10.0
        o["drops"] = [{"id": 1, "pos": [30.0, 0.0, 0.0], "radius": 8, "lands_in": 10, "capture_s": 4, "progress": 0, "holder": None}]
        self.assertIsNone(b._drop_target(o, []))

    def test_run_wait_spot_expires_and_zone_travels_quietly(self):
        self.B.RUN_MODE = True
        b = brain(perception=Fake(threats=[]))
        b._seen_t, b._run_spot = 5.0, (-30.0, [200.0, 0.0])  # spot older than RUN_HIDE_S
        o = obs0()
        b.nav = Fake(step=None)  # map-free straight-line move: shows the goal
        a, m = self.mode(b, o)
        self.assertEqual((m, a["move"]), ("run-wait", [0.0, 0.0]))  # holds where it is
        b.survival = Fake(zone_goal=([0.0, 300.0], False), zone_urgent=False)
        a, m = self.mode(b, o)
        self.assertEqual(m, "run-wait")
        self.assertAlmostEqual(a["move"][1], 0.4)  # toward the zone, quiet speed

    def test_fire_policy(self):
        self.B.FIRE_POLICY = True
        b = brain()
        passive = dict(ENEMY, hp=1000.0)
        self.assertFalse(b._may_fire(obs0(), passive))  # never the first shot
        weak = dict(ENEMY, hp=200.0)
        self.assertTrue(b._may_fire(obs0(), weak))  # one laser shot (315) kills it, nobody else near
        b.perception = Fake(danger=[{"id": 9, "pos": [120.0, 0.0, 0.0]}])
        self.assertFalse(b._may_fire(obs0(), weak))
        self.assertTrue(b._may_fire(obs0(), {"id": 101, "pos": [1, 0, 0]}))  # drone

    def test_fire_reveals_and_return_fire_prefers_gun(self):
        self.B.FIRE_POLICY = self.B.RUN_MODE = True
        b = brain()
        o = obs0()
        o["self"]["weapons"] = [{"kind": "gun"}, {"kind": "laser"}]
        e = dict(ENEMY, hp=1000.0)
        self.assertEqual(b._prefer_gun(o, e, [True, True]), [True, False])
        self.assertEqual(b._prefer_gun(o, dict(e, hp=100.0), [True, True]), [True, True])  # laser kills
        o["zone"] = dict(o["zone"], next_center=[0.0, 0.0], next_radius=200.0)
        b._seen_t, b._run_spot = 9.0, (9.0, [5.0, 0.0])
        b._revealed_t, b._revealed_pos = 9.0, [0.0, 0.0, 0.0]  # we just fired from here
        b.nav = Fake(step=None)
        a, m = self.mode(b, o)
        self.assertEqual(m, "run-wait")
        self.assertGreater(math.hypot(*a["move"]), 0.1)  # walking away from the firing spot

    def test_ladder_fights_gun_only_and_runs_from_laser(self):
        self.B.LADDER = self.B.RUN_MODE = self.B.FIRE_POLICY = True
        gun = dict(ENEMY, weapons=["gun"], hp=1000.0, pos=[130.0, 0.0, 0.0])
        b = brain(perception=Fake(threats=[gun]))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "ladder")
        self.assertTrue(any(a["fire"]))  # FIRE_POLICY bypassed: we shoot first
        b = brain(perception=Fake(threats=[dict(gun, weapons=["gun", "laser"])]))
        self.assertEqual(self.mode(b, obs0())[1], "run")
        b = brain(perception=Fake(threats=[gun]))
        o = obs0()
        self.assertEqual(self.mode(b, o)[1], "ladder")
        o["events"] = [{"type": "damaged", "amount": 45, "weapon": "gun", "bearing": 0.0, "by": 7}] * 2
        self.mode(b, o)
        o["events"] = []
        o["t"] += 4.0  # past RUN_HIT_S
        self.assertEqual(self.mode(b, o)[1], "run")  # it can aim: off the ladder


class TestRobust(unittest.TestCase):
    def test_raising_modules_still_move_and_aim(self):
        b = brain()
        for name in ("perception", "survival", "nav", "combat", "economy"):
            setattr(b, name, Boom())
            o = obs0()
            o["offer"] = {"id": 1, "choices": [], "expires": 15}
            a = b.act(o)
            self.assertIn("move", a)
            self.assertIn("aim", a)
            json.dumps(a)

    def test_broken_obs(self):
        a = brain().act({"t": 1.0})
        self.assertIn("move", a)
        self.assertIn("aim", a)


class TestTiming(unittest.TestCase):
    def test_stream_timing(self):
        b = Brain(CFG, None, int(HELLO["slot"]))
        try:
            from world import World
            b = Brain(CFG, World(str(ROOT / "arena")), int(HELLO["slot"]))
        except Exception:
            pass
        ms = []
        for o in OBS:
            t0 = time.perf_counter()
            a = b.act(o)
            ms.append((time.perf_counter() - t0) * 1000)
            self.assertIn("move", a)
        ms.sort()
        mean, p99 = statistics.mean(ms), ms[int(len(ms) * 0.99) - 1]
        print(f"\nbrain act(): mean {mean:.2f} ms, p99 {p99:.2f} ms, max {ms[-1]:.2f} ms over {len(ms)} obs",
              file=sys.stderr)
        self.assertLessEqual(mean, 15)
        self.assertLessEqual(p99, 35)


if __name__ == "__main__":
    unittest.main()
