# Moderator (main session): journal

Owns: `python/bot.py`, `notes/decisions.md`, `notes/interfaces.md`, `notes/scores.md`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration 3 (2026-11-22): raise the practice score (placement vs the 15-bot squad; track 1.6, sim ~1.9). A/B strategies, movesets and weapon pickups in the squad sim; submit only when the sim predicts ≥ 6.00 (user rule). No commits unless the user asks.

## Plan

Iteration 3: (a) strategy batch `run_sq.sh`, (b) moveset/pickup batch `run_moves.sh`, (c) AAR + results rows, (d) adopt variants > 2 SE over `s_base`, (e) build peek-after-beam and reload-push if movesets pay.

Iteration 2 plan (superseded):
1. Diagnose the seven M1 zone deaths by seed and phase; fix the responsible zone or navigation behavior.
2. Finish simulator phase 2, starting with weapons and pickups; add cubes/upgrades, NPCs and drops after that.
3. Add varied opponents, then rerun 100-match proxies and full guardrails.
4. Write the AAR, update results and journals, and commit each validated iteration.

Done when zone deaths are eliminated, simulator phase 2 is complete, and a robust proxy improvement passes the full check.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| M1 still dies to the zone | 7% zone deaths in the 100-match proxy misses the 0% target and costs placements | Diagnose the seven zone-death trajectories and fix Nav/zone handling | open |
| Sim plateau ~1.9 vs 6.00 target | Placement vs the squad depends on outlasting hunters; tuned aggression barely moves it | Measure hiding, movesets and pickups; then the burn endgame (most HP at 415 s) | in progress |
| Unchecked facts from other sessions | The squad claim was doubted, then confirmed; waste either way | Check a claim against `protocol.md` or ask the user before acting on it | open |
| Simulator lacks weapons and economy | The current proxy excludes non-gun weapons, loot, upgrades, NPCs and drops | Continue phase 2 after diagnosing zone deaths | open |

## Lessons

- Hidden stderr (`2>/dev/null`) turned a missing-files crash into a silent empty batch. Always log errors to a file.
- A working-tree reset can drop uncommitted changes; recheck `git diff` before every batch.

## Log (newest first)

- 2026-11-22, iteration 3: scoring confirmed as placement, practice confirmed as vs squad. Re-applied HOLD_SEARCH off (63 tests pass). Added boost-strafe and hop switches (off). Wrote `notes/ideas/movesets.md`. Queued 10 variants vs squad (112 matches each). Rejected taking mortars (no aim code, +60% cook-off). Results pending.

- 2026-11-21, iteration 2: reconciled the stale handoff with the committed M1 modules; found and fixed the missing Critic N1 code condition and added the 30 ms optional-work guard. Corrected `check/check.py` to preserve explicit POSIX map paths on Windows; direct and Docker checks passed with the map mounted (Docker ready 2505 ms, p50/p99/max 6.5/11.0/12.5 ms). Full Python suite: 63 tests pass. Added parallel match execution (`--jobs 2`) to `sim/run.py`, then completed 100 M1 vs example x15 games. Result: M1 score 8.58 vs example field 7.42, but 7% zone deaths and 4% wins; see `notes/reviews/aar-2026-11-21-1.md`. Next: diagnose zone deaths and complete simulator phase 2.

- 2026-11-21, iteration 1: Tester done: sim phase 1 committed (f8bec8e), 10 tests pass (verified), ≤ 38 s per match. Baseline example ×16: zone deaths 2.5%, rear-hit share 53.9% (the biggest weakness of a naive bot), gun hit 32.4%. Assumptions to settle: zone center semantics during a shrink, same-tick tie places. Sent the Tester on phase 2: parallel runs, the three weapons, loot, cubes/upgrades, NPCs, drops. Opponent pool (passive/aggressive/camper bots) deferred until M1 exists, so they can reuse our modules.
- 2026-11-21, iteration 1: Researcher (online) done: 5 files with sources. Its top recommendations agree with the plan (zone discipline, fight only with good odds, a simulator first, face the threat, exact gun lead, minimum-risk spot scoring, plan for the 415 s collapse); new for M2+: strafe and dodging visible bullets, scanning toward the least-known direction. Several sources were unreachable and are marked. Critic resumed for a second pass (fix verification + comparison with the online recommendations). M1 builders (6) running; Tester running.
- 2026-11-21, iteration 1: Critic reviewed game-plan.md: ready with fixes, 14 findings. High: fight-back ignores weapons (would repeat the recorded loss to a gun+laser mech); retreat doesn't break line of sight; edge hold leaves the rear open to mechs walking in from outside. Medium: hold-point formula past center in phase 6, cover search ~29 ms/tick, no stuck rule. Sent the Strategist to revise the plan. Critic does a second pass against the online research when it lands.
- 2026-11-21, iteration 1: Strategist wrote `notes/ideas/strategies.md` (7 styles, copy-robustness, review metrics). Its ranking, all unmeasured guesses: adaptive 10.5–13, farmer→turtle 9–11, edge-hold 9–11, camper, hider, vulture, roof sniper, drop chaser. Proposed A/B tests: farmer→turtle, pacifist hider, ambush add-on vs edge-hold, on 3 opponent pools (example ×15; laser/hunter mix; mirror field). Blocker: the farmer test needs crates, NPCs, cubes and upgrades, which sim phase 1 leaves out, so sim phase 2 must add them before that test means anything. The hider test can run on phase 1, but without trees it flatters hiding.
- 2026-11-21, iteration 1: Researcher done (6 files in `notes/research/`). Key: final circle hits radius 0 at 415 s so HP at 415 s decides 1st; plating is the best upgrade; walking always outruns the zone edge (be inside the next circle by `shrink_start`); a gun-only mech loses to a laser in the open; 0 of 162 config values differ from protocol.md; observations can skip seconds, so use `obs.t`, not tick counts. Open for later: whether plating heals the added HP; when phase 2+ circles are announced. Carry into interfaces: always send `pick`; don't plan with 0.1 s per observation.
- 2026-11-21, iteration 1: Strategist done (`notes/ideas/game-plan.md`; M1 = move to the next circle's near edge early, never start fights, fight back only when stronger, plating first, full HP at the 415 s collapse; its own estimate about 9 mean, unmeasured). Launched the Critic on the plan; it compares against the online research if that has landed, otherwise a second pass later. Added the Researcher (online) role at the user's request. Still running: Researcher, Researcher (online), World builder, Tester.
- 2026-11-21, iteration 1: branch `iter-1`, docs committed (eaab86f, 71b97b1). Wrote the World interface (`notes/interfaces.md`) and decision log. Launched the first wave in parallel in the main tree: Researcher (config, map, upgrades, zone, stream), Strategist (game plan with M1 staging), World builder (`python/world.py`), Tester (sim phase 1 + baseline run). Milestone: M0 not yet reached (no bot of our own). Next: read the four reports, have the Critic review the game plan and sim, write interfaces for the remaining modules, then brief the second wave of builders.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
