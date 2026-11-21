# Builder: world: journal

Owns: `python/world.py` and `python/tests/test_world.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Load the map and answer height, inside-prism and line-of-sight queries fast.

## Plan

1. Parse `world.json` prisms and `terrain.i16`.
2. Bilinear ground height.
3. Line-of-sight test against prisms and terrain.
4. Spatial grid so each query is well under 1 ms.
5. Startup ≤ 5 s; on failure, return a world that reports nothing blocked.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No map model | Nav, cover and aim all need it | Build height + LOS first | open |

## Lessons

(none yet)

## Log (newest first)

- 2026-11-21, iteration 0: journal created. Next: start the current task.
