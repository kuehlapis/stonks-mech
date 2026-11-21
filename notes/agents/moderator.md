# Moderator (main session): journal

Owns: `python/bot.py`, `notes/decisions.md`, `notes/interfaces.md`, `notes/scores.md`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Start iteration 1: reach M0 (valid bot) and plan M1 (> 6.00).

## Plan

1. Brief the Researcher (map + config facts) and the Tester (baseline timing, simulator plan).
2. Write the first `notes/interfaces.md` for all modules.
3. Brief builders for World, Survival, Brain and a minimal `python/bot.py` that never crashes.
4. Integrate, run the full check, commit, ask the user to submit.

Done when the first build passes the full check and is ready to submit.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No bot of our own yet | Can't score at all | Ship a safe M0 build first | open |
| No local simulator | Only 48-match submissions give feedback, with ±0.7 noise | Prioritize the Tester's simulator | open |

## Lessons

(none yet)

## Log (newest first)

- 2026-11-21, iteration 0: journal created. Next: start the current task.
