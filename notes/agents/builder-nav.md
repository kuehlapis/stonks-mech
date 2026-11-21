# Builder: nav: journal

Owns: `python/nav.py` and `python/tests/test_nav.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Move toward a goal point without getting stuck.

## Plan

1. Grid or graph path over walkable ground.
2. Wall sliding and ledges.
3. Stuck detection and recovery (jump, jet, reroute).
4. Path cost that prefers cover.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Example bot walks into walls | Getting stuck outside the zone kills us | Path around buildings | open |

## Lessons

(none yet)

## Log (newest first)

- 2026-11-21, iteration 0: journal created. Next: start the current task.
