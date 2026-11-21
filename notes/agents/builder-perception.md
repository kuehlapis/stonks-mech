# Builder: perception: journal

Owns: `python/perception.py` and `python/tests/test_perception.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Keep an up-to-date picture of every threat.

## Plan

1. Track mechs by id with position, velocity, weapons, HP, last seen.
2. Turn sounds, beams and damage bearings into threat directions.
3. Threat score per enemy.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Only current sightings used | Unseen attackers kill us from behind | Track and remember threats | open |

## Lessons

(none yet)

## Log (newest first)

- 2026-11-21, iteration 0: journal created. Next: start the current task.
