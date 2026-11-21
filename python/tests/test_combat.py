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

    def ground(self, x, y):
        return 0.0  # flat


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


MORTAR = {"kind": "mortar", "cooldown": 0, "stats": CFG["weapons"]["mortar"]}


def shell_miss(aim, shooter, tgt):
    """Fly the shell along `aim` from the tube and return its horizontal miss when it falls to the target's height."""
    st, m = OBS["self"]["stats"], CFG["weapons"]["mortar"]
    yaw, pitch = aim
    u = [math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch)]
    r0 = st["radius"] + 0.5
    b = [shooter[0] + u[0] * r0, shooter[1] + u[1] * r0, shooter[2] + st["height"] + 0.5 + u[2] * r0]
    vel = [m["speed"] * k for k in u]
    dt = 0.0005
    while not (vel[2] < 0 and b[2] <= tgt[2]):
        b = [b[k] + vel[k] * dt for k in range(3)]
        vel[2] -= m["gravity"] * dt
    return math.hypot(b[0] - tgt[0], b[1] - tgt[1])


class TestMortar(unittest.TestCase):
    def test_arc_lands_on_static_target(self):
        for clear in (True, False):
            for r in (40, 100, 180):
                tgt = (r * 0.6, r * 0.8, 0.0)
                a = Combat(CFG, FakeWorld(clear)).attack(obs([GUN, MORTAR]), target(tgt))
                if not clear and r < 150:
                    continue  # high arc under ~150 m is past max_pitch 1.3: no lob
                self.assertLess(shell_miss(a["aim"], (0, 0, 0), tgt), 3.0, (r, clear))
                self.assertTrue(clear or a["aim"][1] > math.pi / 4)

    def test_fires_only_when_aimed_and_far(self):
        c = Combat(CFG, None)
        aim = c.attack(obs([GUN, MORTAR]), target((100, 0, 0)))["aim"]
        self.assertTrue(c.attack(obs([GUN, MORTAR], aim=aim), target((100, 0, 0)))["fire"][1])
        self.assertFalse(c.attack(obs([GUN, MORTAR]), target((100, 0, 0)))["fire"][1])  # aim flat: off
        self.assertFalse(c.attack(obs([GUN, MORTAR], aim=aim), target((10, 0, 0)))["fire"][1])
        self.assertFalse(c.attack(obs([GUN, MORTAR], aim=aim), target((400, 0, 0)))["fire"][1])  # out of reach

    def test_no_mortar_same_as_before(self):
        c = Combat(CFG, None)
        a, b = c.attack(obs([GUN, None]), target((100, 0, 0))), c.attack(obs([GUN, MORTAR]), target((5, 0, 0)))
        self.assertEqual(a["aim"], Combat(CFG, None).attack(obs([GUN, None]), target((100, 0, 0)))["aim"])
        self.assertEqual(b["fire"][1], False)

    def test_cheap(self):
        c, o, tg = Combat(CFG, None), obs([GUN, MORTAR]), target((100, 20, 0), (5, 3, 0))
        t0 = time.perf_counter()
        for _ in range(1000):
            c.attack(o, tg)
        self.assertLess((time.perf_counter() - t0), 1.0)  # < 1 ms per call


def strafe_pos(t, steady):
    """Target 130 m east, moving north at 11.7 m/s; the strafer flips every 0.5 s. Returns (pos, vel)."""
    if steady:
        return [130.0, 11.7 * t - 60, 0.0], [0.0, 11.7, 0.0]
    k, f = divmod(t, 0.5)
    sgn = 1 if int(k) % 2 == 0 else -1
    return [130.0, sgn * (11.7 * f - 2.925), 0.0], [0.0, 11.7 * sgn, 0.0]


def hop_pos(t):
    """Target 130 m east hopping in place: jump_speed up every time it lands (gravity from config)."""
    g, j = CFG["mech"]["gravity"], CFG["mech"]["jump_speed"]
    f = t % (2 * j / g)
    return [130.0, 0.0, j * f - 0.5 * g * f * f], [0.0, 0.0, j - g * f]


