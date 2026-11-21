"""Phase 2 engine tests: weapons, loot, crates, cubes, upgrades, supply drops, NPCs, trees, obs schema."""
import copy
import gzip
import json
import math
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
from engine import Match, Weapon  # noqa: E402
from run import FlatWorld, recorded_hello, REPO  # noqa: E402
from schema_check import obs_errors  # noqa: E402
from trees import Canopy  # noqa: E402

CFG = recorded_hello()["config"]
W = CFG["weapons"]


class WallWorld(FlatWorld):
    """Flat ground with one wall: the slab x0 <= x <= x1, 0 <= z < h, infinitely long in y."""
    canopy = None

    def __init__(self, x0=50.0, x1=51.0, h=50.0):
        super().__init__()
        self.x0, self.x1, self.h = x0, x1, h

    def top(self, x, y, z):
        return self.h if self.x0 <= x <= self.x1 and self.h <= z + 0.01 else 0.0

    def solid(self, x, y, z):
        return z < 0 or (self.x0 <= x <= self.x1 and z < self.h)

    def blocked(self, x, y, z, radius, height, step=1.2):
        return x - radius < self.x1 and x + radius > self.x0 and z + step < self.h

    def los(self, a, b):
        if a[2] < 0 or b[2] < 0:
            return False
        dx = b[0] - a[0]
        if abs(dx) < 1e-12:
            if not self.x0 <= a[0] <= self.x1:
                return True
            s0, s1 = 0.0, 1.0
        else:
            s0, s1 = sorted(((self.x0 - a[0]) / dx, (self.x1 - a[0]) / dx))
            s0, s1 = max(0.0, s0), min(1.0, s1)
            if s0 > s1:
                return True
        z0, z1 = a[2] + (b[2] - a[2]) * s0, a[2] + (b[2] - a[2]) * s1
        return min(z0, z1) >= self.h


def clean(n=2, cfg=CFG, world=None, pos=None):
    """A match with no loot, crates, NPCs or drops; mechs at pos (default along +x every 60 m), all aiming east."""
    M = Match(cfg, world or FlatWorld(), 1, n)
    M.npcs.clear()
    M.crates.clear()
    M.pickups.clear()
    M.cubes.clear()
    M.drop_times = []
    for i, m in enumerate(M.mechs):
        m.pos = list(pos[i]) if pos else [60.0 * i, 0.0, 0.0]
        m.vel = [0.0, 0.0, 0.0]
        m.aim, m.aim_cmd = [0.0, 0.0], [0.0, 0.0]
    return M


def cfg_with(**weapons):
    c = copy.deepcopy(CFG)
    for k, v in weapons.items():
        c["weapons"][k].update(v)
    return c


def obs(tc, M, m):
    o = M.observe(m)
    e = obs_errors(o)
    tc.assertEqual(e, [], e[:5])
    return o


def decide(M, acts, n=1):
    """n decisions: acts maps mech index -> action dict (others idle with their current aim)."""
    for _ in range(n):
        M.prune_sounds()
        for m in M.alive():
            a = acts.get(m.id, {"aim": list(m.aim_cmd)})
            M.apply_action(m, dict(a, tick=M.tick))
        for _ in range(CFG["match"]["decide_every"]):
            M.step()


def evs(m, typ):
    return [e for e in m.events if e["type"] == typ]


def face(m, yaw):
    m.aim, m.aim_cmd = [yaw, 0.0], [yaw, 0.0]


