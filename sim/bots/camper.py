"""Opponent model: camper style of hunter.py (sim only)."""
import mechfight as mf
from hunter import Bot as _B


class Bot(_B):
    style = "camper"
    name = "camper"


mf.run(Bot)