def hit_rate(predict, traj):
    """Aim each decision, fire one decision interval later (action applies next tick), straight bullets."""
    import combat
    combat.AIM_PREDICT = predict
    try:
        c, st, hits, n = Combat(CFG, FakeWorld(True)), OBS["self"]["stats"], 0, 0
        r0, sp, dt = st["radius"] + 0.5, GUN["stats"]["speed"], c.dt
        h = CFG["mech"]["height"]
        for i in range(100):
            t = 0.05 + i * 0.1
            pos, vel = traj(t)
            o = obs([GUN, None])
            o["t"] = t
            yaw, pitch = c.attack(o, {"id": 7, "pos": pos, "vel": vel, "visible": True, "last_seen": t})["aim"]
            if i < 10:
                continue  # warm up the history
            u = [math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch)]
            tf = (130 - r0 * u[0]) / (sp * u[0])  # bullet reaches the target's x plane
            p, _ = traj(t + dt + tf)
            by = u[1] * (r0 + sp * tf)
            bz = st["muzzle_height"] + u[2] * (r0 + sp * tf)
            n += 1
            hits += abs(by - p[1]) <= st["radius"] and p[2] <= bz <= p[2] + h
        return hits / n
    finally:
        combat.AIM_PREDICT = False


class TestPredict(unittest.TestCase):
    def test_strafer_hit_more(self):
        off, on = hit_rate(False, lambda t: strafe_pos(t, False)), hit_rate(True, lambda t: strafe_pos(t, False))
        print(f"strafer hit rate off {off:.2f} on {on:.2f}", file=sys.stderr)
        self.assertGreater(on, off)

    def test_straight_not_worse(self):
        self.assertGreaterEqual(hit_rate(True, lambda t: strafe_pos(t, True)), hit_rate(False, lambda t: strafe_pos(t, True)))

    def test_hopper(self):
        off, on = hit_rate(False, hop_pos), hit_rate(True, hop_pos)
        print(f"hopper hit rate off {off:.2f} on {on:.2f}", file=sys.stderr)
        self.assertGreater(on, off)

    def test_blind_extrapolates_toward_us_only(self):
        import combat
        combat.AIM_PREDICT = True
        try:
            c = Combat(CFG, None)
            o = obs([GUN, None])
            o["zone"] = {"next_center": [0.0, 0.0]}
            for i in range(10):
                o["t"] = i * 0.1
                c.attack(o, {"id": 3, "pos": [100.0, 0, 0], "vel": [-10.0, 0, 0], "visible": True, "last_seen": o["t"]})
            o["t"] = 1.4
            tp, _, _ = c._predict(o, {"id": 3, "pos": [100.0, 0, 0], "vel": [-10.0, 0, 0], "visible": False,
                                   "last_seen": 0.9}, [100.0, 0, 0], [-10.0, 0, 0])
            self.assertAlmostEqual(tp[0], 95.0, places=3)
            tp, _, _ = c._predict(o, {"id": 4, "pos": [100.0, 0, 0], "vel": [10.0, 0, 0], "visible": False,
                                   "last_seen": 0.9}, [100.0, 0, 0], [10.0, 0, 0])
            self.assertEqual(tp[0], 100.0)  # heading away from us and the zone: no extrapolation
        finally:
            combat.AIM_PREDICT = False

    def test_cheap(self):
        import combat
        combat.AIM_PREDICT = True
        try:
            c, o = Combat(CFG, None), obs([GUN, LASER])
            t0 = time.perf_counter()
            for i in range(1000):
                o["t"] = i * 0.1
                c.attack(o, {"id": 1, "pos": [100.0, 0, 0], "vel": [0, 11.7 * (-1) ** (i // 5), 0], "visible": True})
            ms = (time.perf_counter() - t0)
            print(f"predict attack: {ms:.4f} ms", file=sys.stderr)
            self.assertLess(ms, 0.2)
        finally:
            combat.AIM_PREDICT = False


if __name__ == "__main__":
    unittest.main()