class TestLaser(unittest.TestCase):
    def setUp(self):
        self.M = clean(2, pos=[(0, 0, 0), (100, 0, 0)])
        a, b = self.M.mechs
        a.slots[1] = Weapon("laser", CFG)
        face(b, math.pi)  # faces the shooter: front hit

    def charge_release(self, hold_decisions):
        a = self.M.mechs[0]
        decide(self.M, {0: {"aim": [0, 0], "fire": [False, True]}}, hold_decisions)
        decide(self.M, {0: {"aim": [0, 0], "fire": [False, False]}}, 2)
        return evs(self.M.mechs[1], "damaged"), a

    def test_full_charge(self):
        d, a = self.charge_release(8)  # 16 ticks = 0.8 s > 0.75 s
        self.assertEqual([(e["amount"], e["weapon"], e["by"]) for e in d], [(315, "laser", 0)])
        self.assertNotIn("rear", d[0])
        self.assertEqual(evs(a, "hit")[0]["amount"], 315)
        self.assertAlmostEqual(a.slots[1].cooldown, W["laser"]["cooldown"] - 0.15, places=6)  # fired on the 1st of 4 ticks

    def test_partial_charge(self):
        d, _ = self.charge_release(3)  # 6 ticks = 0.3 s of 0.75
        self.assertAlmostEqual(d[0]["amount"], 315 * (0.35 + 0.65 * 0.3 / 0.75), places=1)

    def test_early_release_fires_at_min_charge(self):
        d, _ = self.charge_release(1)  # 0.1 s, then keeps charging to 0.15 and fires
        self.assertAlmostEqual(d[0]["amount"], 315 * (0.35 + 0.65 * 0.15 / 0.75), places=1)

    def test_auto_fire_after_hold(self):
        M = self.M
        for k in range(40):  # trigger held 4 s
            decide(M, {0: {"aim": [0, 0], "fire": [False, True]}})
            if evs(M.mechs[1], "damaged"):
                break
        t_fire = M.t
        self.assertTrue(evs(M.mechs[1], "damaged"))
        self.assertAlmostEqual(t_fire, W["laser"]["charge"] + W["laser"]["hold_s"], delta=0.11)

    def test_charging_visible_slow_and_heard(self):
        M = self.M
        a, b = M.mechs
        decide(M, {0: {"aim": [0, 0], "fire": [False, True], "move": [0, 1]}}, 6)
        self.assertLessEqual(math.hypot(a.vel[0], a.vel[1]), CFG["mech"]["walk_speed"] * 0.5 + 1e-6)
        ob = obs(self, M, b)
        seen = [e for e in ob["mechs"] if e["id"] == 0][0]
        self.assertTrue(seen["charging"])
        self.assertIn("laser", seen["weapons"])
        self.assertGreater(ob["self"]["weapons"][0]["ammo"], 0)
        sa = obs(self, M, a)
        self.assertGreater(sa["self"]["weapons"][1]["charge"], 0.5)
        M2 = clean(2, pos=[(0, 0, 0), (100, 0, 0)])
        M2.mechs[0].slots[1] = Weapon("laser", CFG)
        face(M2.mechs[1], math.pi)
        decide(M2, {0: {"aim": [0, 0], "fire": [False, True]}})
        self.assertIn("laser_charge", [s["kind"] for s in obs(self, M2, M2.mechs[1])["sounds"]])

    def test_beam_and_sound_seen(self):
        M = self.M
        decide(M, {0: {"aim": [0, 0], "fire": [False, True]}}, 8)
        M.prune_sounds()
        M.apply_action(M.mechs[0], {"aim": [0, 0], "fire": [False, False]})
        M.apply_action(M.mechs[1], {"aim": [math.pi, 0]})
        M.step()
        M.step()
        ob = obs(self, M, M.mechs[1])
        self.assertEqual([(b["by"], b["kind"], len(b["path"])) for b in ob["beams"]], [(0, "laser", 2)])
        self.assertIn("laser", [s["kind"] for s in ob["sounds"]])
        self.assertEqual(obs(self, M, M.mechs[0])["beams"], [])  # own beams are not reported

    def test_cookoff(self):
        b = self.M.mechs[1]
        b.slots[1] = Weapon("mortar", CFG)
        d, a = self.charge_release(8)
        self.assertAlmostEqual(d[0]["amount"], 315 * 1.6, places=2)
        self.assertEqual(evs(b, "effect"), [{"type": "effect", "effect": "cookoff", "by": 0}])
        self.assertEqual(evs(a, "hit")[0]["effect"], "cookoff")

    def test_wall_blocks(self):
        M = clean(2, world=WallWorld(), pos=[(0, 0, 0), (100, 0, 0)])
        M.mechs[0].slots[1] = Weapon("laser", CFG)
        decide(M, {0: {"aim": [0, 0], "fire": [False, True]}}, 8)
        decide(M, {0: {"aim": [0, 0], "fire": [False, False]}}, 2)
        self.assertEqual(evs(M.mechs[1], "damaged"), [])

    def test_pierce(self):
        M = clean(3, pos=[(0, 0, 0), (60, 0, 0), (120, 0, 0)])
        a = M.mechs[0]
        a.slots[1] = Weapon("laser", CFG)
        decide(M, {0: {"aim": [0, 0], "fire": [False, True]}}, 8)
        decide(M, {0: {"aim": [0, 0], "fire": [False, False]}}, 1)
        self.assertTrue(evs(M.mechs[1], "damaged"))
        self.assertFalse(evs(M.mechs[2], "damaged"))
        a.upg["laser_pierce"] = 1
        M._restat(a)
        a.slots[1].cooldown = 0
        for m in M.mechs:
            m.events = []
        decide(M, {0: {"aim": [0, 0], "fire": [False, True]}}, 8)
        decide(M, {0: {"aim": [0, 0], "fire": [False, False]}}, 1)
        self.assertTrue(evs(M.mechs[1], "damaged"))
        self.assertTrue(evs(M.mechs[2], "damaged"))


