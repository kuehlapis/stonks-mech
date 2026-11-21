# Results

One row per iteration (local) and per submission (track), newest last. Each row shows the change (Δ) against the previous row and against the baseline (iteration 0), so the improvement is visible at a glance. Targets come from `objective.md`. Raw output for each row goes in `notes/tests/<date>-<target>.md`.

## Track score (ground truth)

Current highest score on the track: **6.00**. Objective: **≥ 12.00** mean, ≥ 50% wins.

| Iter | Date | Commit | Mean score | Δ prev | Δ vs 6.00 | Win rate | Milestone |
|---|---|---|---|---|---|---|---|
| 0 | 2026-11-21 | e4c70b3 | not submitted | – | – | – | – |

## Guardrails (every build)

Times from `check.py` over the 300 recorded observations. `check.py` reports p50, not the mean; p50 stands in for the mean target.

| Iter | Date | Bot | Check direct | Check Docker | p50 ms (≤ 15) | p99 ms (≤ 35) | max ms (< 45) | Late | Ready ms (≤ 5000) | Crashes | Build s (≤ 180) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-11-21 | `example_bot.py` (baseline) | PASS | PASS | 1.4 / 6.7 | 4.1 / 11.4 | 4.3 / 11.7 | 0 / 0 | 208 / 1755 | 0 | 6 (cached) |
| 1 | 2026-11-21 | `python/bot.py` M1 | PASS | PASS | 1.9 / 6.5 | 3.1 / 11.0 | 3.4 / 12.5 | 0 / 0 | 1507 / 2505 | 0 | ~35 |

Times are "direct / Docker" on this machine, not the 1-CPU match container.

## Local proxies (once the simulator exists)

| Iter | Date | Matches | Zone deaths (0%) | Ticks outside zone (≤ 2%) | Mean place vs example ×15 (≤ 2.0) | Gun hit rate 50–150 m (≥ 40%) | Rear-hit damage share (≤ 20%) | HP at ≤ 3 alive (≥ 60%) | Drops captured uncontested (≥ 80%) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-11-21 | – | no simulator yet | – | – | – | – | – | – |
| 1 | 2026-11-21 | 10 (×16 mechs) | 2.5% (4/160) | 2.56% | n/a: example ×16, mean place 8.51, score 7.49, wins 6.2% (≈ even share by construction) | 32.4% (3526 shots) | 53.9% | 72.4% (30 samples) | not simulated | 
| 2 | 2026-11-21 | 100 (1 M1 + 15 example) | 7.0% (7/100) | 0.35% | M1 place 7.42 vs examples 8.58 (score 8.58 vs 7.42) | 85.5% (910 shots) | 9.8% | 80.0% (18 samples) | not simulated |

Iter 1 note: **sim phase 1, example ×16** (`notes/tests/2026-11-21-sim-baseline.md`). First sim row, so Δ prev and Δ baseline are "–" (row 0 had no simulator). The sim leaves out mortar, laser, lightning, loot/pickups, crates, cubes, upgrades, NPCs, supply drops, trees, overhang slide-out and slope limits; in it every mech has only the gun. Proxies here are a calibration point, not a target check: "vs example ×15" and "drops captured" need a candidate bot and phase 2.

## Iteration 2 proxy details

100 matches, seeds 1000-1099, one M1 bot against 15 example bots. Raw data: `notes/tests/2026-11-21-m1-vs-example.json`; review: `notes/reviews/aar-2026-11-21-1.md`.

| Metric | M1 | Example field |
|---|---:|---:|
| Mean score | 8.58 | 7.42 |
| Mean place | 7.42 | 8.58 |
| Win rate | 4.0% | 6.4% |
| Zone deaths | 7.0% | 3.1% |
| Time outside zone | 0.35% | 2.27% |
| Rear-hit damage share | 9.8% | 48.5% |
| Gun hit rate, 50-150 m | 85.5% (910 shots) | 31.9% (35,427 shots) |
| HP with at most 3 alive | 80.0% (18 samples) | 67.1% (282 samples) |
| Kills per mech-match | 0.32 | 0.94 |

Opponent figures aggregate the 1500 example mech-matches in these same runs. This is simulator phase 1: it has no non-gun weapons, loot, upgrades, NPCs, drops, or tree visibility.
| 1 (sim phase 2) | 2026-11-21 | 16 (`bot.py` ×1 vs example ×15, seed 7) | 12.5% (2/16) | 1.52% | 6.88 (score 9.12, wins 25%) | 80.2% (182 shots) | 8.1% | 74.7% (4 samples) | 0 of 0 attempted (bot does not contest drops) |

Iter 1 note: **sim phase 1, example ×16** (`notes/tests/2026-11-21-sim-baseline.md`). First sim row, so Δ prev and Δ baseline are "–" (row 0 had no simulator). The sim leaves out mortar, laser, lightning, loot/pickups, crates, cubes, upgrades, NPCs, supply drops, trees, overhang slide-out and slope limits; in it every mech has only the gun. Proxies here are a calibration point, not a target check: "vs example ×15" and "drops captured" need a candidate bot and phase 2.

Iter 1 (sim phase 2) note: **first row on the full-rules simulator** (`notes/tests/2026-11-21-sim-phase2.md`): weapons, loot, crates, cubes, upgrades, drops, NPCs, trees. Not comparable with the phase 1 row (different rules and a different bot), so Δ is "–". 16 matches is small: wins 25% = 4/16. NPCs caused 3 of our 12 deaths; NPC behaviour has several assumptions (see the report).

## What changed per iteration

Iteration 2: M1 versus example x15, 100 matches, seeds 1000-1099 (`notes/tests/2026-11-21-m1-vs-example.json`; AAR: `notes/reviews/aar-2026-11-21-1.md`). M1 score was 8.58 versus the opponents 7.42, but zone deaths were 7% (target 0%) and win rate was 4% versus 6.4%. Opponent metrics summarize the 1500 example mech-matches in these same runs. The phase 1 simulator is gun-only and has no economy.

| Iter | Change | Expected effect | Measured effect | Kept or reverted |
|---|---|---|---|---|
| 0 | Baseline: kit example bot, unchanged | – | numbers above | kept as baseline |
| 1 | Integrated M1 modules; N1/N2 fixes | +1.5 to +3 guessed | 100-match score 8.58 vs 7.42; 9.8% rear damage; 85.5% gun hits; 7% zone deaths | Keep M1, investigate zone deaths before submission |
| 2 | Stable hold point per circle; zone moves can't step outside the live circle | zone deaths → 0% | same seeds: score 8.73 (Δ +0.15, within noise), zone deaths 1.0% (Δ −6.0 pts), outside-zone 0.03%, rear 8.7%, win 4% (AAR 2) | kept |
