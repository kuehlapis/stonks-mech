# Tester: journal

Owns: `notes/tests/`, test harnesses and the local simulator (not bot behavior). Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

2026-11-22 bounded 16-pair strategy screen: ran only the clean candidate
`z_ladder` against `s_base2`, seed 11, rotate, jobs 4, against the current
`sim/bots/squad.py`. Result: z_ladder 2.81 ± 0.55 vs baseline 2.38 ± 0.46,
paired score delta +0.44 ± 0.45 and paired kill delta +0.25 ± 0.19.
No winner confirmed; stop remains at 16 pairs. Excluded r_run as bundled
(RUN_MODE + FIRE_POLICY) and b_rear/m_boost/s_close/s_duck30 as stale,
confounded snapshots. No bot behavior changed. Report and raw JSON:
`notes/tests/2026-11-22-screen-z-ladder16.md` and
`notes/tests/screen-2026-11-22-z_ladder-vs-s_base2-seed11.json`.

2026-11-22 maximum-hard squad model design: no code or matches are
authorized for this step. The model proposal, knob set and failure-learning
contract are documented in
`notes/ideas/maximum-hard-squad-2026-11-22.md`. Its first future calibration
must be a 40-seed/anchor run, but it must not start until the moderator
accepts the design and explicitly releases a match batch.

2026-11-22 paired screener: implement and validate `sim/screener.py`, a
16-seed/seed-11/`--rotate` paired no-code-change strategy runner. It must
support sequential or parallel candidate arms, report paired and absolute
metrics, block unapproved cover/ambush variants, and share a batch lock with
56+ match calibration runs. Status: **done**; unit and one-seed smoke pass.

2026-11-22 laser-defense switch: 56-paired-match `b_peek` test against the
calibrated squad. Result: no benefit (`1.96 ± 0.26` vs completed baseline
`2.00 ± 0.25`; paired rerun score difference `-0.20 ± 0.20`; kills
`-0.14 ± 0.14` paired). Status: **done**. Keep switch OFF.

2026-11-22 calibration baseline: one 56-paired-match run of `s_base2`
against the current `sim/bots/squad.py`, seed 11, rotation enabled.
Status: **done**. No bot behavior or switch was changed.

Iteration 3 bounded zone smoke: trace a pre-415 squad zone case and fix
the simulator model only. Status: **done**. Post-fix 4-match smoke has
0 pre-415 squad zone deaths and 0 simulator errors.

Iteration 1 (moderator brief, Critic plateau-2026-11-22 finding 3): harder squad model `sim/bots/squad_chase.py` (boost chase >40 m at energy >30, sound-bearing last-known position; roof jetting skipped: squad.py nav has none). Status: done (see Log 2026-11-22).

Previous: 
Iteration 1, simulator phase 2 (moderator brief): extend `sim/engine.py` to the full rules of `protocol.md` (laser, lightning, mortar, both fire slots, weapon loot, crates, cubes, upgrade offers, supply drops, NPC drones, trees for vision), keep the public API, ≤ ~10 ms per decision at 16 mechs, `--jobs N` and per-weapon/cause/cube/drop metrics in `sim/run.py`, schema test for observations, unit tests per feature, smoke run of 16 matches.

Status: done (see Log).

## Plan

Current screener plan:
1. Implement a 16-seed seed-11 rotated pair runner around `sim/inproc.play`.
2. Add direct/assisted candidate-death attribution and shared batch locking.
3. Reject cover/ambush candidates until Builder/Critic spec files exist.
4. Add unit tests and run the smallest simulator test slice.

1. Engine: weapon items in slots, the three weapons, events. Done.
2. Loot, crates, cubes, upgrades, drops, NPCs. Done.
3. Trees (`sim/trees.py`, 16 m grid, ellipsoid crowns, trunks). Done.
4. Tests: `sim/tests/test_phase2.py` (40) + stdlib schema validator `sim/tests/schema_check.py`. Done, 50/50 OK.
5. `run.py --jobs`, engine timing, new metrics. Done.
6. Smoke run, report `notes/tests/2026-11-21-sim-phase2.md`, results row. Done.

Current bounded trace: run pre-415 analysis on the immunity artifact, replay one
worst outside-zone slot, and separate zone deaths from outside-zone ticks.
Do not edit bot behavior or ship code.