class TestLightning(unittest.TestCase):
    def setUp(self):
        self.M = clean(3, pos=[(0, 0, 0), (30, 0, 0), (38, 8, 0)])
        self.a = self.M.mechs[0]
        self.a.slots[1] = Weapon("lightning", CFG)
        for m in self.M.mechs[1:]:
            face(m, math.pi)

    def test_hit_and_chain(self):
        M, a = self.M, self.a
        M.prune_sounds()
        M.apply_action(a, {"aim": [0, 0], "fire": [False, True]})
        M.step()
        d1, d2 = evs(M.mechs[1], "damaged"), evs(M.mechs[2], "damaged")
        self.assertEqual([e["amount"] for e in d1], [60])
        self.assertAlmostEqual(d2[0]["amount"], 42, places=2)
        self.assertAlmostEqual(a.energy, 100 - W["lightning"]["energy"])
        ob = obs(self, M, M.mechs[2])
        self.assertEqual([(b["kind"], len(b["path"])) for b in ob["beams"]], [("lightning", 3)])
        self.assertIn("lightning", [s["kind"] for s in ob["sounds"]])

    def test_rate(self):
        M = self.M
        decide(M, {0: {"aim": [0, 0], "fire": [False, True]}}, 10)  # 1 s held: shots at 0, .25, .5, .75
        self.assertEqual(len(evs(M.mechs[1], "damaged")), 4)

    def test_cone_and_no_target(self):
        M = clean(2, pos=[(0, 0, 0), (30 * math.cos(0.6), 30 * math.sin(0.6), 0)])  # 34 deg off the aim
        a = M.mechs[0]
        a.slots[1] = Weapon("lightning", CFG)
        decide(M, {0: {"aim": [0, 0], "fire": [False, True]}})
        self.assertEqual(evs(M.mechs[1], "damaged"), [])
        self.assertAlmostEqual(a.energy, 100 - 3)  # fired anyway, cost energy
        self.assertEqual(M.beams[-1][2], "lightning")

    def test_short(self):
        M = self.M
        b = M.mechs[1]
        b.slots[1] = Weapon("laser", CFG)
        decide(M, {1: {"aim": [math.pi, 0], "fire": [False, True]}}, 2)
        self.assertTrue(b.charging)
        decide(M, {0: {"aim": [0, 0], "fire": [False, True]}, 1: {"aim": [math.pi, 0], "fire": [False, True]}})
        self.assertFalse(b.charging)
        self.assertIn({"type": "effect", "effect": "short", "by": 0}, b.events)
        self.assertTrue(any(e.get("effect") == "short" for e in evs(M.mechs[0], "hit")))
        decide(M, {1: {"aim": [math.pi, 0], "fire": [False, True]}}, 15)  # 1.5 s later still shorted
        self.assertFalse(b.charging)
        decide(M, {1: {"aim": [math.pi, 0], "fire": [False, True]}}, 6)
        self.assertTrue(b.charging)


