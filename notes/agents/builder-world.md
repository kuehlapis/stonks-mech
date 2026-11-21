# Builder: world: journal

Owns: `python/world.py` and `python/tests/test_world.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration 1 brief from the moderator: implement `python/world.py` exactly to the `World` interface in `notes/interfaces.md` (ground, top, solid, los, blocked, bounds), with tests in `python/tests/test_world.py` that check real prisms and measure the performance budgets. Status: done, waiting for Critic review / Tester integration.

## Plan

1. Parse `world.json` prisms and `terrain.i16` (done).
2. Bilinear ground height, clamped at the grid edge (done).
3. Point-in-prism by ray casting over the prism's edges in a 1 m y-band (done).
4. 8 m spatial grid: each cell lists the prisms whose bbox touches it plus that prism's edges touching the cell; each cell also keeps its max terrain height (done).
5. `los`: 2D DDA over grid cells; per prism, clip the segment to the z-slab, test crossings with the cell's edges, then a midpoint-inside test; ground sampled every 1 m only in cells where the segment dips below the cell's max terrain (done).
6. `blocked`: cylinder overlap = center inside or any edge within radius, ignoring prisms with top ≤ z + step or base ≥ z + height (done).

Done when: tests pass on 3.12 and 3.13, every per-call time inside budget. Met (see Log). The old plan item "on failure return a world that reports nothing blocked" is superseded: the interface says `__init__` may raise and callers catch.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No map model | Nav, cover and aim all need it | Height, solid, LOS, blocked with a spatial grid | done (iteration 1) |
| `blocked` has no `step` in the interface | `step_up` is a config value (`config.mech`); hard-coding breaks the "read every balance number from hello.config" rule | Added optional `step=1.2` keyword (protocol §7 default); moderator should add it to `notes/interfaces.md` so nav passes the config value | open (proposal) |
| `blocked` ignores the map edge and slopes | Protocol §7: the map edge is a wall and slopes > 50° can't be walked; nav/sim may plan through them | Either nav checks `bounds` and slope, or add both to `blocked`; moderator's call | open (proposal) |
| LOS ignores trees | Trunks stop vision (§8); perception might expect an enemy visible that is behind a trunk | If perception needs it, add a separate `sight(a, b)` that includes trunks/crowns | open (proposal) |
| Terrain LOS samples every 1 m | A sub-metre ridge between samples could be missed | Exact segment vs bilinear-cell test if a test shows false clears | open (low impact) |
| Grazing cases (segment exactly through a vertex) | Strict crossing test may miss a line through a corner | Midpoint-inside test catches most; accept unless seen | open (low impact) |

## Lessons

- Brute-force references (ray casting over every prism, dense segment sampling) in the tests caught nothing in the module but caught three wrong hand-picked test points: buildings here are row houses sharing walls, so "15 m east of a building" was inside its neighbour. Find test points by scanning for a wall with open ground beyond, and check them with the reference first.
- A `while len(x) < N` loop that reads a fixed index on rejection hangs forever; always draw a fresh random sample per attempt.
- Polygons have up to 312 vertices; testing whole rings per query would blow the 0.02 ms budget. Bucketing edges by y-band (inside test) and by grid cell (los, blocked) keeps queries at a few edges.
- `tracemalloc` makes the load 35× slower; measure memory with `resource` in Docker instead.

## Log (newest first)

- 2026-11-21, iteration 1: built `python/world.py` (~250 lines, stdlib only) and `python/tests/test_world.py` (9 tests) + `python/tests/__init__.py`.
  Evidence: `python -m unittest discover python/tests` → `Ran 9 tests ... OK` on Python 3.12.4 (Windows) and 3.13.18 (`python:3.13-slim` in Docker, read-only, `--user 65534`, `--cpus 1`).
  Measured (3.12 local / 3.13 Docker): load 0.54 s / 0.77 s (budget 3 s); per-call ms ground 0.0046 / 0.0046, top 0.0067 / 0.0090, solid 0.0064 / 0.0090 (budget 0.02), blocked 0.0067 / 0.0042 (budget 0.05), los over 200 m (clear lines, no early exit) 0.042 / 0.033 mean (budget 0.3); separate run on 1000 clear 200 m lines: mean 0.053, p99 0.139, max 0.287 ms. Memory: RSS 11.6 → 31.6 MB across load in Docker (20 MB for World; budget 150 MB); tracemalloc peak 19 MB locally.
  Correctness: `solid` matches brute force on 1500 random points; `los` matches dense sampling on 40 random segments (some blocked).
  Result: done. Next: Critic review; moderator decides the `step` parameter, map-edge and trees proposals.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
