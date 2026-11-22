import copy
import gzip
import json
import math
import random
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
from survival import Survival  # noqa: E402
from world import World  # noqa: E402
from nav import Nav  # noqa: E402
import survival as SV  # noqa: E402

BUILDING = (-114.5, 62.0)  # real prism in arena/v2/world.json (see test_world.py)
WALL = (-118.15, 60.85)    # its west wall midpoint
OUT = (-0.992, -0.126)     # outward normal, open ground for about 60 m


def _out(d):
    return (WALL[0] + d * OUT[0], WALL[1] + d * OUT[1])


with gzip.open(ROOT / "check" / "stream.jsonl.gz", "rt") as f:
    CFG = json.loads(f.readline())["config"]
    OBS0 = json.loads(f.readline())
WORLD = World(str(ROOT / "arena"))
NAV = Nav(CFG, WORLD)
MARGIN = OBS0["self"]["stats"]["radius"] + 12


def obs(pos, t=0.0, in_zone=True, **zone):
    o = copy.deepcopy(OBS0)
    o["t"] = t
    o["self"]["pos"] = list(pos) if len(pos) == 3 else [pos[0], pos[1], WORLD.ground(*pos)]
    o["self"]["in_zone"] = in_zone
    o["zone"].update(zone)
    return o


def threat(xy, z_off=0.0):
    return {"id": 1, "pos": [xy[0], xy[1], WORLD.ground(*xy) + z_off], "vel": [0, 0, 0]}


class CountingWorld:
    """Real world, but los is counted and can be forced visible for one threat eye."""
    def __init__(self, see_from=None):
        self.calls, self.see_from = 0, see_from

    def __getattr__(self, k):
        return getattr(WORLD, k)

    def los(self, a, b):
        self.calls += 1
        if self.see_from is not None:
            return math.hypot(a[0] - self.see_from[0], a[1] - self.see_from[1]) < 1e-6
        return WORLD.los(a, b)


class TestHoldPoint(unittest.TestCase):
    def test_radius_zero_is_center(self):
        s = Survival(CFG, WORLD)
        o = obs((100, 100), next_center=[0.0, 0.0], next_radius=0)
        self.assertEqual(s.hold_point(o), [0.0, 0.0])
        self.assertEqual(Survival(CFG, None).hold_point(o), [0.0, 0.0])

    def test_clamp_and_inside(self):
        s = Survival(CFG, None)
        p = s.hold_point(obs((300, 0), next_center=[0.0, 0.0], next_radius=100))
        self.assertAlmostEqual(p[0], 100 - MARGIN)
        self.assertAlmostEqual(p[1], 0)
        p = s.hold_point(obs((20, 0), next_center=[0.0, 0.0], next_radius=100))  # already deeper: stay
        self.assertAlmostEqual(p[0], 20)

    def test_snaps_off_building(self):
        nc = [BUILDING[0] + 55, BUILDING[1]]
        o = obs((BUILDING[0] - 100, BUILDING[1]), next_center=nc, next_radius=55 + MARGIN)
        raw = Survival(CFG, None).hold_point(o)
        st = OBS0["self"]["stats"]
        self.assertTrue(WORLD.blocked(raw[0], raw[1], WORLD.ground(*raw), st["radius"], st["height"], st["step_up"]))
        p = Survival(CFG, WORLD).hold_point(o)
        self.assertFalse(WORLD.blocked(p[0], p[1], WORLD.ground(*p), st["radius"], st["height"], st["step_up"]))
        self.assertGreater(p[0], raw[0])  # moved toward the center
        self.assertLess(p[0], nc[0])


class TestZone(unittest.TestCase):
    def test_outside_zone_goes_to_next_center(self):
        s = Survival(CFG, None)
        o = obs((600, -72.8), in_zone=False)
        goal, boost = s.zone_goal(o)
        self.assertEqual(goal, s.hold_point(o))  # the hold point inside the next circle (stable goal)
        self.assertFalse(boost)  # 0 m outside the 560 circle: no eta
        o = obs((2000, -72.8), in_zone=False)
        self.assertTrue(s.zone_goal(o)[1])  # far out: dps x eta > 0.2 hp

    def test_inside_next_circle_none(self):
        s = Survival(CFG, None)
        self.assertIsNone(s.zone_goal(obs(OBS0["zone"]["next_center"])))

    def test_outside_next_circle_goes_to_hold_point(self):
        s = Survival(CFG, None)
        o = obs((400, -72.8), t=0)
        goal, boost = s.zone_goal(o)
        self.assertEqual(goal, s.hold_point(o))
        self.assertFalse(boost)
        self.assertTrue(s.zone_goal(obs((400, -72.8), t=58))[1])  # late: boost

    def test_live_circle_uses_saved_values(self):
        s = Survival(CFG, None)
        z = OBS0["zone"]
        s.live_circle(obs((0, 0), t=59))
        # mid-shrink the server may move obs.zone.center; we must ignore it
        c, r = s.live_circle(obs((0, 0), t=85, center=[999.0, 999.0], radius=1.0))
        self.assertAlmostEqual(r, (z["radius"] + z["next_radius"]) / 2)
        self.assertAlmostEqual(c[0], (z["center"][0] + z["next_center"][0]) / 2)

    def test_hold_facing(self):
        s = Survival(CFG, None)
        nc = OBS0["zone"]["next_center"]
        o = obs((nc[0] + 100, nc[1]), t=0)  # 100 m east of next center, far from the 560 edge
        self.assertLessEqual(abs(s.hold_facing(o)), math.radians(60) + 1e-9)  # outward = east ± 60°
        o = obs((nc[0] + 100, nc[1]), t=200, center=nc, radius=110, next_radius=50, shrink_start=300, shrink_end=330)
        self.assertAlmostEqual(abs(s.hold_facing(o)), math.pi)  # edge 10 m away: inward = west

    def test_final_center(self):
        s = Survival(CFG, None)
        self.assertIsNone(s.final_center(OBS0))
        self.assertEqual(s.final_center(obs((0, 0), next_center=[5.0, 6.0], next_radius=0)), [5.0, 6.0])