class TestMortar(unittest.TestCase):
    def test_splash_falloff_concussion(self):
        M = clean(2, pos=[(0, 0, 0), (80, 0, 0)])
        a, b = M.mechs
        b.vel = [0.0, 0.0, 0.0]
        pt = (76.5, 0.0, 0.0)  # 1.0 m from b's cylinder
        face(b, math.pi)
        M._explode(pt, a, None, M.t, (1.0, 0.0, -1.0))
        f = 1 - (1 - W["mortar"]["splash_edge"]) * 1.0 / W["mortar"]["splash_radius"]
        d = evs(b, "damaged")
        self.assertAlmostEqual(d[0]["amount"], 160 * f, places=1)
        self.assertAlmostEqual(b.energy, 100 - 45 * f, places=4)
        self.assertAlmostEqual(b.vel[0], 16 * f, places=4)
        self.assertAlmostEqual(b.vel[2], 9 * f, places=4)
        self.assertFalse(b.grounded)
        self.assertIn({"type": "effect", "effect": "concuss", "by": 0}, b.events)
        self.assertEqual(evs(a, "hit")[0]["effect"], "concuss")
        self.assertIn("explosion", [s[1] for s in M.sounds])

    def test_direct_and_self(self):
        M = clean(2, pos=[(0, 0, 0), (80, 0, 0)])
        a, b = M.mechs
        face(b, math.pi)
        M._explode((77.5, 0.0, 4.0), a, b, M.t, (1.0, 0.0, 0.0))
        self.assertEqual([e["amount"] for e in evs(b, "damaged")], [200])
        M._explode((2.0, 0.0, 0.0), a, None, M.t, (1.0, 0.0, -1.0))  # inside a's own cylinder, in front
        self.assertAlmostEqual(evs(a, "damaged")[0]["amount"], 160 * 0.5, places=2)
        self.assertEqual(evs(a, "hit"), [{"type": "hit", "target": 1, "amount": 200, "weapon": "mortar", "effect": "concuss"}])

    def test_wall_blocks_splash(self):
        M = clean(2, world=WallWorld(50, 51, 50), pos=[(0, 0, 0), (54, 0, 0)])
        a, b = M.mechs
        M._explode((49.9, 0.0, 1.0), a, None, M.t, (1.0, 0.0, 0.0))
        self.assertEqual(evs(b, "damaged"), [])

    def test_shell_flight(self):
        M = clean(2, pos=[(0, 0, 0), (5000, 5000, 0)])
        a = M.mechs[0]
        a.slots[1] = Weapon("mortar", CFG)
        a.aim = [0.0, 0.6]
        decide(M, {0: {"aim": [0, 0.6], "fire": [False, True]}})
        self.assertEqual(len(M.projectiles), 1)
        self.assertEqual(M.projectiles[0]["kind"], "mortar")
        land = None
        for _ in range(200):
            decide(M, {0: {"aim": [0, 0.6]}})
            ex = [s for s in M.sounds if s[1] == "explosion"]
            if ex:
                land = ex[0]
                break
        self.assertIsNotNone(land)
        v = W["mortar"]["speed"]
        self.assertAlmostEqual(land[2], v * v * math.sin(1.2) / W["mortar"]["gravity"], delta=25)
        # a mech standing there gets hit
        M2 = clean(2, pos=[(0, 0, 0), (land[2], 0, 0)])
        M2.mechs[0].slots[1] = Weapon("mortar", CFG)
        M2.mechs[0].aim = [0.0, 0.6]
        decide(M2, {0: {"aim": [0, 0.6], "fire": [False, True]}})
        decide(M2, {0: {"aim": [0, 0.6]}}, 60)
        self.assertTrue(evs(M2.mechs[1], "damaged"))


class TestWeaponObs(unittest.TestCase):
    def test_fields(self):
        M = clean(2)
        a = M.mechs[0]
        a.slots[1] = Weapon("mortar", CFG)
        w = obs(self, M, a)["self"]["weapons"]
        self.assertEqual(set(w[0]), {"kind", "cooldown", "ammo", "reload", "stats"})
        self.assertEqual(set(w[1]), {"kind", "cooldown", "stats"})
        a.slots[1] = Weapon("laser", CFG)
        self.assertEqual(set(obs(self, M, a)["self"]["weapons"][1]), {"kind", "cooldown", "charge", "stats"})

    def test_cube_damage_scaling(self):
        M = clean(2, cfg=cfg_with(gun={"spread_deg": 0}))
        a, b = M.mechs
        face(b, math.pi)
        a.cubes = 12
        M._restat(a)
        p = math.atan2(4.5 - a.st["muzzle_height"], 60)  # a 60% taller mech shoots over a 9 m one at pitch 0
        face(a, p)
        a.aim[1] = a.aim_cmd[1] = p
        decide(M, {0: {"aim": [0, p], "fire": [True, False]}}, 3)
        self.assertAlmostEqual(evs(b, "damaged")[0]["amount"], 45 * 1.4, places=2)  # capped at stat_cap 10


