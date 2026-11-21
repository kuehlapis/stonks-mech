# Assumptions register (moderator, 2026-11-22)

Every assumption the plan rests on, with its source and status. Agents: challenge any row; say which are wrong, untested, or cheaply checkable.

## Measured state

| Build (vs zone-smart + retaliating squad unless noted) | Matches | Score | Kills | Median death |
|---|---|---|---|---|
| Current bot `s_base` (= the 1.6 track submission) | 112 (old squad) | 2.07 ± 0.15 | 1.36 | 101 s |
| `s_base` | 8 (seed 3) | 3.0 | 1.5 | 123 s |
| `r_run` (RUN_MODE + FIRE_POLICY) | 8 | 1.62 | 0.38 | 92 s |
| `r_run_end` (+ hide/regen/burn) | 56 (mixed squad code) | 1.04 ± 0.17 | 0.30 | 62 s |
| `r_run_end_aim` (r_run_end + AIM_PREDICT) | 8 | 1.62 | 0.25 | 99 s |
| `z_ladder` (r_run_end_aim + LADDER) | 8 | 2.12 | 1.25 | 107 s |
| `z_full` (everything) | 8 | 1.25 | 0.75 | 53 s |

Timing note: with less load, `ms_max` was 41 ms (r_run_end_aim) and 22 ms (z_ladder), against 101–146 ms when the machine was saturated, which supports "load, not code" (A16).
| Track: current bot | 48 | 1.6 | ? | ? |

Nothing built this session beats `s_base`. Untested alone: AIM_PREDICT, REAR_TURN, PEEK_AFTER_BEAM, RELOAD_PUSH, STRAFE_BOOST_E, STRAFE_JUMP, TAKE_MORTAR, FUNNEL, ZONE_LEAN, BURN_ENDGAME, REGEN_BREAK, LADDER, CUBE_CAP.

## Assumptions

| # | Assumption | Source | Status |
|---|---|---|---|
| A1 | Score = 16 − place, mean over 48 practice matches | user, track page | confirmed |
| A2 | Practice = us vs 15 house bots (4 easy, 4 medium, 4 hard, 3 expert) acting as one squad: shared vision, never fight each other, hunt us weakest first | user paste of track page | confirmed |
| A3 | Placement = squad bots alive when we die; squad bots never kill each other, so score = our kills + squad deaths to NPCs/zone before ours + outlasting at the final burn | derived from A2 + protocol | derived, not checked on track |
| A4 | Squad bots do NOT die to the zone | user directive (assume) | assumed; track unknown |
| A5 | House bots shoot back at whoever shoots them | user | given |
| A6 | Firing reveals us: gun heard 320 m, laser 380 m, beams show the shooter's exact position | protocol §Sound, §beams | confirmed (rules) |
| A7 | Hunter count = 1 + squad deaths, +1 at 150 s, +2 at 240 s, all from 300 s; weakest first | sim/bots/squad.py guess from track text "one early, more as you thin them out" | guess |
| A8 | Shared vision is instant and perfect; sightings remembered 30 s | squad.py:118 | guess |
| A9 | Non-hunters fire at us within 60 m (DEFEND_RANGE), or at any range for 10 s after we hit them | squad.py | guess (calibrated to example bot 1.01 vs track 1.15) |
| A10 | Hard/expert aim noise ≈ 0.006–0.03 rad, full lead; easy ≈ 0.044 rad | squad.py | guess |
| A11 | Squad bots walk (11.7 m/s), boost only when out of zone or stuck; never jet onto roofs | squad.py | guess (squad_chase adds boost + sound) |
| A12 | Squad bots ignore sounds | squad.py | guess |
| A13 | Squad bots loot lasers and pick upgrades; easy bots may not | squad.py / strategist | guess |
| A14 | The sim engine matches the real engine closely enough to rank strategies | sim/engine.py built from protocol | unverified; sim 2.07 vs track 1.6 |
| A15 | 8-match results are informative when the gap is large | moderator | weak; SE at n = 8 ≈ 0.4–0.9 |
| A16 | Time budget: 50 ms per decision; our worst case 74–146 ms was machine load | measured under load | unverified on an idle machine |
| A17 | Running away / holding fire lengthens survival | strategist P1 | **refuted in sim** (r_run 92 s vs 123 s) |
| A18 | Hiding until late pays ~+10 per match | critic (old zone-dumb squad) | void under A4 |
| A19 | Past 6.00 needs ~4+ kills per match or winning 1-v-2/1-v-3 fights vs medium/hard | strategist | derived from A3, A4, A7 |
| A20 | Bullets don't inherit shooter velocity; gun has no drop | sim/engine.py, protocol:303 | confirmed (rules + sim) |
| A21 | Trees block vision past 45 m but not shots; our world model has no canopy | protocol:369-372; world.py | confirmed |
| A22 | Holding a mortar gives enemy lasers +60% on us | protocol | confirmed |
| A23 | The "current highest 6.00" on the track was reached by some bot against the same squad | objective.md | given; how is unknown |

## Open question for everyone

How did someone reach 6.00 against this squad? Which of A3–A13 must be wrong for that to be possible, and what would that bot be doing?
