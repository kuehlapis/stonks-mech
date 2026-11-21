# 2026-11-21: sim phase 1 baseline, `example_bot.py` ×16

Tester, iteration 1. Simulator: `sim/run.py` + `sim/engine.py`, geometry from `python/world.py`.

## Commands

```sh
python -m unittest discover sim/tests          # Ran 10 tests ... OK
python sim/run.py --matches 10 --seed 1 --bot "python -u python/example_bot.py" --out notes/tests/2026-11-21-sim-baseline.json
```

Full JSON (per match, per mech, every death with cause / killer / time / place / HP before the fatal hit / position): `notes/tests/2026-11-21-sim-baseline.json`.

## Summary (160 mech-matches)

| Metric | Value |
|---|---|
| Mean score (16 − place) | 7.49 (≈ 7.5 by construction: 16 identical bots) |
| Mean place | 8.51 |
| Win rate | 6.2% |
| Zone deaths | 2.5% (4 of 160; 146 gun deaths, 10 match winners) |
| Ticks outside zone | 2.56% of ticks alive |
| Rear-hit share of damage taken | 53.9% |
| Gun hit rate 50–150 m, moving target | 32.4% (3526 shots) |
| HP when ≤ 3 alive | 72.4% of max (30 samples) |
| HP at 415 s (survivors) | no samples: every match ended by elimination (251–404 s) |
| Late answers | 0.001% (1 decision), bad lines 0, `act()` exceptions 0 |
| Kills per mech per match | 0.91 |

## Speed (this machine, 16 bot processes, other agents running in parallel)

| Seed | Match end (s) | Wall (s) | ms / decision |
|---|---|---|---|
| 1000 | 367.1 | 10.93 | 2.98 |
| 1001 | 323.25 | 17.07 | 5.28 |
| 1002 | 364.75 | 14.79 | 4.05 |
| 1003 | 369.9 | 22.57 | 6.1 |
| 1004 | 387.3 | 28.31 | 7.31 |
| 1005 | 250.95 | 19.73 | 7.86 |
| 1006 | 328.0 | 19.44 | 5.93 |
| 1007 | 375.6 | 26.81 | 7.14 |
| 1008 | 403.95 | 25.74 | 6.37 |
| 1009 | 374.95 | 23.9 | 6.37 |

Worst full-length estimate: 4800 decisions × 7.86 ms ≈ 38 s per 8-minute match (target ≤ 90 s). Total wall for 10 matches: 3 min 38 s. Profile (in-process, seed 1004, first 200 s): engine ~5 ms observe + ~4.5 ms step per decision under cProfile; top costs `World.los` (vision), `World.blocked` (movement). Rerunning seed 1004 alone gave the same match end (387.3 s) at 5.95 ms/decision vs 7.31 in the batch, so part of the spread is machine load.

## Raw output

```
match 1/10 seed 1000: ended t=367.1 s, wall 10.93 s, 2.98 ms/decision
  1:s5 2:s12 3:s11 4:s0 5:s15 6:s3 7:s6 8:s13 9:s14 10:s9 11:s4 12:s7 13:s10 14:s2 15:s8 16:s1
match 2/10 seed 1001: ended t=323.25 s, wall 17.07 s, 5.28 ms/decision
  1:s4 2:s15 3:s14 4:s2/z 5:s9 6:s12 7:s13 8:s6 9:s5 10:s11 11:s0 12:s3 13:s1 14:s7 15:s8 16:s10
match 3/10 seed 1002: ended t=364.75 s, wall 14.79 s, 4.05 ms/decision
  1:s1 2:s6 3:s0 4:s10 5:s3 6:s7 7:s11 8:s4 9:s12 10:s13 11:s8 12:s15 13:s14 14:s9 15:s2 16:s5
match 4/10 seed 1003: ended t=369.9 s, wall 22.57 s, 6.1 ms/decision
  1:s10 2:s15 3:s0 4:s13 5:s1 6:s9 7:s2 8:s7 9:s11 10:s12 11:s3 12:s6 13:s14 14:s4 15:s8 16:s5
match 5/10 seed 1004: ended t=387.3 s, wall 28.31 s, 7.31 ms/decision
  1:s3 2:s14 3:s2 4:s15 5:s1 6:s6 7:s8 8:s11 9:s12/z 10:s9 11:s10 12:s13 13:s4 14:s0 15:s7 16:s5
match 6/10 seed 1005: ended t=250.95 s, wall 19.73 s, 7.86 ms/decision
  1:s1 2:s15/z 3:s5 4:s10 5:s3 6:s12 7:s7 8:s13/z 9:s8 10:s14 11:s9 12:s0 13:s6 14:s4 15:s2 16:s11
match 7/10 seed 1006: ended t=328.0 s, wall 19.44 s, 5.93 ms/decision
  1:s9 2:s7 3:s12 4:s3 5:s8 6:s10 7:s1 8:s6 9:s14 10:s15 11:s0 12:s5 13:s11 15:s2 15:s13 16:s4
match 8/10 seed 1007: ended t=375.6 s, wall 26.81 s, 7.14 ms/decision
  1:s12 2:s4 3:s10 4:s1 5:s9 6:s5 7:s7 8:s8 9:s2 10:s15 11:s11 12:s0 13:s13 14:s6 15:s14 16:s3
match 9/10 seed 1008: ended t=403.95 s, wall 25.74 s, 6.37 ms/decision
  1:s7 2:s13 3:s12 4:s10 5:s9 6:s8 7:s5 8:s11 9:s0 10:s4 11:s3 12:s14 13:s15 14:s1 15:s6 16:s2
match 10/10 seed 1009: ended t=374.95 s, wall 23.9 s, 6.37 ms/decision
  1:s12 2:s5 3:s9 4:s8 5:s1 6:s11 7:s13 8:s3 9:s0 10:s15 11:s2 12:s4 13:s7 14:s14 15:s10 16:s6
(per_bot JSON summary printed here; identical to the "per_bot" block of the JSON file)
real	3m37.541s
user	0m0.031s
sys	0m0.031s
```

## What phase 1 leaves out (phase 2)

Mortar, laser, lightning; loot, pickups, crates, cubes, upgrades and offers; NPC drones; supply drops; trees (vision ignores canopy and trunks); overhang/eave slide-out and roof-edge slide-off/step-on; max_slope_deg. Those obs fields are sent as `[]` / `null`.

## Known inaccuracies vs protocol.md

- Zone `center`/`radius` in obs are the phase's start circle (bots interpolate with `shrink_start/end`); §9 is ambiguous on this. Next circles are uniform random inside the current one with the center inside the arena; the real draw is unknown.
- Same-tick deaths all get place = mechs alive before that tick (§4 "share a placement"; the exact shared number is assumed).
- Projectiles are listed by range/fov only, no line-of-sight test.
- Roof edges: a mech whose footprint overlaps a surface lands on its highest point under the footprint (8 samples on the rim); no 0.6 m/tick slide-off.
- Terrain steeper than step_up per tick acts as a wall; slopes are not tested against 50°.
- Air control uses walk_speed as the target speed; jets apply with gravity, capped at max_rise_speed.
- A shot whose barrel is inside a wall is discarded (no stop at the wall surface; no damage either way).
- Gun hit-rate attribution: the intended target is the enemy within 10° of the aim yaw, 50–150 m away, moving > 1 m/s; a hit counts only on that target.
- Rear share counts weapon damage only (zone damage excluded).
- Spawns: open ground with nothing overhead, within 0.8 × start radius, 130 m apart (relaxed ×0.8 every 3000 failed tries).