class TestLoot(unittest.TestCase):
    def setUp(self):
        self.M = clean(2, pos=[(0, 0, 0), (200, 0, 0)])
        self.a = self.M.mechs[0]

    def put(self, kind, x=2.0, y=0.0):
        return self.M._add_pickup(Weapon(kind, CFG), (x, y, 0.0))

    def take(self, pid, drop=None, who=0):
        a = {"aim": [0, 0], "take": pid}
        if drop is not None:
            a["drop"] = drop
        decide(self.M, {who: a})

    def test_take_and_equip_delay(self):
        pid = self.put("laser")
        self.take(pid)
        self.assertEqual(evs(self.a, "took"), [{"type": "took", "id": pid, "kind": "laser", "slot": 1}])
        self.assertNotIn(pid, self.M.pickups)
        self.assertAlmostEqual(self.a.slots[1].cooldown, W["laser"]["cooldown"] - 0.1, places=6)
        decide(self.M, {0: {"aim": [0, 0], "fire": [False, True]}}, 5)
        self.assertFalse(self.a.charging)  # still equipping
        self.assertIn("laser", self.a.kinds_taken)

    def test_failures(self):
        M, a = self.M, self.a
        self.take(99999)
        far = self.put("laser", 10.0)
        self.take(far)
        near = self.put("mortar")
        self.take(near)
        again = self.put("mortar", 1.0, 1.0)
        self.take(again)
        las = self.put("laser", 1.0, -1.0)
        self.take(las)
        r = [(e["id"], e["reason"]) for e in evs(a, "take_failed")]
        self.assertEqual(r, [(99999, "gone"), (far, "range"), (again, "have"), (las, "full")])
        obs(self, M, a)  # take_failed events validate against the schema (and are consumed)
        # swap the mortar out for the laser
        self.take(las, drop=1)
        took, dropped = evs(a, "took"), evs(a, "dropped")
        self.assertEqual(took[0]["kind"], "laser")
        self.assertEqual((dropped[0]["kind"], dropped[0]["slot"]), ("mortar", 1))
        self.assertEqual(M.pickups[dropped[0]["id"]].pos, a.pos)

    def test_busy_and_no_drop_while_charging(self):
        M, a = self.M, self.a
        a.slots[1] = Weapon("laser", CFG)
        decide(M, {0: {"aim": [0, 0], "fire": [False, True]}})
        pid = self.put("mortar")
        decide(M, {0: {"aim": [0, 0], "fire": [False, True], "take": pid, "drop": 1}})
        self.assertEqual(evs(a, "take_failed")[0]["reason"], "busy")
        decide(M, {0: {"aim": [0, 0], "fire": [False, True], "drop": 1}})
        self.assertEqual(a.slots[1].kind, "laser")
        self.assertEqual(evs(a, "dropped"), [])

    def test_contested_closer_wins(self):
        M = clean(2, pos=[(0, 0, 0), (3, 0, 0)])
        pid = M._add_pickup(Weapon("laser", CFG), (2.0, 0.0, 0.0))
        decide(M, {0: {"take": pid}, 1: {"take": pid}})
        self.assertEqual(evs(M.mechs[1], "took")[0]["id"], pid)
        self.assertEqual(evs(M.mechs[0], "take_failed")[0]["reason"], "gone")

    def test_gun_keeps_ammo(self):
        M = clean(2, pos=[(0, 0, 0), (0, 300, 0)])
        a = M.mechs[0]
        decide(M, {0: {"aim": [0, 0], "fire": [True, False]}}, 3)
        ammo = a.slots[0].ammo
        decide(M, {0: {"aim": [0, 0], "drop": 0}})
        self.assertIsNone(a.slots[0])
        pid = evs(a, "dropped")[0]["id"]
        decide(M, {0: {"aim": [0, 0], "take": pid}})
        self.assertEqual(a.slots[0].ammo, ammo)
        self.assertEqual(evs(a, "took")[0]["slot"], 0)

    def test_death_drop(self):
        M, a = self.M, self.a
        b = M.mechs[1]
        b.slots[1] = Weapon("laser", CFG)
        b.cubes = 3
        M._hurt(b, 1e5, "gun", a.pos, a, M.t)
        M.step()
        self.assertFalse(b.alive)
        self.assertEqual(sorted(p.w.kind for p in M.pickups.values()), ["laser"])
        self.assertEqual(len(M.cubes), 3 + CFG["cubes"]["death_drop_extra"])
        self.assertEqual(evs(a, "kill"), [{"type": "kill", "target": 1}])
        self.assertEqual((b.cubes_final, b.weapons_final), (3, ["gun", "laser"]))

    def test_visible_only_when_seen(self):
        M, a = self.M, self.a
        pid = self.put("laser", -100.0, 0.0)  # behind, beyond near range
        self.assertEqual(obs(self, M, a)["pickups"], [])
        face(a, math.pi)
        self.assertEqual([p["id"] for p in obs(self, M, a)["pickups"]], [pid])


