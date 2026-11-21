# Tester: journal

Owns: `notes/tests/`, test harnesses and the local simulator (not bot behavior). Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration 1, simulator phase 2 (moderator brief): extend `sim/engine.py` to the full rules of `protocol.md` (laser, lightning, mortar, both fire slots, weapon loot, crates, cubes, upgrade offers, supply drops, NPC drones, trees for vision), keep the public API, ≤ ~10 ms per decision at 16 mechs, `--jobs N` and per-weapon/cause/cube/drop metrics in `sim/run.py`, schema test for observations, unit tests per feature, smoke run of 16 matches.

Status: done (see Log).

## Plan

1. Engine: weapon items in slots, the three weapons, events. Done.
2. Loot, crates, cubes, upgrades, drops, NPCs. Done.
3. Trees (`sim/trees.py`, 16 m grid, ellipsoid crowns, trunks). Done.
4. Tests: `sim/tests/test_phase2.py` (40) + stdlib schema validator `sim/tests/schema_check.py`. Done, 50/50 OK.
5. `run.py --jobs`, engine timing, new metrics. Done.
6. Smoke run, report `notes/tests/2026-11-21-sim-phase2.md`, results row. Done.

Done when: all features in, tests pass, ≤ 10 ms/decision, smoke run recorded. All met (p99 7.6 ms; slope/slide-out still not modelled).

