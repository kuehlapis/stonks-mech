"""Opponent model: rusher style of hunter.py (sim only)."""
import mechfight as mf
from hunter import Bot as _B


class Bot(_B):
    style = "rusher"
    name = "rusher"


mf.run(Bot)
