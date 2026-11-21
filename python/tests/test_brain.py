import copy
import gzip
import json
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

    def test_zone_outranks_loot(self):
        b = brain(survival=Fake(zone_goal=([0.0, 300.0], True), hold_point=[50.0, 0.0]),
                  economy=Fake(wanted_pickup={"id": 1, "kind": "laser", "pos": [5.0, 0.0, 0.0]}))
        self.assertEqual(self.mode(b, obs0())[1], "zone")

    def test_zone_path_cannot_steer_outside_live_circle(self):
        o = obs0()
        o["self"]["pos"] = [90.0, 0.0, 0.0]
        o["self"]["in_zone"] = True
        s = Fake(zone_goal=([200.0, 0.0], True), live_circle=([0.0, 0.0], 100.0))
        b = brain(survival=s)
        a, mode = self.mode(b, o)
        self.assertEqual(mode, "zone")
        self.assertEqual(a["move"], [-1.0, 0.0])

    def test_loot_outranks_hold(self):
        b = brain(economy=Fake(wanted_pickup={"id": 1, "kind": "laser", "pos": [5.0, 0.0, 0.0]}, take={"take": 1}))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "loot")
        self.assertEqual(a["take"], 1)

    def test_threatened_goes_to_cover_without_firing(self):
        b = brain(perception=Fake(threats=[ENEMY], threatened_by=ENEMY),
                  survival=Fake(find_cover=[-20.0, 0.0], hold_point=[50.0, 0.0]))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "cover")
        self.assertEqual(a["fire"], [False, False])

    def test_laser_holder_engages_gun_only_disengages(self):
        b = brain(perception=Fake(threats=[ENEMY], engaged_by=ENEMY),
                  survival=Fake(find_cover=[-20.0, 0.0], hold_point=[50.0, 0.0]))
        o = obs0()
        a, m = self.mode(b, o)
        self.assertEqual(m, "disengage")
        self.assertEqual(a["fire"][1], False)  # slot 1 empty; slot 0 gun may fire back

    def test_engaged_no_cover_is_cornered_fight(self):
        close = dict(ENEMY, pos=[50.0, 0.0, 0.0])
        b = brain(perception=Fake(threats=[close], engaged_by=close))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "fight")
        self.assertEqual(a["fire"], [True, True])

    def test_engaged_no_cover_distant_threat_flees(self):
        b = brain(perception=Fake(threats=[ENEMY], engaged_by=ENEMY))
        a, m = self.mode(b, obs0())
        self.assertEqual(m, "flee")
        self.assertEqual(a["move"], [-1.0, 0.0])
        self.assertTrue(a["boost"])

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

    def test_offer_pick_merged(self):
        o = obs0()
        o["offer"] = {"id": 1, "choices": [], "expires": 15}
        a, _ = self.mode(brain(economy=Fake(pick=2)), o)
        self.assertEqual(a["pick"], 2)


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
    def test_slow_tick_reuses_recent_cover(self):
        b = brain()
        p = [-20.0, 0.0, 0.0]
        b._last_cover = (10.0, [list(ENEMY["pos"])], p)
        b._tick_started = time.perf_counter() - 0.031
        self.assertEqual(b._find_cover(obs0(), [ENEMY]), p)

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