class TestCratesCubes(unittest.TestCase):
    def test_crate_break(self):
        c = copy.deepcopy(CFG)
        c["loot"]["crate_weapon_chance"] = 1.0
        M = clean(2, cfg=c, pos=[(0, 0, 0), (300, 0, 0)])
        a = M.mechs[0]
        M.crates[1000] = __import__("engine").Thing("crate", 1000, (20.0, 0.0, 0.0), hp=300.0)
        self.assertEqual(obs(self, M, a)["crates"], [{"id": 1000, "pos": [20.0, 0.0, 0.0], "hp": 300.0}])
        M._hurt(M.crates[1000], 300, "gun", None, a, M.t)
        self.assertNotIn(1000, M.crates)
        self.assertEqual(len(M.cubes), 1)
        self.assertEqual(len(M.pickups), 1)
        self.assertIn("crate", [s[1] for s in M.sounds])
        self.assertEqual(evs(a, "hit")[0]["target"], 1000)

    def test_gun_hits_crate(self):
        M = clean(2, cfg=cfg_with(gun={"spread_deg": 0}), pos=[(0, 0, 0), (300, 0, 0)])
        a = M.mechs[0]
        M.crates[1000] = __import__("engine").Thing("crate", 1000, (20.0, 0.0, 0.0), hp=300.0)
        p = math.atan2(1.2 - 7, 20)
        decide(M, {0: {"aim": [0, p], "fire": [True, False]}}, 4)
        self.assertLess(M.crates[1000].hp, 300)

    def test_cube_pickup_growth_offer(self):
        M = clean(2, pos=[(0, 0, 0), (5, 0, 0)])
        a, b = M.mechs
        a.hp = 1000.0
        a.last_combat_t = 0.0  # no regen this tick
        M._add_cubes(2.5, 0.0, 0.0, 1)
        M.cubes[next(iter(M.cubes))].pos = [2.5, 0.0, 0.0]  # equidistant: lower id wins
        M.step()
        self.assertEqual((a.cubes, b.cubes), (1, 0))
        self.assertAlmostEqual(a.max_hp, 1400 * 1.04)
        self.assertAlmostEqual(a.hp, 1000 + 56, places=4)
        self.assertAlmostEqual(a.st["radius"], 2.5 * 1.05)
        o = obs(self, M, a)
        self.assertEqual(o["self"]["stats"]["eye_height"], 8 * 1.05)
        self.assertIn({"type": "pickup", "cubes": 1}, o["events"])
        off = o["offer"]
        self.assertIsNotNone(off)
        ids = [c["id"] for c in off["choices"]]
        self.assertEqual(len(set(ids)), 3)
        self.assertAlmostEqual(off["expires"], M.t - M.dt + 5, places=2)

    def test_offer_choices_valid(self):
        for s in range(40):
            M = clean(2)
            M.rng = random.Random(s)
            a = M.mechs[0]
            a.slots[1] = Weapon("laser", CFG) if s % 2 else None
            a.upg = {"plating": 3}
            a.offers_pending = 1
            M._draw_offer(a)
            for c in a.offer["choices"]:
                u = M.upgrade_defs[c["id"]]
                self.assertNotEqual(c["id"], "plating")
                self.assertIn(u.get("requires") or "gun", a.held_kinds())

    def test_pick_expiry_queue(self):
        M = clean(2)
        a = M.mechs[0]
        M._gain_cube(a, 3)  # thresholds 1 and 3
        self.assertEqual(a.offers_pending, 1)  # one shown now, one queued
        self.assertIsNotNone(a.offer)
        first = a.offer["choices"]
        decide(M, {0: {"pick": 2}})
        self.assertEqual(a.upgrades, [first[2]["id"]])
        self.assertIn({"type": "upgrade", "id": first[2]["id"]}, a.events)
        self.assertIsNotNone(a.offer)  # the queued second offer
        second = a.offer["choices"]
        decide(M, {}, 52)  # 5.2 s with no pick
        self.assertEqual(a.upgrades[1], second[0]["id"])

    def test_upgrade_effects(self):
        M = clean(2)
        a = M.mechs[0]
        a.offer = {"id": 1, "expires": 99, "choices": [{"id": "plating", "name": "", "desc": ""},
                                                       {"id": "gun_damage", "name": "", "desc": ""}]}
        M._apply_upgrade(a, 0)
        self.assertAlmostEqual(a.max_hp, 1610)
        a.offer = {"id": 2, "expires": 99, "choices": [{"id": "gun_damage", "name": "", "desc": ""}]}
        M._apply_upgrade(a, 0)
        self.assertAlmostEqual(obs(self, M, a)["self"]["weapons"][0]["stats"]["damage"], 51.75)
        self.assertEqual(obs(self, M, a)["self"]["upgrades"], ["plating", "gun_damage"])


