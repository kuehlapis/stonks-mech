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

- 2026-11-21, iteration 1: Critic reviewed game-plan.md: ready with fixes, 14 findings. High: fight-back ignores weapons (would repeat the recorded loss to a gun+laser mech); retreat doesn't break line of sight; edge hold leaves the rear open to mechs walking in from outside. Medium: hold-point formula past center in phase 6, cover search ~29 ms/tick, no stuck rule. Sent the Strategist to revise the plan. Critic does a second pass against the online research when it lands.
- 2026-11-21, iteration 1: Strategist wrote `notes/ideas/strategies.md` (7 styles, copy-robustness, review metrics). Its ranking, all unmeasured guesses: adaptive 10.5–13, farmer→turtle 9–11, edge-hold 9–11, camper, hider, vulture, roof sniper, drop chaser. Proposed A/B tests: farmer→turtle, pacifist hider, ambush add-on vs edge-hold, on 3 opponent pools (example ×15; laser/hunter mix; mirror field). Blocker: the farmer test needs crates, NPCs, cubes and upgrades, which sim phase 1 leaves out, so sim phase 2 must add them before that test means anything. The hider test can run on phase 1, but without trees it flatters hiding.
- 2026-11-21, iteration 1: Researcher done (6 files in `notes/research/`). Key: final circle hits radius 0 at 415 s so HP at 415 s decides 1st; plating is the best upgrade; walking always outruns the zone edge (be inside the next circle by `shrink_start`); a gun-only mech loses to a laser in the open; 0 of 162 config values differ from protocol.md; observations can skip seconds, so use `obs.t`, not tick counts. Open for later: whether plating heals the added HP; when phase 2+ circles are announced. Carry into interfaces: always send `pick`; don't plan with 0.1 s per observation.
- 2026-11-21, iteration 1: Strategist done (`notes/ideas/game-plan.md`; M1 = move to the next circle's near edge early, never start fights, fight back only when stronger, plating first, full HP at the 415 s collapse; its own estimate about 9 mean, unmeasured). Launched the Critic on the plan; it compares against the online research if that has landed, otherwise a second pass later. Added the Researcher (online) role at the user's request. Still running: Researcher, Researcher (online), World builder, Tester.
- 2026-11-21, iteration 1: branch `iter-1`, docs committed (eaab86f, 71b97b1). Wrote the World interface (`notes/interfaces.md`) and decision log. Launched the first wave in parallel in the main tree: Researcher (config, map, upgrades, zone, stream), Strategist (game plan with M1 staging), World builder (`python/world.py`), Tester (sim phase 1 + baseline run). Milestone: M0 not yet reached (no bot of our own). Next: read the four reports, have the Critic review the game plan and sim, write interfaces for the remaining modules, then brief the second wave of builders.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