Done when: all features in, tests pass, ≤ 10 ms/decision, smoke run recorded. All met (p99 7.6 ms; slope/slide-out still not modelled).

Superseded plan (phase 1, iteration 1): engine/runner/tests/baseline, all done; see the Log.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Maximum-hard squad spec not frozen | Different future test runs can silently change shared memory, pressure, mobility or hunter count | Freeze the proposed constants and three pressure arms in `notes/ideas/maximum-hard-squad-2026-11-22.md`; retain normalized diffs only | done (design-only) |
| Failure metrics do not separate direct and assisted removals consistently | A placement score can improve because NPC/drone/zone events, while the bot/tactic did not improve; this misreads winning behavior | Log direct mech kills, NPC-assisted squad deaths, drone-assisted squad deaths, zone removals, first-encounter size, weapon/cause, hunter count and time since sight/memory; never credit assisted squad deaths as direct kills | open (future harness change) |
| Pressure sensitivity 60/80/100 has no calibration order | Raising pressure can overfit one anchor and obscure whether the squad is too easy or too hard | Rank 60, 80, 100 with paired 40-seed anchor runs; valid gate first (0 zone deaths, 0 exceptions), calibration gate second | open |
| Squad memory expiration is not instrumented | Claims of 30 s shared tracking need a measurable expiry and source class | Record seen/memory source, age at first hunt, stale-target death share and re-acquisition time; reject guesses that expand memory beyond 30 s | open |
| Mobility metrics omit jet-hop/boost/zigzag outcomes | A model can claim realistic movement while failing to change contact duration or rear damage | Record boost distance/time, jet-hop count/vertical delta, strafe reversal intervals, rear damage share, first engagement range and LOS-break duration | open |
| Failure learning has no per-loss root-cause taxonomy | Repeating the same opening or wall wedge wastes batches | For each candidate death: classify hunter count, tier, weapon, range, LOS state, rear hit, memory age, zone/NPC assist and stuck state; aggregate one maximum-action replan per batch | open |
| No fast paired screener | 56-match calibration batches block iteration speed and are invalid for a single switch | Added a 16-seed seed-11 rotated screener with lock, direct/assisted attribution and candidate-arm parallelism | done |
| Exact-centre zone pull-back could divide by zero | The smoke found a simulator crash, invalidating model results and hiding the zone metric | Guard centre distance in `sim/bots/squad.py`; rerun 4 matches with 0 errors and 0 pre-415 zone deaths | done |
| No local simulator | Without it, every change waits for a 48-match submission | Phase 1 sim built (`sim/`) | done |
| Sim has gun only: no mortar/laser/lightning, loot, crates, cubes, upgrades, NPCs, drops | Real matches are decided by weapons and cubes; proxies measured on a gun-only world can mislead the fight/flee and loot work (M2–M4) | Phase 2 built: all of these in `sim/engine.py` | done |
| Trees ignored for vision | Sight lines differ from the server | Ellipsoid crowns + trunks in `sim/trees.py` (blocks 47% of clear 50–200 m lines); formula is an assumption | done (model unverified) |
| No overhang slide-out, roof-edge slide-off, 50° slope | Nav stuck rates differ from the server; nav proxies are optimistic | Slope test in `_move` (terrain gradient over the step), slide-out per §7 | open |
| NPC behaviour is assumption-heavy (standoff 20 m, no lead, bullet range 135 m) and NPCs cause ~16% of deaths in the sim | Over- or under-stating NPC danger skews the "fight NPCs / avoid NPCs" decision | Ask the Researcher for any evidence of NPC behaviour (spectator replays, other teams' notes); calibrate hit rate | open |
| Mortar direct = damage only (not + splash), laser linear charge scaling, lightning cone ±30° | Each changes a weapon's value by 20–50% in the sim | Settle from a recorded match with these weapons when one exists (Researcher) | open |
| Only the example bot as opponent | Track opponents are other teams' bots; a pool of one style overfits | Moderator is writing `sim/bots/`; `--count` mixes them | open (moderator) |
| Zone `center` semantics during shrink and same-tick tie place are assumptions | Wrong assumption shifts zone timing and placement scoring | Ask the Researcher to settle §9 / §4 from the recorded stream or other evidence | open |
| Squad model too soft (hunters walk, no sound hunting) | A/B robustness wins may not hold vs the track's house squad | `sim/bots/squad_chase.py`; roof jetting still missing | done (roofs open) |
| Squad bots wedge on walls once the zone pull-back is on (squad 5–8, chase 16 pre-burn zone deaths per 60) | Inflates squad zone deaths and outside-zone ticks | Zone exit now overrides combat/stuck side-slide in `sim/bots/squad.py`; exact seed smoke 2100033/6 reduced slot ticks_out 4,441 -> 3,355 | done |
| Sim not calibrated (v1: sub1 1.23 vs track 1.6) | Proxies over-reward fight changes (s_base sim 1.88 vs track 1.60) | v2 squad.py written; measure sub1, s_base2 and example on 40 seeds with 0 zone deaths before 415 s | in progress |
| No per-tick timing harness over `check/stream.jsonl.gz` (mean/p99/max) | Guardrail table reports p50 as the mean stand-in | Small script replaying the stream and timing each answer | open |
| 100-match proxy runs take ~35 min serially | objective.md asks for ≥ 100 matches per measurement | Run matches in parallel processes (`--jobs`), when needed | done: `sim/run.py --jobs` |
| 100-match proxy runs take ~35 min serially | objective.md asks for ≥ 100 matches per measurement | `--jobs 8`: 16 matches in 39 s, so 100 matches ≈ 4 min, 0% late | done |
| Pre-415 squad exit classifications | Zone immunity removes zone deaths; outside-zone ticks and pre-415 combat deaths remain | Highest replay cases classified as wall wedge, next-ring geometry, or short combat death | done |
| Post-fix sub1 calibration | Validate 40-seed sub1 score, 0 pre-415 zone deaths, 0 errors | 8-seed smoke passed zone/error guards; 40-seed rerun sub1 1.82 ± 0.27, 0 zone deaths, 0 errors | done |
| Remaining 40-seed anchors | Measure s_base2 and example with the current squad model and unchanged pressure | s_base2 1.55 ± 0.26; example 1.12 ± 0.22; both 0 squad zone deaths and 0 errors | done |

## Lessons

- The raw JSON is the source of truth: report the runner summary and independently verify squad pre-415 zone deaths.
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

- 2026-11-22, bounded 16-pair screen: ran shell `126` at seed 11 with
  `--seeds 16 --jobs 4`, rotate enabled, candidate `z_ladder` and baseline
  `s_base2`, each 16 matches against 15 current-squad bots. Wall time
  1152.59 s. z_ladder: 2.81 ± 0.55, 1.44 kills/match, 50.0% early, 5.8%
  rear damage, 1.56% outside-zone, 0 errors, 4 late. Baseline:
  2.38 ± 0.46, 1.19 kills/match, 56.2% early, 4.5% rear, 1.91%
  outside-zone, 0 errors, 3 late. Paired score delta +0.44 ± 0.45; paired
  kill delta +0.25 ± 0.19. Stopped at 16 pairs: no winner and no 56-match
  batch. Excluded r_run (bundled RUN_MODE/FIRE_POLICY) and
  b_rear/m_boost/s_close/s_duck30 (stale/confounded snapshots). Raw:
  `notes/tests/screen-2026-11-22-z_ladder-vs-s_base2-seed11.json`.
  Report: `notes/tests/2026-11-22-screen-z-ladder16.md`.

- 2026-11-22, maximum-hard squad design: analyzed
  `sim/bots/squad.py`, `notes/research/house-bots.md`, `protocol.md`,
  the current 40-seed calibration artifacts and recent 56-match traces.
  Wrote the no-code/no-match proposal
  `notes/ideas/maximum-hard-squad-2026-11-22.md`. Key evidence:
  30 s shared memory is already used; the 40-seed post-fix anchors are
  sub1 1.82 ± 0.27, s_base2 1.55 ± 0.26 and example 1.12 ± 0.22 with
  zero squad zone deaths; the authoritative seed-21 rerun has sub1
  1.98 ± 0.29 and s_base2 2.20 ± 0.29. The one observed bot in
  `house-bots.md` retaliated ≥31 s, boosted at 19.4 m/s, juked
  0.3–0.6 s and had ~0.023 rad hard/expert lead error. The proposed
  next model keeps memory 30 s, retaliation 31 s, tier aim/lead/reaction,
  all-hunter release at 300 s, full zone-safe routing and exact
  DEFEND_RANGE 60/80/100 sensitivity arms. No code or match was changed.

- 2026-11-22, paired screener implementation: added `sim/screener.py`,
  `sim/batchlock.py`, 16-seed seed-11 rotated candidate/baseline pairing,
  direct/assisted squad-death attribution fields in `sim/engine.py`, timing
  p99 reporting, PowerShell runner documentation, and unit tests. Existing
  variants remain usable; cover/ambush names are blocked until their
  Builder and Critic spec files exist. No `python/` bot behavior changed.
  Evidence: `python -m unittest sim.tests.test_screener` → 4 tests OK;
  seed-11 one-seed smoke completed in 253.76 s, 0 candidate/baseline
  errors, and wrote `notes/tests/paired-screener-smoke.json`.

- 2026-11-22, iter 1 (`b_peek` laser-defense A/B): rebuilt
  `sim/versions/b_peek` from current `python/` with only
  `brain.PEEK_AFTER_BEAM=True`; `LASER_DUCK=10.0` was unchanged. Ran 56
  paired matches seed 11 with `--rotate` against the calibrated squad.
  `b_peek` = **1.96 ± 0.26**, 0.95 kills/match, 51.8% early deaths,
  1.04 laser hits/match, 7.4% rear damage, 0.44% outside-zone ticks,
  3 candidate late answers, 0 candidate errors. Squad: 9.08 ± 0.15,
  27.68% outside-zone ticks, 24 late answers, 0 errors, 0 pre-415 zone deaths.
  Against the completed baseline `2.00 ± 0.25 / 0.98 kills / 48.2% early`,
  the standalone difference was -0.04 score / -0.03 kills / +3.6 pp early.
  An instrumented paired rerun gave b_peek-vs-baseline
  `-0.20 ± 0.20` score, `-0.14 ± 0.14` kills, and
  `-0.16 ± 0.17` laser hits/match. Laser hits were 58 for b_peek vs 67
  in the rerun baseline. Report:
  `notes/tests/2026-11-22-b_peek56.md`. Raw:
  `notes/tests/2026-11-22-b_peek56.json`. Verdict: no benefit; switch remains off.

- 2026-11-22, iter 1 (56-paired current-squad baseline): ran the exact requested command with seed 11, `--rotate`, 56 matches, and `--jobs 4`. `s_base2`: score **2.00 ± 0.25**, 0.98 kills/match, runner median death 133.5 s (raw standard median 131.15 s), early deaths 48.2%, causes gun 42 / laser 12 / NPC 1 / zone 1, rear damage 10.1%, outside-zone ticks 0.34%, 0 errors and 0 late answers. The one zone death occurred at 269.9 s. `squad`: score 9.03 ± 0.15, median death 107.0 s, 0.08 kills/match, causes NPC 146 / gun 41 / laser 20 / lightning 5, rear damage 52.2%, outside-zone ticks 27.75%, 0 errors and 0 late answers, and 0 squad zone deaths. Raw artifact: `notes/tests/cal-current-s_base2-baseline56.json`; report: `notes/tests/2026-11-22-cal-current-s_base2-baseline56.md`. No bot behavior or switch changed.
- 2026-11-22, current-squad 40-seed calibration: ran paired rotated
  `--seed 21 --rotate` batches sequentially against `sim/bots/squad.py`.
  sub1: `1.98 ± 0.29`, 0.90 kills/match, 55.0% early deaths, median
  108.7 s, bot outside-zone 0.00%, 0 pre-415 squad zone deaths.
  s_base2: `2.20 ± 0.29`, 1.05 kills/match, 55.0% early deaths, median
  87.9 s, bot outside-zone 0.37%, 0 pre-415 squad zone deaths.
  example: `1.40 ± 0.28`, 0.45 kills/match, 67.5% early deaths, median
  43.35 s, bot outside-zone 2.95%, 0 pre-415 squad zone deaths.
  Squad outside-zone ticks were 27.10%, 27.18%, and 27.84%.
  Raw: `notes/tests/cal-current-{sub1,s_base2,example}.json`.
  All run validity gates passed on squad zone deaths. No bot A/B run.

- 2026-11-22, iter 1 (remaining calibration anchors): ran s_base2 and example against the current squad model, 40 rotated seeds 2100025–2100064. s_base2: 1.55 ± 0.26, 0.85 kills, median death 64.3 s, 0 squad zone deaths <415 s, 0 errors, bot outside-zone 1.09%. example: 1.12 ± 0.22, 0.38 kills, median death 39.3 s, 0 squad zone deaths <415 s, 0 errors, bot outside-zone 2.29%. Squad outside-zone shares: s_base2 26.61%, example 26.96%. Raw artifacts: `notes/tests/cal-postfix-s_base2-40.json`, `notes/tests/cal-postfix-example-40.json`. Sub1 anchor remains 1.82 ± 0.27. The target bands are: sub1 met at the upper edge, s_base2 met inside SE, example met. Updated `notes/tests/2026-11-22-calibration.md`.
- 2026-11-22, iter 1 (post-fix calibration): 8-seed smoke seeds 2100025–2100032 produced 0 pre-415 squad zone deaths and 0 squad/sub1 act() errors. Squad outside-zone ticks 27.88%; sub1 outside ticks 0%. Full 40-seed run initially exposed 4 squad zero-distance exceptions, fixed with a goal-clamp guard in `sim/bots/squad.py`; simulator tests 50/50 passed. Clean rerun: sub1 1.82 ± 0.27, kills 0.88, median death 73.3 s, 0 pre-415 squad zone deaths, 0 errors. Squad outside-zone ticks 27.93%. Artifacts: `notes/tests/cal-postfix-smoke-sub1.json`, `notes/tests/cal-postfix-sub1-40.json`, `notes/tests/2026-11-22-postfix-calibration.md`.
- 2026-11-22, bounded zone smoke: replayed seed 2100000 slot 15, then ran
  `zone-smoke-4.json` (pre-fix): 60 squad mechs, 0 pre-415 zone deaths,
  but 1 simulator error from `squad.py:245` exact-centre division.
  Patched only `sim/bots/squad.py` to guard `d > 1e-9`.
  Reran the bounded 4-match setup:
  `zone-smoke-4-fixed.json`: 60 squad mechs, 0 pre-415 zone deaths,
  0 errors, 0 late answers. `python -m unittest discover sim/tests`:
  50 tests passed. No `python/` file changed.

- 2026-11-22, iter 1 (highest-ticks-out replay): replayed original highest cases seed/slot 2100025/13, 2100012/11, 2100021/5, 2100033/6, 2100010/8. Classification: 2100033/6 = wall wedge; 2100012/11 = next-ring geometry plus 85 s current-ring exit; 2100010/8 = next-ring geometry; 2100025/13 and 2100021/5 = short combat deaths, with no replay outside-ring evidence. Applied only a simulator fix in `sim/bots/squad.py`: during `zone_exit`, preserve centre-directed movement and suppress wall side-slide. Bounded exact replay 2100033/6 improved slot `ticks_out` from 4,441 to 3,355 (`-1,086`, -24.5%) and removed the 308 s low-progress interval. `python -m unittest discover sim/tests`: 50/50 passed. Report: `notes/tests/2026-11-22-pre415-squad-zone-trace.md`. Shipped bot behavior unchanged.

- 2026-11-22, iter 1 (bounded pre-415 zone trace): analyzed `notes/tests/cal-immune-sub1.json`, 40 seeds / 600 squad rows. Squad zone deaths = 0. Squad death causes in the 40-seed summary: NPC 123, gun 34, laser 13. Raw squad rows with `ticks_out > 0` = 449/600; max = 7,882 ticks, median = 1,448. Replay seed 2100025 / slot 13 with `--trace 13` was bounded to one match (480 s); trace artifact `notes/tests/squad-immune-seed2100025-slot13.jsonl`, summary `squad-immune-seed2100025-slot13.json`. The replay did not observe an outside-current-ring segment, so the worst 40-seed row needs exact seed/slot replay rather than a navigation change. Report: `notes/tests/2026-11-22-pre415-squad-zone-trace.md`. Next: replay worst `ticks_out` rows and classify next-ring exit vs wall wedge.

- 2026-11-22, iter 1 (calibration c1): v2 `squad.py` vs `sub1`, 40 rotated seeds (21–60), `--jobs 4`: score 2.23 ± 0.31, kills 1.02, median death 79.7 s, early death 72.5%, causes gun/laser/NPC 33/5/2. **Invalid:** correct raw-row `death_t` inspection (not the initially queried nonexistent `t`) finds 407 squad zone deaths before 415 s. The unchanged v2 example run is likewise invalid: 1.62 ± 0.34, kills 0.45, median death 39.55 s, 357 squad zone deaths before 415. Do not run s_base2. Trace the v2 zone regression first. Raw `notes/tests/cal-v2-sub1.json`, `cal-v2-example.json`.

- 2026-11-22, iter 3 (Docker map-load check, BLOCKED): inspected `CLAUDE.md`, root `Dockerfile`, and `python/bot.py`. The required Docker command is correctly specified and `bot.py` logs `world load failed` on fallback. A sandboxed `docker version` could not open `//./pipe/docker_engine` (Windows daemon permission denied). Requested elevated Docker access for the mandated read-only check, but it was user-aborted after 580 s with no returned output, so no Docker build/check result or map-load stderr evidence exists. Do not infer that the map loads; rerun exactly the CLAUDE command from a Docker-authorized Linux/WSL shell and grep stderr for `world load failed` and `ready`.

- 2026-11-22, iter 1 (calibration, UNFINISHED at session end): kept the old model as sim/bots/squad_v1.py. Wrote squad.py v2 (RETALIATE_S 30, strafe 0.3–0.6 s, chase boost > 40 m, wall slide, zone fallback boost); it imports, but no 40-seed run has measured it. Run c0 (squad_v1, 40 seeds): sub1 1.23 ± 0.21, kills 0.65, death_t_median 59.8 s, 320 squad zone deaths before 415 s, so invalid. Floor analysis: score ≈ our kills (0.65) + NPC kills of squad bots before we die (0.55). Details in notes/tests/2026-11-22-calibration.md. Next: v2 runs for sub1, example and s_base2.

- 2026-11-22, iter 1 (zone-death trace): squad_chase bots dying to the zone before 390 s were not pulled out by chase or sound guesses. Trace of slot 7 (seed 1, `--trace 7`): the bot sat wedged at (3,-140) for 90 s, jumping with move aimed at next_center, until the zone reached it. Root cause: a wall taller than step_up plus the ZONE_SMART pull-back, which re-aims at the same wall every tick, so squad's 'new goal after 3 s stuck' escape does nothing. squad.py has the same cause (5–8 deaths); chase is worse because boosting drains the energy needed to jet. Fix in squad_chase.py only: when stuck, slide sideways (flip every 4 s), jet only while airborne, no chase boost while stuck. Pre-390 zone deaths 25 -> 16 (squad.py 5–8); cur 4.0 / death_t_median 153.0. No-ret wrapper IndexError was my wrapper's fault (no mf.run call; inproc takes the class from mf.run), not an inproc bug; with that fixed, squad no-ret: cur 3.5 / 126.7 s, squad zone 31 (8 before 390 s). Wrote the Tester section of notes/ideas/assumptions-discussion.md (A9–A16).

- 2026-11-22, iter 1 (moderator follow-ups): squad.py gets `RETALIATE_S = 10.0` (hit by a non-squad mech -> hunts it 10 s, shares an 80 m bearing guess) and `ZONE_SMART = True` (goal clamped into next circle minus 15 m, move pulled back if >5 m past that, non-hunters skip fights to regen when next_radius <= 25). squad_chase inherits both. 4 matches each, seed 1, 0 errors: vs squad cur 3.75 / death_t_median 93.8, squad zone deaths 31 (26 in final burn >= 390 s, 5 before); vs squad_chase cur 4.25 / 166.4, zone 36 (16 final, 20 before: unexplained, open). A no-retaliation A/B wrapper failed in inproc (IndexError), not rerun. Lesson: don't edit a bot file while a batch using it is running (the first run mixed code).

- 2026-11-22, iter 1: built `sim/bots/squad_chase.py` (subclass of squad.Bot, ~40 lines). Smoke: 4 matches, cur ×1 vs squad_chase ×15, 0 errors; cur score 3.0 (se 0.91), win 0%, death_t_median 171.4 s, deaths gun 2 laser 1 zone 1; squad score 7.78, 38 zone deaths, late=9/6 (batch running in parallel). Out: scratchpad chase.json. Limit: sounds carry no id, so sounds near a squad mate's position are dropped (heuristic).

- 2026-11-21, iteration 2: moderator added `--jobs` to `sim/run.py` using isolated worker processes; two-match `--jobs 2` smoke run passed. A corrected M1 vs example x15 batch completed 100 matches (seeds 1000-1099): M1 mean score 8.58, mean place 7.42, win rate 4%, zone deaths 7%, outside-zone ticks 0.35%, rear damage share 9.8%, gun hit rate 85.5% (910 shots), HP at <=3 alive 80.0%, 0 exceptions. Raw JSON: `notes/tests/2026-11-21-m1-vs-example.json`; AAR: `notes/reviews/aar-2026-11-21-1.md`. Parallel runner work is done; phase 2 remains open, starting with weapons and loot.
- 2026-11-21, iteration 1, sim phase 2: full rules in `sim/engine.py` (weapons as slot items: laser, lightning, mortar; loot/take/drop with all `take_failed` reasons; crates; cubes with size growth; upgrade offers; supply drops; 12 NPC drones; every sound kind), trees in new `sim/trees.py`, `--jobs` + engine timing + per-weapon damage, deaths by cause, cubes, weapons held, drops, upgrades in `sim/run.py`. Found and fixed a phase 1 bug: held trigger banked a tick, 2nd gun shot at 0.20 s instead of 0.24 s (`_tick_cd`). Tests: `python -m unittest discover sim/tests` → 50 OK (schema validator accepts the recorded stream and every sim obs). Speed: 16 alive, 2,700 decisions: mean 4.28 ms, p99 7.62, max 13.2. Smoke `python sim/run.py --matches 16 --jobs 8 --seed 7 --bot "python -u python/bot.py" --bot "python -u python/example_bot.py"`: 38.9 s wall; bot.py score 9.12, place 6.88, wins 4/16, deaths gun 6 / npc 3 / zone 2 / laser 1, rear share 8.1%, laser held at end 31%, 0 drops, 0 NPC kills; example 7.39; 0% late, 0 exceptions. 16 assumptions listed in `notes/tests/2026-11-21-sim-phase2.md`. Results row "1 (sim phase 2)". Next: slope/slide-out, NPC calibration, opponent pool.

- 2026-11-21, iteration 1: built `sim/engine.py`, `sim/run.py`, `sim/tests/test_engine.py` (10 tests OK: `python -m unittest discover sim/tests`). Fixed two physics bugs found by an in-geometry check (seed 7000: 4–8 zone deaths/match from mechs stuck in walls → 0; overlap samples 2580 → 263, the rest curbs ≤ step_up). Added the moderator's mid-task asks: per-death records and HP at 415 s in the JSON, `--count`. Baseline `python sim/run.py --matches 10 --seed 1 --bot "python -u python/example_bot.py"`: mean score 7.49, place 8.51, wins 6.2%, zone deaths 2.5%, outside zone 2.56% of ticks, rear share 53.9%, gun hit 32.4% at 50–150 m (3526 shots), HP at ≤ 3 alive 72.4%, late 0.001%, 0 exceptions. Speed 2.98–7.86 ms/decision, max 28.3 s wall per match; worst full 8-minute estimate ≈ 38 s (≤ 90 s target). Report `notes/tests/2026-11-21-sim-baseline.md`, JSON `notes/tests/2026-11-21-sim-baseline.json`, results row iteration 1. Next: phase 2 weapons/loot; opponent pool; timing harness.
- 2026-11-21, iteration 0: baseline measured on `example_bot.py`. `check.py` PASS direct (p50 1.4 ms, p99 4.1, max 4.3, ready 208 ms) and PASS under the Docker sandbox (p50 6.7, p99 11.4, max 11.7, ready 1755 ms, 2 stale observations correctly skipped). Recorded in `notes/results.md` row 0. Docker on Windows Git Bash needs `MSYS_NO_PATHCONV=1` and `$(pwd -W)` for the `-v` path. Next: timing harness and simulator design.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