class TestDrops(unittest.TestCase):
    def test_call_land_capture(self):
        M = clean(3, pos=[(0, 0, 0), (300, 0, 0), (-300, 0, 0)])
        M.drop_times = [0.5]
        decide(M, {}, 6)
        self.assertEqual(len(M.drops), 1)
        d = M.drops[0]
        o = obs(self, M, M.mechs[1])
        self.assertAlmostEqual(o["drops"][0]["lands_in"], CFG["drops"]["fall_s"] - (M.t - 0.5), places=1)
        _, _, _, _, _, nc, nr, _ = M.zone.phase(0.5)
        self.assertLessEqual(math.hypot(d.pos[0] - nc[0], d.pos[1] - nc[1]), nr)
        a, b, c = M.mechs
        a.pos = list(d.pos)
        b.pos = [d.pos[0] + 3, d.pos[1], d.pos[2]]
        c.pos = [d.pos[0] + 400, d.pos[1] + 300, 0.0]  # 500 m: hears the landing (drop carries 600 m)
        heard = []
        while M.t < d.land_t + 1.0:
            decide(M, {})
            heard += [s["kind"] for s in obs(self, M, c)["sounds"]]
        self.assertIn("drop", heard)

        self.assertEqual(d.progress, 0.0)  # two inside: frozen at 0
        b.pos = [d.pos[0] + 50, d.pos[1], d.pos[2]]
        a.hp = 500.0
        decide(M, {}, 20)
        self.assertGreater(d.progress, 1.5)
        a.pos, b.pos = [d.pos[0] + 50, d.pos[1], d.pos[2]], list(d.pos)  # a different mech alone: restart
        decide(M, {}, 1)
        self.assertLessEqual(d.progress, 0.1 + 1e-9)
        self.assertEqual(d.holder, 1)
        decide(M, {}, 41)
        self.assertEqual(M.drops, [])
        self.assertEqual(b.cubes, CFG["drops"]["cubes"])
        self.assertEqual(b.hp, b.max_hp)
        self.assertIn({"type": "drop", "id": d.id, "cubes": 3}, obs(self, M, b)["events"])
        self.assertEqual(b.drops_captured, 1)


class TestNPC(unittest.TestCase):
    def setUp(self):
        self.M = clean(2, pos=[(0, 0, 0), (400, 0, 0)])
        E = __import__("engine")
        nc = CFG["npc"]
        self.n = E.Thing("npc", 100, (30.0, 0.0, 0.0), home=[30.0, 0.0, 0.0], vel=[0.0, 0.0, 0.0], aim=[0.0, 0.0],
                         hp=float(nc["hp"]), max_hp=float(nc["hp"]), target=None, mode="wander", goal=None,
                         goal_t=0.0, cooldown=0.0, alive=True)
        self.M.npcs[100] = self.n

    def test_aggro_shoot_deaggro(self):
        M, n = self.M, self.n
        a = M.mechs[0]
        seen, got = set(), []
        for _ in range(20):
            decide(M, {0: {"aim": [0, 0]}})
            o = obs(self, M, a)
            seen.update(p["kind"] for p in o["projectiles"])
            got += o["events"]
        self.assertIs(n.target, a)
        self.assertIn("npc", seen)
        d = [e for e in got if e["type"] == "damaged" and e["weapon"] == "npc"]
        self.assertTrue(d)
        self.assertEqual((d[0]["amount"], d[0]["by"]), (25, 100))
        o = obs(self, M, a)
        e = [x for x in o["mechs"] if x["kind"] == "npc"][0]
        self.assertEqual(set(e), {"id", "kind", "pos", "vel", "aim", "hp", "max_hp"})
        a.pos = [300.0, 0.0, 0.0]
        decide(M, {}, 2)
        self.assertIsNone(n.target)  # deaggro: beyond deaggro_range

    def test_attacker_aggro_and_cubes(self):
        M, n = self.M, self.n
        b = M.mechs[1]
        M._hurt(n, 10, "gun", None, b, M.t)
        self.assertIs(n.target, b)
        M._hurt(n, 1000, "gun", None, b, M.t)
        self.assertNotIn(100, M.npcs)
        self.assertEqual(len(M.cubes), CFG["npc"]["cubes"])
        self.assertEqual(b.npc_kills, 1)

    def test_no_zone_damage(self):
        M, n = self.M, self.n
        n.pos = [5000.0, 5000.0, 0.0]
        n.home = list(n.pos)
        decide(M, {}, 10)
        self.assertEqual(n.hp, CFG["npc"]["hp"])


