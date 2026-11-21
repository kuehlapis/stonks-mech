# Tester: journal

Owns: `notes/tests/`, test harnesses and the local simulator (not bot behavior). Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Establish the baseline and plan the local simulator.

## Plan

1. Run the full check on `python/example_bot.py` (direct and Docker) and record the results.
2. Write a timing harness: per-tick mean, p99 and max over the recorded stream.
3. Design a minimal local simulator (movement, zone, gun, vision) to measure the proxy metrics in objective.md.

Done when the baseline report exists and the simulator design is reviewed by the Critic.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No local simulator | Without it, every change waits for a 48-match submission | Build the smallest sim that measures zone deaths and placement | open |

## Lessons

(none yet)

## Log (newest first)

- 2026-11-21, iteration 0: baseline measured on `example_bot.py`. `check.py` PASS direct (p50 1.4 ms, p99 4.1, max 4.3, ready 208 ms) and PASS under the Docker sandbox (p50 6.7, p99 11.4, max 11.7, ready 1755 ms, 2 stale observations correctly skipped). Recorded in `notes/results.md` row 0. Docker on Windows Git Bash needs `MSYS_NO_PATHCONV=1` and `$(pwd -W)` for the `-v` path. Next: timing harness and simulator design.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