Superseded plan (phase 1, iteration 1): engine/runner/tests/baseline, all done; see the Log.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No local simulator | Without it, every change waits for a 48-match submission | Phase 1 sim built (`sim/`) | done |
| Sim has gun only: no mortar/laser/lightning, loot, crates, cubes, upgrades, NPCs, drops | Real matches are decided by weapons and cubes; proxies measured on a gun-only world can mislead the fight/flee and loot work (M2–M4) | Phase 2 built: all of these in `sim/engine.py` | done |
| Trees ignored for vision | Sight lines differ from the server | Ellipsoid crowns + trunks in `sim/trees.py` (blocks 47% of clear 50–200 m lines); formula is an assumption | done (model unverified) |
| No overhang slide-out, roof-edge slide-off, 50° slope | Nav stuck rates differ from the server; nav proxies are optimistic | Slope test in `_move` (terrain gradient over the step), slide-out per §7 | open |
| NPC behaviour is assumption-heavy (standoff 20 m, no lead, bullet range 135 m) and NPCs cause ~16% of deaths in the sim | Over- or under-stating NPC danger skews the "fight NPCs / avoid NPCs" decision | Ask the Researcher for any evidence of NPC behaviour (spectator replays, other teams' notes); calibrate hit rate | open |
| Mortar direct = damage only (not + splash), laser linear charge scaling, lightning cone ±30° | Each changes a weapon's value by 20–50% in the sim | Settle from a recorded match with these weapons when one exists (Researcher) | open |
| Only the example bot as opponent | Track opponents are other teams' bots; a pool of one style overfits | Moderator is writing `sim/bots/`; `--count` mixes them | open (moderator) |
| Zone `center` semantics during shrink and same-tick tie place are assumptions | Wrong assumption shifts zone timing and placement scoring | Ask the Researcher to settle §9 / §4 from the recorded stream or other evidence | open |
| No per-tick timing harness over `check/stream.jsonl.gz` (mean/p99/max) | Guardrail table reports p50 as the mean stand-in | Small script replaying the stream and timing each answer | open |
| 100-match proxy runs take ~35 min serially | objective.md asks for ≥ 100 matches per measurement | Run matches in parallel processes (`--jobs`), when needed | done: `sim/run.py --jobs` |
| 100-match proxy runs take ~35 min serially | objective.md asks for ≥ 100 matches per measurement | `--jobs 8`: 16 matches in 39 s, so 100 matches ≈ 4 min, 0% late | done |

## Lessons

- Writing the test first for a timing rule (lightning 4 shots in 1 s) exposed a phase 1 off-by-one-tick that the phase 1 test had encoded as correct. Derive expected counts from the rule text, not from a run.
- Unit tests that call `observe()` every decision consume `m.events`; collect events from the observations, not from the mech.
- A tall (cubed) mech shooting at pitch 0 overshoots a normal one: size growth changes aim. Bots that aim at `pos.z + 4.5` from `muzzle_height` handle it; worth telling Combat.
- Profile first again paid off: a coarse 16 m tree grid with ellipsoid chords is 0.013 ms per line, so no need for anything cleverer.

- Measure world calls before optimising: `World.los` over 200 m is 0.04 ms, so straightforward per-pair vision is fine (engine ~5 ms/decision at 16 alive).
- A cheap invariant check (is any mech's cylinder inside geometry?) found two real physics bugs in minutes: the step-up exemption applied in the air, and falling into roof edges. Keep such diagnostics in mind for phase 2.
- Identical-bot runs make mean score ≈ 7.5 by construction; only the per-behaviour proxies (zone, rear share, hit rate, HP late) carry information there.
- Seeds reproduce matches exactly when bots are deterministic (seed 1004 replayed to the same end time), which makes A/B comparisons on the same seeds possible.
- Timing per match varies 2× with machine load from parallel agents; report the worst case.

## Log (newest first)

- 2026-11-21, iteration 2: moderator added `--jobs` to `sim/run.py` using isolated worker processes; two-match `--jobs 2` smoke run passed. A corrected M1 vs example x15 batch completed 100 matches (seeds 1000-1099): M1 mean score 8.58, mean place 7.42, win rate 4%, zone deaths 7%, outside-zone ticks 0.35%, rear damage share 9.8%, gun hit rate 85.5% (910 shots), HP at <=3 alive 80.0%, 0 exceptions. Raw JSON: `notes/tests/2026-11-21-m1-vs-example.json`; AAR: `notes/reviews/aar-2026-11-21-1.md`. Parallel runner work is done; phase 2 remains open, starting with weapons and loot.
- 2026-11-21, iteration 1, sim phase 2: full rules in `sim/engine.py` (weapons as slot items: laser, lightning, mortar; loot/take/drop with all `take_failed` reasons; crates; cubes with size growth; upgrade offers; supply drops; 12 NPC drones; every sound kind), trees in new `sim/trees.py`, `--jobs` + engine timing + per-weapon damage, deaths by cause, cubes, weapons held, drops, upgrades in `sim/run.py`. Found and fixed a phase 1 bug: held trigger banked a tick, 2nd gun shot at 0.20 s instead of 0.24 s (`_tick_cd`). Tests: `python -m unittest discover sim/tests` → 50 OK (schema validator accepts the recorded stream and every sim obs). Speed: 16 alive, 2,700 decisions: mean 4.28 ms, p99 7.62, max 13.2. Smoke `python sim/run.py --matches 16 --jobs 8 --seed 7 --bot "python -u python/bot.py" --bot "python -u python/example_bot.py"`: 38.9 s wall; bot.py score 9.12, place 6.88, wins 4/16, deaths gun 6 / npc 3 / zone 2 / laser 1, rear share 8.1%, laser held at end 31%, 0 drops, 0 NPC kills; example 7.39; 0% late, 0 exceptions. 16 assumptions listed in `notes/tests/2026-11-21-sim-phase2.md`. Results row "1 (sim phase 2)". Next: slope/slide-out, NPC calibration, opponent pool.

- 2026-11-21, iteration 1: built `sim/engine.py`, `sim/run.py`, `sim/tests/test_engine.py` (10 tests OK: `python -m unittest discover sim/tests`). Fixed two physics bugs found by an in-geometry check (seed 7000: 4–8 zone deaths/match from mechs stuck in walls → 0; overlap samples 2580 → 263, the rest curbs ≤ step_up). Added the moderator's mid-task asks: per-death records and HP at 415 s in the JSON, `--count`. Baseline `python sim/run.py --matches 10 --seed 1 --bot "python -u python/example_bot.py"`: mean score 7.49, place 8.51, wins 6.2%, zone deaths 2.5%, outside zone 2.56% of ticks, rear share 53.9%, gun hit 32.4% at 50–150 m (3526 shots), HP at ≤ 3 alive 72.4%, late 0.001%, 0 exceptions. Speed 2.98–7.86 ms/decision, max 28.3 s wall per match; worst full 8-minute estimate ≈ 38 s (≤ 90 s target). Report `notes/tests/2026-11-21-sim-baseline.md`, JSON `notes/tests/2026-11-21-sim-baseline.json`, results row iteration 1. Next: phase 2 weapons/loot; opponent pool; timing harness.
- 2026-11-21, iteration 0: baseline measured on `example_bot.py`. `check.py` PASS direct (p50 1.4 ms, p99 4.1, max 4.3, ready 208 ms) and PASS under the Docker sandbox (p50 6.7, p99 11.4, max 11.7, ready 1755 ms, 2 stale observations correctly skipped). Recorded in `notes/results.md` row 0. Docker on Windows Git Bash needs `MSYS_NO_PATHCONV=1` and `$(pwd -W)` for the `-v` path. Next: timing harness and simulator design.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
