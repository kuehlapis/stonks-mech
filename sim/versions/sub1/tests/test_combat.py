import copy
import gzip
import json
import math
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
from combat import Combat  # noqa: E402

with gzip.open(ROOT / "check" / "stream.jsonl.gz", "rt") as f:
    CFG = json.loads(f.readline())["config"]
    OBS = next(o for o in map(json.loads, f) if o.get("self"))  # real self/weapons dicts
GUN = OBS["self"]["weapons"][0]
LASER = {"kind": "laser", "cooldown": 0, "charge": 0, "stats": CFG["weapons"]["laser"]}  # not in the stream


def obs(weapons, aim=(0.0, 0.0), pos=(0.0, 0.0, 0.0)):
    o = copy.deepcopy(OBS)
    o["self"].update(pos=list(pos), vel=[0, 0, 0], aim=list(aim), weapons=copy.deepcopy(weapons))
    return o


def target(pos, vel=(0, 0, 0)):
    return {"id": 5, "pos": list(pos), "vel": list(vel), "visible": True}


class FakeWorld:
    def __init__(self, clear):
        self.clear = clear

    def los(self, a, b):
        return self.clear


def miss(pos, vel, shooter=(0, 0, 0)):
    """Fire along the commanded aim and return the closest approach of bullet to target center."""
    c = Combat(CFG, None)
    a = c.attack(obs([GUN, None], pos=shooter), target(pos, vel))["aim"]
    yaw, pitch = a
    u = [math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch)]
    st = OBS["self"]["stats"]
    r0, sp = st["radius"] + 0.5, GUN["stats"]["speed"]
    m = [shooter[0], shooter[1], shooter[2] + st["muzzle_height"]]
    tc = [pos[0], pos[1], pos[2] + CFG["mech"]["height"] / 2]
    best, t = 1e9, 0.0
    while t < 1.5:
        b = [m[k] + u[k] * (r0 + sp * t) for k in range(3)]
        p = [tc[k] + vel[k] * t for k in range(3)]
        best = min(best, math.dist(b, p))
        t += 0.0005
    return best


class TestCombat(unittest.TestCase):
    def test_intercept_hits_moving_target(self):
        cases = [((150, 0, 0), (0, 11.7, 0)), ((100, 80, 5), (-19.5, 4, 0)), ((40, -30, -3), (8, 8, 10)),
                 ((200, 50, 20), (0, -19.5, -5)), ((-120, 10, 0), (11.7, 11.7, 0))]
        misses = [miss(p, v) for p, v in cases]
        print("miss distances (m):", [round(x, 3) for x in misses])
        for x in misses:
            self.assertLess(x, CFG["mech"]["radius"] * 0.2)
        self.assertGreater(Combat(CFG, None).attack(obs([GUN, None]), target(*cases[0]))["aim"][0], 0.01)  # led

    def test_fires_when_aim_on_target_only(self):
        c = Combat(CFG, None)
        t = target((100, 0, 0))
        on = c.attack(obs([GUN, None]), t)
        self.assertEqual(c.attack(obs([GUN, None], aim=on["aim"]), t)["fire"], [True, False])
        self.assertEqual(c.attack(obs([GUN, None], aim=(0.3, 0)), t)["fire"], [False, False])

    def test_out_of_range_no_fire(self):
        c = Combat(CFG, None)
        t = target((CFG["weapons"]["gun"]["range"] + 20, 0, 0))
        a = c.attack(obs([GUN, None]), t)
        self.assertEqual(c.attack(obs([GUN, None], aim=a["aim"]), t)["fire"], [False, False])

    def test_no_los_no_fire(self):
        t = target((100, 0, 0))
        a = Combat(CFG, None).attack(obs([GUN, LASER]), t)["aim"]
        self.assertEqual(Combat(CFG, FakeWorld(False)).attack(obs([GUN, LASER], aim=a), t)["fire"], [False, False])
        self.assertEqual(Combat(CFG, FakeWorld(True)).attack(obs([GUN, LASER], aim=a), t)["fire"], [True, True])

    def test_cooldown_blocks_gun(self):
        g = dict(GUN, cooldown=0.2)
        c = Combat(CFG, None)
        t = target((100, 0, 0))
        a = c.attack(obs([g, None]), t)["aim"]
        self.assertFalse(c.attack(obs([g, None], aim=a), t)["fire"][0])

    def test_reload(self):
        c = Combat(CFG, None)
        empty = dict(GUN, ammo=0)
        r = c.attack(obs([empty, None]), target((100, 0, 0)))
        self.assertTrue(r["reload"])
        self.assertFalse(r["fire"][0])
        low = dict(GUN, ammo=2)
        self.assertTrue(c.attack(obs([low, None]), target((400, 0, 0)))["reload"])
        self.assertFalse(c.attack(obs([low, None]), target((100, 0, 0)))["reload"])
        self.assertFalse(c.attack(obs([dict(empty, reload=1.0), None]), target((100, 0, 0)))["reload"])
        self.assertTrue(c.face(obs([low, None]), 1.0)["reload"])
        self.assertFalse(c.face(obs([GUN, None]), 1.0)["reload"])

    def test_laser_charge_then_release(self):
        c = Combat(CFG, None)
        t = target((150, 20, 0), (0, 11.7, 0))  # hitscan: aim straight at the center, no lead
        full = CFG["weapons"]["laser"]["charge"]
        r = c.attack(obs([None, LASER]), t)
        self.assertEqual(r["fire"], [False, True])  # start charging
        aim = r["aim"]
        self.assertAlmostEqual(aim[0], math.atan2(20, 150), places=6)
        half = dict(LASER, charge=full / 2)
        self.assertTrue(c.attack(obs([None, half], aim=aim), t)["fire"][1])  # keep holding
        done = dict(LASER, charge=full)
        self.assertTrue(c.attack(obs([None, done], aim=(aim[0] + 0.2, 0)), t)["fire"][1])  # off target: hold
        self.assertFalse(c.attack(obs([None, done], aim=aim), t)["fire"][1])  # release
        self.assertFalse(c.attack(obs([None, LASER]), target((300, 0, 0)))["fire"][1])  # beyond range: no start
        self.assertFalse(c.attack(obs([None, dict(LASER, cooldown=1.0)]), t)["fire"][1])
        self.assertEqual(c.face(obs([None, done]), 2.0), {"aim": [2.0, 0.0], "fire": [False, False], "reload": False})

    def test_null_and_swapped_slots(self):
        c = Combat(CFG, None)
        t = target((100, 0, 0))
        self.assertEqual(c.attack(obs([None, None]), t)["fire"], [False, False])
        a = c.attack(obs([LASER, GUN]), t)
        self.assertEqual(a["fire"], [True, False])  # laser in slot 0 starts; gun slot 1 aim not yet on
        self.assertEqual(c.attack(obs([LASER, GUN], aim=a["aim"]), t)["fire"], [True, True])
        o = obs([GUN, None])
        o["self"]["weapons"] = None
        self.assertEqual(c.attack(o, t)["fire"], [False, False])

    def test_timing(self):
        c = Combat(CFG, FakeWorld(True))
        o = obs([GUN, dict(LASER, charge=0.3)])
        t = target((120, 40, 2), (5, -9, 0))
        n = 2000
        s = time.perf_counter()
        for _ in range(n):
            c.attack(o, t)
            c.face(o, 1.0)
        ms = (time.perf_counter() - s) / n * 1000
        print(f"attack+face: {ms:.4f} ms")
        self.assertLess(ms, 1.0)


if __name__ == "__main__":
    unittest.main()
