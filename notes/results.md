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

Times are "direct / Docker" on this machine, not the 1-CPU match container.

## Local proxies (once the simulator exists)

| Iter | Date | Matches | Zone deaths (0%) | Ticks outside zone (≤ 2%) | Mean place vs example ×15 (≤ 2.0) | Gun hit rate 50–150 m (≥ 40%) | Rear-hit damage share (≤ 20%) | HP at ≤ 3 alive (≥ 60%) | Drops captured uncontested (≥ 80%) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-11-21 | – | no simulator yet | – | – | – | – | – | – |
| 1 | 2026-11-21 | 10 (×16 mechs) | 2.5% (4/160) | 2.56% | n/a: example ×16, mean place 8.51, score 7.49, wins 6.2% (≈ even share by construction) | 32.4% (3526 shots) | 53.9% | 72.4% (30 samples) | not simulated | 

Iter 1 note: **sim phase 1, example ×16** (`notes/tests/2026-11-21-sim-baseline.md`). First sim row, so Δ prev and Δ baseline are "–" (row 0 had no simulator). The sim leaves out mortar, laser, lightning, loot/pickups, crates, cubes, upgrades, NPCs, supply drops, trees, overhang slide-out and slope limits; in it every mech has only the gun. Proxies here are a calibration point, not a target check: "vs example ×15" and "drops captured" need a candidate bot and phase 2.

## What changed per iteration

| Iter | Change | Expected effect | Measured effect | Kept or reverted |
|---|---|---|---|---|
| 0 | Baseline: kit example bot, unchanged | – | numbers above | kept as baseline |
