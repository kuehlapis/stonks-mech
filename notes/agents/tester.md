# Tester: journal

Owns: `notes/tests/`, test harnesses and the local simulator (not bot behavior). Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration 1 (moderator brief): build `sim/`, a phase 1 local match runner for mechfight/1 (movement, aim, HP/regen, rear armor, zone, gun, vision, gun/step sounds, damaged/hit/kill events, placement), with tests, a CLI with per-bot metrics and JSON output, ≤ 90 s per 8-minute match; run 10 matches of example ×16 and record them. Mid-task additions from the moderator: per-death records (cause, killer, time, place, HP, position) and mean HP at 415 s in the JSON; `--bot CMD --count K` to mix opponents.

Status: done (see Log).

## Plan

1. Engine (`sim/engine.py`) against `python/world.py`, flat stub as fallback. Done.
2. Runner/CLI (`sim/run.py`): 16 processes, recorded hello config, lockstep 50 ms, coast-then-idle, end. Done.
3. Tests (`sim/tests/test_engine.py`): zone, cylinder hit, rear arc, gun front/rear damage, placement ties, coast/idle, bad action fields. Done, 10 pass.
4. Baseline 10 matches, report and results row. Done.

Done when: sim runs 10 matches end to end, tests pass, results recorded. All three met.

Superseded plan (iteration 0): "timing harness over the recorded stream" is still open; moved to Areas of improvement.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No local simulator | Without it, every change waits for a 48-match submission | Phase 1 sim built (`sim/`) | done |
| Sim has gun only: no mortar/laser/lightning, loot, crates, cubes, upgrades, NPCs, drops | Real matches are decided by weapons and cubes; proxies measured on a gun-only world can mislead the fight/flee and loot work (M2–M4) | Phase 2: loot + pickups + the three weapons first (largest effect on fights), then cubes/upgrades, drops, NPCs | open |
| Trees ignored for vision; no overhang slide-out, roof-edge slide-off, 50° slope | Sight lines and nav stuck rates differ from the server; nav proxies are optimistic | Add canopy/trunk test from `world.json` trees; slope test in `_move` | open |
| Only the example bot as opponent | Track opponents are other teams' bots; a pool of one style overfits | Moderator to commission passive / aggressive / camping opponents; `--count` already mixes them | open |
| Zone `center` semantics during shrink and same-tick tie place are assumptions | Wrong assumption shifts zone timing and placement scoring | Ask the Researcher to settle §9 / §4 from the recorded stream or other evidence | open |
| No per-tick timing harness over `check/stream.jsonl.gz` (mean/p99/max) | Guardrail table reports p50 as the mean stand-in | Small script replaying the stream and timing each answer | open |
| 100-match proxy runs take ~35 min serially | objective.md asks for ≥ 100 matches per measurement | Run matches in parallel processes (`--jobs`), when needed | open |

## Lessons

- Measure world calls before optimising: `World.los` over 200 m is 0.04 ms, so straightforward per-pair vision is fine (engine ~5 ms/decision at 16 alive).
- A cheap invariant check (is any mech's cylinder inside geometry?) found two real physics bugs in minutes: the step-up exemption applied in the air, and falling into roof edges. Keep such diagnostics in mind for phase 2.
- Identical-bot runs make mean score ≈ 7.5 by construction; only the per-behaviour proxies (zone, rear share, hit rate, HP late) carry information there.
- Seeds reproduce matches exactly when bots are deterministic (seed 1004 replayed to the same end time), which makes A/B comparisons on the same seeds possible.
- Timing per match varies 2× with machine load from parallel agents; report the worst case.

## Log (newest first)

- 2026-11-21, iteration 1: built `sim/engine.py`, `sim/run.py`, `sim/tests/test_engine.py` (10 tests OK: `python -m unittest discover sim/tests`). Fixed two physics bugs found by an in-geometry check (seed 7000: 4–8 zone deaths/match from mechs stuck in walls → 0; overlap samples 2580 → 263, the rest curbs ≤ step_up). Added the moderator's mid-task asks: per-death records and HP at 415 s in the JSON, `--count`. Baseline `python sim/run.py --matches 10 --seed 1 --bot "python -u python/example_bot.py"`: mean score 7.49, place 8.51, wins 6.2%, zone deaths 2.5%, outside zone 2.56% of ticks, rear share 53.9%, gun hit 32.4% at 50–150 m (3526 shots), HP at ≤ 3 alive 72.4%, late 0.001%, 0 exceptions. Speed 2.98–7.86 ms/decision, max 28.3 s wall per match; worst full 8-minute estimate ≈ 38 s (≤ 90 s target). Report `notes/tests/2026-11-21-sim-baseline.md`, JSON `notes/tests/2026-11-21-sim-baseline.json`, results row iteration 1. Next: phase 2 weapons/loot; opponent pool; timing harness.
- 2026-11-21, iteration 0: baseline measured on `example_bot.py`. `check.py` PASS direct (p50 1.4 ms, p99 4.1, max 4.3, ready 208 ms) and PASS under the Docker sandbox (p50 6.7, p99 11.4, max 11.7, ready 1755 ms, 2 stale observations correctly skipped). Recorded in `notes/results.md` row 0. Docker on Windows Git Bash needs `MSYS_NO_PATHCONV=1` and `$(pwd -W)` for the `-v` path. Next: timing harness and simulator design.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
