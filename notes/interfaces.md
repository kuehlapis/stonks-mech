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

## M1 modules: iteration 1

Implements `notes/ideas/game-plan.md` §9 "M1" (rule ids like Z1, F3, N1 refer to it). Shared conventions:

- `cfg` is `hello["config"]` (a dict). `world` is a `World` **or `None`** (map failed to load): every module must work with `None` (map-free fallback, CLAUDE.md).
- `obs` is the raw observation dict. Time is `obs["t"]`, never tick counts (observations can be seconds apart).
- A *threat* is a dict: `{"id": int|None, "pos": [x,y,z], "vel": [x,y,z], "weapons": [str], "hp": float|None, "max_hp": float|None, "aim": [yaw,pitch]|None, "charging": bool, "visible": bool, "last_seen": t, "virtual": bool}` (`virtual` = built from an unseen attacker's damage bearing, game-plan §1).
- Points are `[x, y]` or `[x, y, z]` lists. Yaw/pitch per protocol.md §5.
- No module prints to stdout. Each module's `__init__` must not raise on a valid config.

```python
# python/perception.py: per-tick cost ≤ 2 ms
class Perception:
    def __init__(self, cfg: dict, my_id: int) -> None: ...
    def update(self, obs: dict) -> None: ...          # call once per obs, first
    threats: list[dict]                               # visible + remembered (vision.memory_s) + virtual, enemies only (mechs, not NPCs)
    def engaged_by(self, t: float) -> dict | None:    # threat that damaged us (by = mech id 0–15) in the last 3 s, else None
    def threatened_by(self, obs: dict, world) -> dict | None:   # visible enemy aimed_at_me (≤ 15°, with los), charging first
    def damage_bearing(self, t: float) -> float | None:         # bearing of latest damaged event ≤ 3 s old
    def sound_bearing(self, t: float) -> float | None:          # latest combat sound near/mid ≤ 3 s old

# python/survival.py: per-tick cost ≤ 10 ms worst case (cover search), ≤ 1 ms otherwise
class Survival:
    def __init__(self, cfg: dict, world) -> None: ...
    def hold_point(self, obs: dict) -> list:          # Z2, clamped and snapped off buildings
    def zone_goal(self, obs: dict) -> tuple[list, bool] | None:   # Z1: (goal, boost) when we must move for the zone, else None
    def hold_facing(self, obs: dict) -> float:        # Z4 yaw (outward or inward)
    def find_cover(self, obs: dict, threats: list) -> list | None:  # F3, ≤ 32 los calls, cached 1 s
    def final_center(self, obs: dict) -> list | None: # phase 6: next_center when we should stand on it, else None

# python/nav.py: per-tick cost ≤ 3 ms
class Nav:
    def __init__(self, cfg: dict, world) -> None: ...
    def step(self, obs: dict, goal: list, boost: bool = False, quiet: bool = False) -> dict:
        """Returns {"move": [dx, dy], "boost": bool, "jump": bool} toward goal.
        Avoids buildings, applies the N1 stuck rule, never targets out-of-reach towers.
        quiet=True keeps speed under sound.step_speed. Arrived (within 2 m): move [0, 0]."""

# python/combat.py: per-tick cost ≤ 1 ms
class Combat:
    def __init__(self, cfg: dict, world) -> None: ...
    def attack(self, obs: dict, target: dict) -> dict:
        """{"aim": [yaw, pitch], "fire": [bool, bool], "reload": bool} at a threat: gun with lead
        (intercept from target vel and gun speed), laser charged and released at full charge
        when the actual aim is on target, nothing fired out of range or without los."""
    def face(self, obs: dict, yaw: float) -> dict:
        """{"aim": [yaw, 0.0], "fire": [False, False]} and releases (stops) any laser charge."""

# python/economy.py: per-tick cost ≤ 1 ms
class Economy:
    def __init__(self, cfg: dict) -> None: ...
    def pick(self, obs: dict) -> int | None:          # U1: index into offer choices, or None if no offer
    def wanted_pickup(self, obs: dict, threats: list) -> dict | None:   # L1: the laser pickup to walk to, else None
    def take(self, obs: dict) -> dict:                # {"take": id} (+ "drop") when a wanted pickup is in reach, else {}

# python/brain.py: whole act() ≤ 15 ms mean, ≤ 35 ms p99
class Brain:
    def __init__(self, cfg: dict, world, my_id: int) -> None:   # builds the five modules above
    def act(self, obs: dict) -> dict:                 # the full action (tick is filled in by the wrapper)
```

`python/bot.py` (moderator) loads the World (catching any error → `None`), builds `Brain`, and calls `mf.run`.

## Later modules

Defined when M2+ work starts.
