import gzip
import json
import math
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
from perception import Perception  # noqa: E402
from world import World  # noqa: E402

CFG = {"vision": {"memory_s": 5}, "mech": {"eye_height": 8, "height": 9}, "cubes": {"size_per_cube": 0.05}}


def mech(i, pos, aim=0.0, charging=False, kind="mech"):
    return {"id": i, "kind": kind, "pos": pos, "vel": [1, 0, 0], "aim": [aim, 0], "hp": 900, "max_hp": 1400,
            "cubes": 0, "weapons": ["gun", "laser"], "charging": charging}


def obs(t, mechs=(), events=(), sounds=()):
    return {"t": t, "self": {"id": 1, "pos": [0.0, 0.0, 0.0], "cubes": 0},
            "mechs": list(mechs), "events": list(events), "sounds": list(sounds)}


class NoLos:
    def los(self, a, b):
        return False


class TestPerception(unittest.TestCase):
    def test_tracking_and_expiry(self):
        p = Perception(CFG, 1)
        p.update(obs(10, [mech(5, [50, 0, 0]), mech(1, [0, 0, 0]), mech(104, [9, 9, 0], kind="npc")]))
        self.assertEqual([th["id"] for th in p.threats], [5])
        self.assertTrue(p.threats[0]["visible"])
        p.update(obs(14))
        self.assertEqual(len(p.threats), 1)
        self.assertFalse(p.threats[0]["visible"])
        self.assertEqual(p.threats[0]["last_seen"], 10)
        p.update(obs(15.1))
        self.assertEqual(p.threats, [])

    def test_virtual_threat_from_damage(self):
        p = Perception(CFG, 1)
        b = math.pi / 2
        p.update(obs(20, events=[{"type": "damaged", "amount": 300, "weapon": "laser", "bearing": b, "by": 7}]))
        th = p.threats[0]
        self.assertTrue(th["virtual"])
        self.assertAlmostEqual(th["pos"][0], 0, places=6)
        self.assertAlmostEqual(th["pos"][1], 150)
        self.assertEqual(p.damage_bearing(21), b)
        p.update(obs(21, events=[{"type": "damaged", "amount": 90, "weapon": "mortar", "bearing": 0.0, "by": 8}]))
        mortar = [th for th in p.threats if th["id"] == 8][0]
        self.assertEqual(mortar["weapons"], ["mortar"])
        self.assertAlmostEqual(mortar["pos"][0], 100)
        p.update(obs(23.1))
        self.assertEqual([th["id"] for th in p.threats], [8])  # 7 expired after 3 s
        self.assertIsNone(p.damage_bearing(24.5))

    def test_engaged_window(self):
        p = Perception(CFG, 1)
        p.update(obs(30, [mech(5, [50, 0, 0])], events=[{"type": "damaged", "amount": 45, "weapon": "gun",
                                                          "bearing": 0.0, "by": 5}]))
        self.assertEqual(p.engaged_by(30)["id"], 5)
        self.assertEqual(p.engaged_by(33)["id"], 5)
        self.assertIsNone(p.engaged_by(33.1))
        p.update(obs(31, events=[{"type": "damaged", "amount": 20, "weapon": "zone", "bearing": None, "by": None},
                                 {"type": "damaged", "amount": 25, "weapon": "npc", "bearing": 1.0, "by": 104}]))
        self.assertEqual(p.engaged_by(31)["id"], 5)  # npc and zone don't engage

    def test_threatened_charging_first(self):
        p = Perception(CFG, 1)
        p.update(obs(40, [mech(5, [30, 0, 0], aim=math.pi), mech(6, [0, 80, 0], aim=-math.pi / 2, charging=True),
                          mech(9, [0, -30, 0], aim=0.0)]))  # 9 aims away
        self.assertEqual(p.threatened_by(obs(40), None)["id"], 6)
        self.assertIsNone(p.threatened_by(obs(40), NoLos()))
        p.update(obs(40.05, [mech(5, [30, 0, 0], aim=math.pi + 0.2)]))  # 11.5° off: still aimed
        self.assertEqual(p.threatened_by(obs(40.05), None)["id"], 5)
        p.update(obs(40.1, [mech(5, [30, 0, 0], aim=math.pi + 0.3)]))  # 17° off
        self.assertIsNone(p.threatened_by(obs(40.1), None))

    def test_sound_bearing(self):
        p = Perception(CFG, 1)
        p.update(obs(50, sounds=[{"kind": "gun", "bearing": 1.0, "dist": "mid", "age": 0.5},
                                 {"kind": "step", "bearing": 2.0, "dist": "near", "age": 0.0},
                                 {"kind": "laser", "bearing": 3.0, "dist": "far", "age": 0.0}]))
        self.assertEqual(p.sound_bearing(50), 1.0)
        self.assertIsNone(p.sound_bearing(53.6))

    def test_timing_on_stream(self):
        world = World(str(ROOT / "arena"))
        lines = gzip.open(ROOT / "check" / "stream.jsonl.gz", "rt").read().splitlines()
        hello = json.loads(lines[0])
        msgs = [json.loads(x) for x in lines[1:]]
        msgs = [m for m in msgs if m.get("type") == "obs"]
        p = Perception(hello["config"], msgs[0]["self"]["id"])
        times = []
        for o in msgs:
            s = time.perf_counter()
            p.update(o)
            p.threatened_by(o, world)
            p.engaged_by(o["t"])
            p.damage_bearing(o["t"])
            p.sound_bearing(o["t"])
            times.append((time.perf_counter() - s) * 1e3)
        mean = sum(times) / len(times)
        print("perception %d obs: mean %.3f ms, max %.3f ms" % (len(times), mean, max(times)), file=sys.stderr)
        self.assertGreaterEqual(len(times), 290)
        self.assertLessEqual(mean, 2.0)


if __name__ == "__main__":
    unittest.main()
