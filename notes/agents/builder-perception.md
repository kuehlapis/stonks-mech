# Builder: perception: journal

Owns: `python/perception.py` and `python/tests/test_perception.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration 1 (M1): implement `python/perception.py` + `python/tests/test_perception.py` against `notes/interfaces.md` "M1 modules" (moderator brief, 2026-11-21). Done: built, 6 tests pass, timing 0.015 ms mean.

## Plan

1. Track mechs by id with position, velocity, weapons, HP, last seen.
2. Turn sounds, beams and damage bearings into threat directions.
3. Threat score per enemy.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Only current sightings used | Unseen attackers kill us from behind | Track and remember threats | done (iter 1: memory_s tracks + virtual threats) |
| Virtual threat z is our own feet height | `update()` gets no world, so a virtual threat's eye isn't `ground + 8`; los checks against it would be off | Pass world to `update` (interface change) or let callers re-ground | open |
| Mortar virtual threat sits on the blast bearing | game-plan §1 says the bearing points at the blast, not the shooter | Callers must not aim along it; maybe offset 20 m sideways | open |
| No threat score, no beam use | Beams give exact shooter muzzle position for unseen laser/lightning shooters | Use `beams[].path[0]` to place virtual threats exactly | open |
| `los` ignores trees | `threatened_by` may flag enemies whose sight is blocked by trunks/canopy | Add trunks if false alarms show in sim | open |

## Lessons

- Reading the stream first (config keys, event shapes) kept the module small: everything needed was already in obs; no world needed in `update`.

## Log (newest first)

- 2026-11-21, iteration 1: built `python/perception.py` (tracks enemy mechs 0–15 by id, keeps them `vision.memory_s` after last seen, virtual threats from unseen `damaged.by` at 150 m laser / 100 m other, mortar marked `["mortar"]`, expire 3 s; engaged_by, threatened_by (15°, los eye `z + eye_height×size` to our center, charging first then nearest), damage_bearing, sound_bearing). Extra threat key `cubes` (for eye height). Evidence: `python -m unittest discover python/tests` → 27 tests OK; timing over 300 stream obs with real World: mean 0.015 ms, max 0.073 ms (budget 2 ms). Python 3.13 not installed here, ran on 3.12.4 only. Next: beams for exact shooter positions; world-grounded virtual z.

- 2026-11-21, iteration 0: journal created. Next: start the current task.
