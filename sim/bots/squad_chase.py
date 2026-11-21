"""Harder squad model (sim only): squad.py plus hunters that hunt by sound (boost and wall-slide now live in squad.py).
Roof jetting is not modelled: squad.py's nav has no roof/jet logic, only a stuck hop."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import squad  # noqa: E402  (imported as "squad" so it does not call mf.run)
import mechfight as mf  # noqa: E402

HEARD = {"step", "boost", "gun", "laser", "laser_charge", "lightning", "mortar", "reload", "jet"}
RANGE = {"near": 40.0, "mid": 110.0, "far": 200.0}


class Bot(squad.Bot):
    name = "squad_chase"

    def act(self, obs):
        me, t = obs["self"], obs["t"]
        x, y = me["pos"][0], me["pos"][1]
        reg = self.reg
        mates = reg.setdefault("pos", {})
        mates[self.slot] = (x, y)
        if self.slot in self._hunters(t) and not any(t - s["t"] < 3 for s in reg["seen"].values()):
            for s in obs.get("sounds") or []:
                if s.get("kind") not in HEARD or s.get("bearing") is None:
                    continue
                r = RANGE.get(s.get("dist"), 200.0)
                sx, sy = x + r * math.cos(s["bearing"]), y + r * math.sin(s["bearing"])
                # shortcut: drop sounds near a squad mate (sounds carry no source id)
                if all(math.dist(p, (sx, sy)) > 0.5 * r + 10 for k, p in mates.items() if k != self.slot):
                    reg["seen"]["sound"] = {"t": t - s.get("age", 0), "pos": [sx, sy, 0.0], "vel": [0, 0, 0], "hp": None}
                    break
        return super().act(obs)


if __name__ != "squad_chase":
    mf.run(Bot)