class TestTrees(unittest.TestCase):
    def setUp(self):
        data = {"bounds": {"minX": -100, "minY": -100, "maxX": 100, "maxY": 100},
                "rules": {"canopyDensity": 0.35, "canopyBlockT": 0.25},
                "trees": {"fields": ["x", "y", "z", "height", "crownR", "crownBase", "trunkR", "osm", "crownX", "crownY"],
                          "data": [0, 0, 0, 20, 4, 5, 0.5, 0, 0, 0]}}
        self.c = Canopy(data=data)

    def test_trunk_and_crown(self):
        c = self.c
        self.assertTrue(c.blocks((-50, 0, 2), (50, 0, 2)))  # trunk
        self.assertTrue(c.blocks((-50, 0, 12.5), (50, 0, 12.5)))  # 8 m through the crown
        self.assertFalse(c.blocks((-50, 3.5, 12.5), (50, 3.5, 12.5)))  # 3.9 m of foliage: still sees
        self.assertFalse(c.blocks((-50, 0, 25), (50, 0, 25)))  # above the tree
        self.assertFalse(c.blocks((-50, 10, 12.5), (50, 10, 12.5)))

    def test_vision(self):
        M = clean(2, pos=[(-60, 0, 0), (60, 0, 0)])
        M.canopy = Canopy(data={"bounds": {"minX": -600, "minY": -600, "maxX": 600, "maxY": 600},
                                "trees": {"fields": ["x", "y", "z", "height", "crownR", "crownBase", "trunkR", "crownX", "crownY"],
                                          "data": [0, 0, 0, 20, 6, 0, 0.5, 0, 0]}})
        a = M.mechs[0]
        self.assertEqual(obs(self, M, a)["mechs"], [])  # behind a crown, 120 m
        M.mechs[1].pos = [30.0, 0.0, 0.0]
        a.pos = [0.0, 0.0, 0.0]  # 30 m: near range ignores canopy
        self.assertEqual([m["id"] for m in obs(self, M, a)["mechs"]], [1])


class TestSchema(unittest.TestCase):
    def test_validator_accepts_recorded_stream(self):
        with gzip.open(os.path.join(REPO, "check", "stream.jsonl.gz"), "rt") as f:
            lines = [json.loads(x) for x in f]
        obs_ = [x for x in lines if x.get("type") == "obs"]
        for o in obs_[::10]:
            self.assertEqual(obs_errors(o), [])
        bad = dict(obs_[0])
        del bad["zone"]
        self.assertTrue(obs_errors(bad))

    def test_running_match(self):
        """Observations from a real-map match with crude bots that fight and loot validate against the schema."""
        from run import load_world
        world, _ = load_world()
        M = Match(CFG, world, 11, 16)
        rng = random.Random(4)
        kinds = set()
        while M.t < 60:
            acts = {}
            for m in M.alive():
                o = M.observe(m)
                e = obs_errors(o)
                self.assertEqual(e, [], e[:5])
                kinds.update(x["type"] for x in o["events"])
                p = o["self"]["pos"]
                a = {"tick": o["tick"], "move": [rng.uniform(-1, 1), rng.uniform(-1, 1)],
                     "aim": [o["self"]["aim"][0] + 0.4, 0], "fire": [rng.random() < 0.5, rng.random() < 0.5]}
                for x in o["mechs"]:
                    dx, dy = x["pos"][0] - p[0], x["pos"][1] - p[1]
                    a["aim"] = [math.atan2(dy, dx), 0.0]
                    break
                if o["pickups"]:
                    a["take"] = o["pickups"][0]["id"]
                if o["offer"]:
                    a["pick"] = 1
                acts[m.id] = a
            M.prune_sounds()
            for m in M.alive():
                M.apply_action(m, acts[m.id])
            M.step()
            M.step()
        self.assertTrue({"damaged", "hit"} <= kinds, kinds)


if __name__ == "__main__":
    unittest.main()
