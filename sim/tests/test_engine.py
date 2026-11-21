import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from engine import Match, Zone, is_rear, placements, seg_cyl  # noqa: E402
from run import FlatWorld, recorded_hello  # noqa: E402

CFG = recorded_hello()["config"]


class TestZone(unittest.TestCase):
    def setUp(self):
        self.z = Zone(CFG["zone"], random.Random(3), FlatWorld().bounds, 30)

    def test_interpolation(self):
        t0, ts, te, c, r, nc, nr, dps = self.z.phases[0]
        self.assertEqual((ts, te, r, nr, dps), (60, 110, 560, 380, 20))
        self.assertEqual(self.z.circle(30)[:3], (c[0], c[1], 560))
        mid = self.z.circle(85)
        self.assertAlmostEqual(mid[2], 470)
        self.assertAlmostEqual(mid[0], (c[0] + nc[0]) / 2)
        self.assertAlmostEqual(self.z.circle(110)[2], 380)  # phase 2 holds at the circle phase 1 shrank to
        o = self.z.obs(110)
        self.assertEqual((o["radius"], o["next_radius"], o["shrink_start"], o["shrink_end"], o["dps"]), (380, 240, 155, 195, 35))

    def test_nested_and_final(self):
        for _, _, _, c, r, nc, nr, _ in self.z.phases:
            self.assertLessEqual(math.dist(c, nc) + nr, r + 1e-9)
        self.assertEqual(self.z.circle(1e4)[2:], (0, 260))


class TestGeometry(unittest.TestCase):
    def test_seg_cyl(self):
        c = (0, 0, 0)
        self.assertAlmostEqual(seg_cyl((-10, 0, 4), (10, 0, 4), c, 2.8, -0.3, 9.3), 7.2 / 20)
        self.assertIsNone(seg_cyl((-10, 3, 4), (10, 3, 4), c, 2.8, -0.3, 9.3))   # passes beside
        self.assertIsNone(seg_cyl((-10, 0, 10), (10, 0, 10), c, 2.8, -0.3, 9.3))  # passes over the head
        self.assertAlmostEqual(seg_cyl((0, 0, 20), (0, 0, 0), c, 2.8, -0.3, 9.3), (20 - 9.3) / 20)  # from above
        self.assertEqual(seg_cyl((0, 0, 4), (1, 0, 4), c, 2.8, -0.3, 9.3), 0.0)  # starts inside
        self.assertIsNone(seg_cyl((-20, 0, 4), (-12, 0, 4), c, 2.8, -0.3, 9.3))  # stops short

    def test_rear(self):
        self.assertFalse(is_rear(0.0, 0.0, 180))
        self.assertFalse(is_rear(math.radians(89), 0.0, 180))
        self.assertTrue(is_rear(math.radians(91), 0.0, 180))
        self.assertTrue(is_rear(math.pi, 0.0, 180))
        self.assertFalse(is_rear(-3.0, 3.0, 180))  # wraps across +-pi


def duel(target_yaw):
    """Mech 0 at the origin aims east at mech 1, 60 m away, facing target_yaw; no spread."""
    cfg = dict(CFG, weapons=dict(CFG["weapons"], gun=dict(CFG["weapons"]["gun"], spread_deg=0)))
    m = Match(cfg, FlatWorld(), 1, 2)
    a, b = m.mechs
    a.pos, b.pos = [0.0, 0.0, 0.0], [60.0, 0.0, 0.0]
    a.aim = a.aim_cmd = [0.0, 0.0]
    b.aim = b.aim_cmd = [target_yaw, 0.0]
    m.apply_action(a, {"fire": [True, False], "aim": [0.0, 0.0]})
    m.apply_action(b, {"aim": [target_yaw, 0.0]})
    for _ in range(10):
        m.step()
    return m


class TestGun(unittest.TestCase):
    def test_front_hit(self):
        m = duel(math.pi)  # target faces the shooter
        b = m.mechs[1]
        dmg = [e for e in b.events if e["type"] == "damaged"]
        self.assertTrue(dmg)
        self.assertEqual(dmg[0]["amount"], 45)
        self.assertNotIn("rear", dmg[0])
        self.assertAlmostEqual(abs(dmg[0]["bearing"]), math.pi, places=2)  # came from the west
        self.assertEqual(m.mechs[0].ammo, 12 - 3)  # 10 ticks of held trigger at 0.24 s: t=0, 0.25, 0.5 -> 3 shots

    def test_rear_hit(self):
        b = duel(0.0).mechs[1]  # target faces away
        dmg = [e for e in b.events if e["type"] == "damaged"]
        self.assertEqual(dmg[0]["amount"], 67.5)
        self.assertTrue(dmg[0]["rear"])
        self.assertAlmostEqual(b.dmg_rear, b.dmg_taken)


class TestPlacement(unittest.TestCase):
    def test_ties(self):
        # 4 mechs: 0 dies first alone, 1 and 2 die on the same tick, 3 survives
        p = placements({0: 10, 1: 20, 2: 20, 3: None}, {0: 0, 1: 0, 2: 0, 3: 500}, {0: 4, 1: 3, 2: 3})
        self.assertEqual(p, {0: 4, 1: 3, 2: 3, 3: 1})

    def test_time_limit_hp(self):
        p = placements({0: 5, 1: None, 2: None, 3: None}, {0: 0, 1: 900, 2: 1200, 3: 900}, {0: 4})
        self.assertEqual(p, {0: 4, 2: 1, 1: 2, 3: 2})


class TestTiming(unittest.TestCase):
    def test_coast_then_idle(self):
        m = Match(CFG, FlatWorld(), 1, 2)
        a = m.mechs[0]
        m.apply_action(a, {"move": [1, 0], "boost": True, "fire": [True, False], "aim": [1.0, 0.0]})
        m.apply_action(a, None)
        self.assertEqual((a.move, a.boost, a.fire, a.aim_cmd), ([1.0, 0.0], True, False, [1.0, 0.0]))
        m.tick = 22  # 1.1 s after the last answer
        m.apply_action(a, None)
        self.assertEqual((a.move, a.boost, a.aim_cmd), ([0.0, 0.0], False, a.aim))

    def test_bad_action_fields(self):
        m = Match(CFG, FlatWorld(), 1, 2)
        a = m.mechs[0]
        m.apply_action(a, {"move": "x", "aim": [float("nan"), 0], "fire": 1, "boost": "yes"})
        self.assertEqual((a.move, a.boost, a.fire), ([0.0, 0.0], False, False))


if __name__ == "__main__":
    unittest.main()
