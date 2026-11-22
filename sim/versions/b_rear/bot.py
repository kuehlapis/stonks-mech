"""Entry point: load the map (None on failure), build the Brain, run the protocol loop."""
import mechfight as mf
from brain import Brain


class Bot:
    name = "stonks-mech"

    def __init__(self, hello: mf.Hello):
        world = None
        try:
            from world import World
            world = World(hello["map"]["dir"])
        except Exception as e:  # map-free fallback, CLAUDE.md
            mf.log(f"world load failed, running map-free: {e!r}")
        self.brain = Brain(hello["config"], world, int(hello["slot"]))

    def act(self, obs: mf.Observation) -> mf.Action:
        return self.brain.act(obs)


mf.run(Bot)
