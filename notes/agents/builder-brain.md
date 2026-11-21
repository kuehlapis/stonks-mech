# Builder: brain: journal

Owns: `python/brain.py` and `python/tests/test_brain.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Choose one goal per tick and build one action.

## Plan

1. Goal priority: zone > retreat > fight > loot > roam.
2. Combine move, aim and fire from the modules.
3. Stay inside the time budget.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No arbitration | Modules would fight each other | Simple fixed priority list | open |

## Lessons

(none yet)

## Log (newest first)

- 2026-11-21, iteration 0: journal created. Next: start the current task.
