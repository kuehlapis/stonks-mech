import copy
import gzip
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
import brain as B  # noqa: E402

with gzip.open(ROOT / "check" / "stream.jsonl.gz", "rt") as f:
    msgs = [json.loads(line) for line in f if line.strip()]
HELLO = msgs[0]
OBS = [m for m in msgs if m.get("type") == "obs"]
CFG = HELLO["config"]


class Fake:
    def __init__(self, **ret):
        self.threats = ret.pop("threats", [])
        self.hit_by = ret.pop("hit_by", {})
        self.npcs = {}
        self._ret = ret

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a, **k: self._ret.get(name)


def enemy(x, hp=1400.0, weapons=("gun",), eid=7):
    return {"id": eid, "pos": [x, 0.0, 0.0], "vel": [0, 0, 0], "weapons": list(weapons), "hp": hp, "max_hp": 1400.0,
            "aim": [0.0, 0.0], "charging": False, "visible": True, "last_seen": 10.0, "virtual": False}


def obs0(alive=16):
    o = copy.deepcopy(OBS[0])
    o["self"]["pos"] = [0.0, 0.0, 0.0]
    o["t"] = 10.0
    o["alive"] = alive
    o["events"] = []
    return o


def brain(threats=(), hit_by=None):
    b = B.Brain(CFG, None, 3)
    b.perception = Fake(threats=list(threats), hit_by=hit_by or {})
    b.survival = Fake(hold_point=[50.0, 0.0])
    b.nav = Fake(step={"move": [1.0, 0.0], "boost": False, "jump": False}, free_at=True)
    b.combat = Fake(attack={"aim": [0.0, 0.0], "fire": [True, False], "reload": False},
                    face={"aim": [0.5, 0.0], "fire": [False, False]}, precharge=[False, False])
    return b


class TestSquadMode(unittest.TestCase):
    def setUp(self):
        self.saved = B.SQUAD_MODE
        B.SQUAD_MODE = True

    def tearDown(self):
        B.SQUAD_MODE = self.saved

    def mode(self, b, o):
        B.mf.draw.clear()
        a = b.act(o)
        return a, B.mf.draw.take()["label"]

    def test_close_enemy_is_fought(self):
        a, m = self.mode(brain([enemy(40.0)]), obs0())
        self.assertEqual(m, "fight")
        self.assertTrue(a["fire"][0])

    def test_far_idle_enemy_not_engaged(self):
        e = enemy(220.0)
        e["aim"] = [3.14, 0.0]  # looking away, not closing
        _, m = self.mode(brain([e]), obs0())
        self.assertNotIn(m, ("fight", "cornered"))

    def test_attacker_engaged_at_range(self):
        _, m = self.mode(brain([enemy(150.0)], hit_by={7: 9.0}), obs0())
        self.assertEqual(m, "fight")

    def test_losing_two_on_one_retreats_to_cover(self):
        b = brain([enemy(40.0), enemy(60.0, eid=8)])
        b.survival = Fake(hold_point=[50.0, 0.0], find_cover=[-20.0, 0.0, 0.0])
        o = obs0()
        o["self"]["hp"] = 0.5 * o["self"]["max_hp"]
        _, m = self.mode(b, o)
        self.assertEqual(m, "cover")

    def test_ffa_detection_turns_squad_mode_off(self):
        b = brain()
        b.act(obs0(alive=16))
        self.assertFalse(b._is_ffa)
        b.act(obs0(alive=16 - B.FFA_DEAD))  # five mechs gone, none by us
        self.assertTrue(b._is_ffa)

    def test_never_crashes_with_broken_modules(self):
        class Boom:
            def __getattr__(self, n):
                def f(*a, **k):
                    raise RuntimeError("boom")
                return f
        b = brain([enemy(40.0)])
        for name in ("perception", "survival", "nav", "combat", "economy"):
            setattr(b, name, Boom())
            a = b.act(obs0())
            self.assertIn("move", a)
            json.dumps(a)


if __name__ == "__main__":
    unittest.main()
