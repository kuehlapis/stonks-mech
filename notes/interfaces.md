# Interfaces

Owned by the moderator. Builders code against this; a change here is a moderator decision (`notes/decisions.md`).

Conventions for every module: plain Python 3.13 standard library, world frame from protocol.md §5 (x east, y north, z up, meters, radians), points as `[x, y, z]` lists or tuples, no I/O except reading the map at startup, no printing to stdout.

## World (`python/world.py`): iteration 1

```python
class World:
    def __init__(self, map_dir: str) -> None:
        """Load v2/world.json and v2/terrain.i16 from map_dir. May raise; callers catch."""

    bounds: tuple[float, float, float, float]   # (min_x, min_y, max_x, max_y) from world.json

    def ground(self, x: float, y: float) -> float:
        """Terrain height (m) at x, y, sampled bilinearly. Outside the grid: nearest edge value."""

    def top(self, x: float, y: float, z: float) -> float:
        """Height of the highest walkable surface at x, y at or below z + 0.01:
        terrain or the top of a prism whose column contains (x, y) and whose top is <= z + 0.01."""

    def solid(self, x: float, y: float, z: float) -> bool:
        """True if (x, y, z) is inside a prism (ring minus holes, base <= z < top) or below the terrain."""

    def los(self, a, b) -> bool:
        """True if the straight segment a→b passes through no prism and stays above the terrain.
        Trees are ignored (they block vision only partly and never block shots)."""

    def blocked(self, x: float, y: float, z: float, radius: float, height: float, step: float = 1.2) -> bool:
        """True if a vertical cylinder (feet at z, given radius and height) standing at x, y
        overlaps any prism, ignoring surfaces it could step onto (top - z <= step) — the test nav uses."""
```

Performance budget (one call, on this machine, measured by the builder's tests):

| Call | Budget |
|---|---|
| `World(map_dir)` | ≤ 3 s, ≤ 150 MB |
| `ground`, `top`, `solid` | ≤ 0.02 ms |
| `los` over 200 m | ≤ 0.3 ms |
| `blocked` | ≤ 0.05 ms |

Hint (not binding): bucket prisms into a 2D grid of cells (e.g. 8 m) so each query tests only nearby prisms.

Known limits (callers handle them):
- `blocked` ignores the map edge and slopes steeper than `mech.max_slope_deg`; Navigation must treat both as walls. Pass `step=config.mech.step_up`.
- `los` ignores trees; Perception adds trunks and canopy if it needs true sight.
- `los` samples the ground every 1 m.

## Other modules

Defined after the Strategist's game plan and the Researcher's findings land (iteration 1, step 4). Until then, no builder other than World starts.
