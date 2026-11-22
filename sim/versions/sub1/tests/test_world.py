import json
import math
import random
import struct
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
from world import World  # noqa: E402

ARENA = ROOT / "arena"

# Real prisms from arena/v2/world.json
BUILDING = (-114.5, 62.0)  # building base -5.0 top 10.34, ring (-113.7,71.5) (-117.4,71.0) (-119.2,69.1) (-117.1,52.6) (-108.8,53.7)
WALL = (-118.15, 60.85)  # midpoint of its west wall (-119.2,69.1)-(-117.1,52.6), open ground beyond
OUT = (-0.992, -0.126)  # outward normal of that wall


def _out(d):
    return (WALL[0] + d * OUT[0], WALL[1] + d * OUT[1])
UNDER_BRIDGE = (-110.0, -28.5)  # bridge base 6.59 top 8.59, ground about -4.8


def _pip(r, x, y):
    c = False
    n = len(r) // 2
    for k in range(n):
        x1, y1, x2, y2 = r[2 * k], r[2 * k + 1], r[(2 * k + 2) % (2 * n)], r[(2 * k + 3) % (2 * n)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def _timeit(f, args):
    t = time.perf_counter()
    for a in args:
        f(*a)
    return (time.perf_counter() - t) / len(args) * 1e3


class TestWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t = time.perf_counter()
        cls.w = World(str(ARENA))
        cls.load_s = time.perf_counter() - t
        print("world load %.3f s" % cls.load_s, file=sys.stderr)
        cls.raw = json.loads((ARENA / "v2" / "world.json").read_text(encoding="utf-8"))
        cls.grid = (ARENA / "v2" / "terrain.i16").read_bytes()
        cls.boxes = [(min(p["ring"][0::2]), min(p["ring"][1::2]), max(p["ring"][0::2]), max(p["ring"][1::2]), p)
                     for p in cls.raw["prisms"]]

    def ref_solid(self, x, y, z):
        """Brute force over every prism, no grid."""
        if z < self.w.ground(x, y):
            return True
        return any(x0 <= x <= x1 and y0 <= y <= y1 and p["base"] <= z < p["top"] and _pip(p["ring"], x, y)
                   and not any(_pip(h, x, y) for h in p["holes"]) for x0, y0, x1, y1, p in self.boxes)

    def test_bounds(self):
        b = self.raw["bounds"]
        self.assertEqual(self.w.bounds, (b["minX"], b["minY"], b["maxX"], b["maxY"]))

    def test_ground_matches_raw_grid(self):
        t = self.raw["terrain"]
        nx = t["nx"]

        def raw(i, j):
            return struct.unpack_from("<h", self.grid, 2 * (j * nx + i))[0] / 100.0

        for i, j in [(0, 0), (513, 334), (100, 200), (1069, 723), (700, 50)]:
            x, y = t["minX"] + i * t["step"], t["minY"] + j * t["step"]
            self.assertAlmostEqual(self.w.ground(x, y), raw(i, j), places=6)
        # bilinear midpoint of a cell, and clamping outside the grid
        x, y = t["minX"] + 100.5, t["minY"] + 200.5
        mid = (raw(100, 200) + raw(101, 200) + raw(100, 201) + raw(101, 201)) / 4
        self.assertAlmostEqual(self.w.ground(x, y), mid, places=6)
        self.assertAlmostEqual(self.w.ground(-9999, -9999), raw(0, 0), places=6)
        self.assertAlmostEqual(self.w.ground(9999, 9999), raw(nx - 1, t["ny"] - 1), places=6)

    def test_solid_building_and_bridge(self):
        w = self.w
        x, y = BUILDING
        self.assertTrue(w.solid(x, y, 5.0))
        self.assertFalse(w.solid(x, y, 10.34))  # top is exclusive
        self.assertFalse(w.solid(x, y, 12.0))
        self.assertFalse(w.solid(*_out(5), 5.0))
        x, y = UNDER_BRIDGE
        self.assertTrue(w.solid(x, y, 7.5))
        self.assertFalse(w.solid(x, y, 2.0))
        self.assertTrue(w.solid(x, y, w.ground(x, y) - 0.1))

    def test_top(self):
        w = self.w
        x, y = BUILDING
        self.assertAlmostEqual(w.top(x, y, 20.0), 10.34)
        self.assertAlmostEqual(w.top(x, y, 10.34), 10.34)
        self.assertAlmostEqual(w.top(x, y, 5.0), w.ground(x, y))
        x, y = UNDER_BRIDGE
        self.assertAlmostEqual(w.top(x, y, 0.0), w.ground(x, y))
        self.assertAlmostEqual(w.top(x, y, 9.0), 8.59)

    def test_solid_matches_brute_force(self):
        rnd = random.Random(1)
        b = self.w.bounds
        for _ in range(1500):
            x, y, z = rnd.uniform(b[0], b[2]), rnd.uniform(b[1], b[3]), rnd.uniform(-5, 40)
            self.assertEqual(self.w.solid(x, y, z), self.ref_solid(x, y, z), (x, y, z))

    def test_los(self):
        w = self.w
        x, y = BUILDING
        g = w.ground(x, y)
        o = _out(12)
        self.assertFalse(w.los((o[0], o[1], w.ground(*o) + 4), (x, y, g + 4)))  # through the wall
        self.assertTrue(w.los((o[0], o[1], 15), (x, y, 15)))  # over the roof
        self.assertTrue(w.los((x, y, 10.34), (x, y + 1, 20)))  # standing on the roof, looking up
        p, q = _out(3), _out(40)
        self.assertTrue(w.los((p[0], p[1], w.ground(*p) + 8), (q[0], q[1], w.ground(*q) + 8)))  # open ground
        x, y = UNDER_BRIDGE
        self.assertTrue(w.los((x, -15, 0), (x, -42, 0)))  # under the bridge
        self.assertFalse(w.los((x, -15, 7.5), (x, -42, 7.5)))  # through the deck
        self.assertFalse(w.los((x, -15, w.ground(x, -15) - 1), (x, -42, 0)))  # starts underground
        self.assertTrue(w.los((x, -15, 0), (x, -15, 0)))

    def test_los_matches_dense_sampling(self):
        rnd = random.Random(2)
        b = self.w.bounds
        blocked = 0
        for _ in range(40):
            x, y = rnd.uniform(b[0], b[2]), rnd.uniform(b[1], b[3])
            a = (x, y, self.w.top(x, y, 80) + rnd.uniform(1, 15))
            ang, d = rnd.uniform(0, 2 * math.pi), rnd.uniform(5, 120)
            x, y = a[0] + d * math.cos(ang), a[1] + d * math.sin(ang)
            c = (x, y, self.w.top(x, y, 80) + rnd.uniform(1, 15))
            n = int(d * 4)
            ref = not any(self.ref_solid(*[a[k] + (c[k] - a[k]) * i / n for k in range(3)]) for i in range(1, n))
            blocked += not ref
            self.assertEqual(self.w.los(a, c), ref, (a, c))
        self.assertGreater(blocked, 0)

    def test_blocked(self):
        w = self.w
        near, far = _out(1.5), _out(3.5)
        g = w.ground(*near)
        self.assertTrue(w.blocked(*near, g, 2.5, 9))  # 1.5 m from the wall
        self.assertFalse(w.blocked(*far, w.ground(*far), 2.5, 9))  # 3.5 m from it
        self.assertTrue(w.blocked(*BUILDING, g, 2.5, 9))  # inside
        self.assertFalse(w.blocked(*BUILDING, 10.34, 2.5, 9))  # on the roof
        self.assertFalse(w.blocked(*near, 9.5, 2.5, 9))  # roof is within a step
        self.assertTrue(w.blocked(*near, 9.0, 2.5, 9))  # roof is 1.34 m up: a wall
        self.assertFalse(w.blocked(*near, 11.0, 2.5, 9))  # above it
        x, y = UNDER_BRIDGE
        self.assertFalse(w.blocked(x, y, w.ground(x, y), 2.5, 9))  # 11.4 m clearance: a mech walks under
        self.assertTrue(w.blocked(x, y, 0.0, 2.5, 9))  # head in the deck
        self.assertFalse(w.blocked(x, y, 0.0, 1.8, 3.5))  # an NPC still fits
        self.assertFalse(w.blocked(x, y, 8.0, 2.5, 9))  # deck top is within a step: walk onto it
        self.assertFalse(w.blocked(-200.0, 0.0, w.ground(-200.0, 0.0), 2.5, 9))  # open ground
        self.assertFalse(w.blocked(-200.0, 0.0, w.ground(-200.0, 0.0), 15, 9))  # nothing within 15 m
        self.assertTrue(w.blocked(0.0, -60.0, w.ground(0.0, -60.0), 15, 9))  # but something within 15 m here

    def test_timing(self):
        w = self.w
        rnd = random.Random(3)
        b = w.bounds
        pts = [(rnd.uniform(b[0], b[2]), rnd.uniform(b[1], b[3]), rnd.uniform(0, 30)) for _ in range(5000)]
        segs = []
        while len(segs) < 300:  # clear 200 m lines: the slow case, no early exit
            x, y = rnd.uniform(b[0], b[2]), rnd.uniform(b[1], b[3])
            ang = rnd.uniform(0, 2 * math.pi)
            q = (x + 200 * math.cos(ang), y + 200 * math.sin(ang))
            if b[0] < q[0] < b[2] and b[1] < q[1] < b[3]:
                s = ((x, y, w.top(x, y, 80) + 8), (q[0], q[1], w.top(q[0], q[1], 80) + 8))
                if w.los(*s):
                    segs.append(s)
        ms = {
            "ground": (_timeit(w.ground, [p[:2] for p in pts]), 0.02),
            "top": (_timeit(w.top, pts), 0.02),
            "solid": (_timeit(w.solid, pts), 0.02),
            "blocked": (_timeit(w.blocked, [p + (2.5, 9.0) for p in pts]), 0.05),
            "los200": (_timeit(w.los, segs), 0.3),
        }
        print("world per-call ms: " + ", ".join("%s %.4f (budget %g)" % (k, v, bud) for k, (v, bud) in ms.items()),
              file=sys.stderr)
        self.assertLess(self.load_s, 9.0)  # budget 3 s
        for k, (v, bud) in ms.items():
            self.assertLess(v, 3 * bud, k)
        try:
            import resource
            mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            print("process max RSS %.0f MB" % mb, file=sys.stderr)
            self.assertLess(mb, 450)  # budget 150 MB for World; RSS includes the test process
        except ImportError:  # Windows
            pass


if __name__ == "__main__":
    unittest.main()