class TestCover(unittest.TestCase):
    def test_finds_point_behind_building(self):
        cw = CountingWorld()
        s = Survival(CFG, cw)
        s.nav = NAV
        th = threat(_out(40))
        me = _out(5)
        o = obs(me)
        eye = (th["pos"][0], th["pos"][1], th["pos"][2] + 8)
        self.assertTrue(WORLD.los(eye, (me[0], me[1], WORLD.ground(*me) + 4.5)))  # exposed now
        p = s.find_cover(o, [th])
        self.assertIsNotNone(p)
        self.assertFalse(WORLD.los(eye, (p[0], p[1], p[2] + 4.5)))
        self.assertFalse(WORLD.los(eye, (p[0], p[1], p[2] + 9)))
        self.assertLessEqual(cw.calls, SV.LOS_CAP)
        n = cw.calls
        self.assertEqual(s.find_cover(obs(me, t=0.5), [th]), p)  # cached
        self.assertEqual(cw.calls, n)
        moved = threat(_out(55))
        s.find_cover(obs(me, t=0.6), [moved])  # threat moved 15 m: new search
        self.assertGreater(cw.calls, n)

    def test_los_cap(self):
        ths = [threat(_out(40)), threat((WALL[0] + 40, WALL[1] + 40))]
        cw = CountingWorld(see_from=ths[1]["pos"])  # second threat sees everything: every point fails late
        s = Survival(CFG, cw)
        s.nav = NAV
        self.assertIsNone(s.find_cover(obs(_out(5)), ths))
        self.assertLessEqual(cw.calls, SV.LOS_CAP)
        self.assertGreater(cw.calls, 16)

    def test_world_none(self):
        s = Survival(CFG, None)
        o = obs((0, 0))
        self.assertIsNone(s.find_cover(o, [threat((50, 0))]))
        self.assertIsNone(Survival(CFG, WORLD).find_cover(o, []))
        s.hold_point(o), s.zone_goal(o), s.hold_facing(o), s.final_center(o)


class TestTiming(unittest.TestCase):
    def test_timing(self):
        rng = random.Random(1)
        worst_cover = worst_other = worst_hold = 0.0
        s = Survival(CFG, WORLD)
        s.nav = NAV
        for i in range(200):
            me = (rng.uniform(-400, 400), rng.uniform(-400, 400))
            ths = []
            for _ in range(rng.randint(1, 4)):
                a, d = rng.uniform(-math.pi, math.pi), rng.uniform(100, 200)
                ths.append(threat((me[0] + d * math.cos(a), me[1] + d * math.sin(a)), 3))
            o = obs(me, t=i * 2.0, next_center=[rng.uniform(-200, 200), rng.uniform(-200, 200)], next_radius=rng.uniform(0, 300))
            t0 = time.perf_counter()
            s.find_cover(o, ths)
            worst_cover = max(worst_cover, time.perf_counter() - t0)
            self.assertLessEqual(s.los_calls, SV.LOS_CAP)
            t0 = time.perf_counter()
            s.hold_point(o)  # first call per circle: path search
            worst_hold = max(worst_hold, time.perf_counter() - t0)
            t0 = time.perf_counter()
            s.hold_point(o), s.zone_goal(o), s.hold_facing(o), s.final_center(o)
            worst_other = max(worst_other, (time.perf_counter() - t0) / 4)
        # snap worst case: hold point deep inside the building (several blocked steps), map line fallback
        s.nav = None
        o = obs((BUILDING[0] - 100, BUILDING[1]), next_center=[BUILDING[0] + 55, BUILDING[1]], next_radius=55 + MARGIN)
        t0 = time.perf_counter()
        s.hold_point(o)
        worst_other = max(worst_other, time.perf_counter() - t0)
        print(f"\nsurvival timing: find_cover max {worst_cover * 1e3:.2f} ms, other max {worst_other * 1e3:.3f} ms", file=sys.stderr)
        print(f"hold search max {worst_hold * 1e3:.2f} ms", file=sys.stderr)
        self.assertLess(worst_hold, 0.030)
        self.assertLess(worst_cover, 0.010)
        self.assertLess(worst_other, 0.001)


if __name__ == "__main__":
    unittest.main()
