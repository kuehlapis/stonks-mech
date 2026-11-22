import copy
import gzip
import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from economy import Economy  # noqa: E402

STREAM = os.path.join(os.path.dirname(__file__), "..", "..", "check", "stream.jsonl.gz")
with gzip.open(STREAM, "rt") as f:
    CFG = json.loads(f.readline())["config"]
    OBS = [o for o in map(json.loads, f) if o.get("type") == "obs"]

GUN = {"kind": "gun", "cooldown": 0, "ammo": 12, "reload": 0, "stats": {}}


def obs_with(pickups, weapons=(GUN, None), t=20.0, events=()):
    o = copy.deepcopy(OBS[0])
    o["t"], o["pickups"], o["events"] = t, pickups, list(events)
    o["self"]["weapons"] = [copy.deepcopy(w) for w in weapons]
    return o


def at(o, dx, dy, dz=0.0):
    x, y, z = o["self"]["pos"]
    return [x + dx, y + dy, z + dz]


class TestPick(unittest.TestCase):
    def test_order_real_offer(self):
        e = Economy(CFG)
        o = obs_with([])
        o["offer"] = {"id": 2, "expires": 61.35, "choices": [
            {"id": "gun_rate", "name": "Rotary feed", "desc": ""},
            {"id": "armor", "name": "Reactive armor", "desc": ""},
            {"id": "sensors", "name": "Sensor suite", "desc": ""}]}
        self.assertEqual(e.pick(o), 1)
        o["offer"]["choices"][2]["id"] = "plating"
        self.assertEqual(e.pick(o), 2)

    def test_no_offer_and_unknown(self):
        e = Economy(CFG)
        o = obs_with([])
        o["offer"] = None
        self.assertIsNone(e.pick(o))
        o["offer"] = {"choices": [{"id": "new_x"}, {"id": "laser_pierce"}, {"id": "new_y"}]}
        self.assertEqual(e.pick(o), 1)
        o["offer"] = {"choices": [{"id": "new_x"}, {"id": "new_y"}]}
        self.assertEqual(e.pick(o), 0)

    def test_every_config_id_ranked(self):
        e = Economy(CFG)
        self.assertTrue(all(u["id"] in e.rank for u in CFG["upgrades"]))


class TestLoot(unittest.TestCase):
    def test_laser_in_reach_taken(self):
        e = Economy(CFG)
        o = obs_with([{"id": 8001, "kind": "laser", "pos": at(OBS[0], 3, 0, 1)}])
        self.assertEqual(e.take(o), {"take": 8001})
        self.assertEqual(e.wanted_pickup(o, [])["id"], 8001)

    def test_out_of_reach_not_taken(self):
        e = Economy(CFG)
        self.assertEqual(e.take(obs_with([{"id": 8001, "kind": "laser", "pos": at(OBS[0], 5, 0)}])), {})
        self.assertEqual(e.take(obs_with([{"id": 8001, "kind": "laser", "pos": at(OBS[0], 1, 0, 5)}])), {})

    def test_mortar_ignored(self):
        e = Economy(CFG)
        o = obs_with([{"id": 8002, "kind": "mortar", "pos": at(OBS[0], 1, 0)}])
        self.assertEqual(e.take(o), {})
        self.assertIsNone(e.wanted_pickup(o, []))

    def test_full_slots_drop_non_gun(self):
        e = Economy(CFG)
        p = [{"id": 8003, "kind": "laser", "pos": at(OBS[0], 1, 1)}]
        mortar = {"kind": "mortar", "cooldown": 0, "stats": {}}
        self.assertEqual(e.take(obs_with(p, (GUN, mortar))), {"take": 8003, "drop": 1})
        self.assertEqual(e.take(obs_with(p, (mortar, GUN))), {"take": 8003, "drop": 0})

    def test_have_laser_or_charging(self):
        e = Economy(CFG)
        p = [{"id": 8003, "kind": "laser", "pos": at(OBS[0], 1, 1)}]
        laser = {"kind": "laser", "cooldown": 0, "charge": 0.3, "stats": {}}
        self.assertEqual(e.take(obs_with(p, (GUN, laser))), {})
        self.assertIsNone(e.wanted_pickup(obs_with(p, (GUN, laser)), []))

    def test_eta_limits(self):
        e = Economy(CFG)
        speed = OBS[0]["self"]["stats"]["walk_speed"]
        d = 8.0 * speed / 1.3  # eta 8 s: too far before t = 70, fine after
        p = [{"id": 8004, "kind": "laser", "pos": at(OBS[0], d, 0)}]
        self.assertIsNone(e.wanted_pickup(obs_with(p, t=30.0), []))
        self.assertEqual(e.wanted_pickup(obs_with(p, t=80.0), [])["id"], 8004)

    def test_threat_near_pickup(self):
        e = Economy(CFG)
        p = [{"id": 8005, "kind": "laser", "pos": at(OBS[0], 30, 0)}]
        th = {"id": 5, "pos": at(OBS[0], 130, 0), "vel": [0, 0, 0], "last_seen": 18.0}
        self.assertIsNone(e.wanted_pickup(obs_with(p, t=20.0), [th]))
        th["last_seen"] = 10.0  # stale: older than 5 s
        self.assertEqual(e.wanted_pickup(obs_with(p, t=20.0), [th])["id"], 8005)
        th["last_seen"], th["pos"] = 19.0, at(OBS[0], 200, 0)  # 170 m from the pickup
        self.assertEqual(e.wanted_pickup(obs_with(p, t=20.0), [th])["id"], 8005)

    def test_take_failed_backoff(self):
        e = Economy(CFG)
        p = [{"id": 8006, "kind": "laser", "pos": at(OBS[0], 1, 0)}]
        fail = [{"type": "take_failed", "id": 8006, "reason": "gone"}]
        self.assertEqual(e.take(obs_with(p, t=20.0, events=fail)), {})
        self.assertEqual(e.take(obs_with(p, t=24.0)), {})
        self.assertEqual(e.take(obs_with(p, t=25.1)), {"take": 8006})

    def test_recorded_stream_and_timing(self):
        e = Economy(CFG)
        start = time.perf_counter()
        for o in OBS:
            e.pick(o), e.wanted_pickup(o, []), e.take(o)
        per_tick_ms = (time.perf_counter() - start) * 1000 / len(OBS)
        self.assertLess(per_tick_ms, 1.0)


if __name__ == "__main__":
    unittest.main()
