# Scores

Current highest score on the track: **6.00**. Objective: **≥ 12.00** mean and ≥ 50% wins (`objective.md`).

| Date | Commit | Mean score | Win rate | Milestone | What changed |
|---|---|---|---|---|---|
| 2026-11-21 | f803b02 | **1.6** | not shown | M0 (valid, passes checks); M1 (> 6.00) not reached | First submission: iteration 2 aggressive bot (squad-sim estimate 1.71–1.74; example bot 1.15 on the track) |
| 2026-11-22 | c529ecc | **1.60** | not shown | M1 not reached | Current default bot (all iteration-3 switches off): +876 lines since f803b02 (aggression tuning, lightning, cube pickup, dodge, grounded boost-strafe). Sim said 1.88–3.0; track says no change. Second calibration anchor. |
| 2026-11-22 | ca4646a | **1.93** | not shown | M1 not reached | Latest submitted candidate: squad-mode laser-first/crate-farming/engage-retreat rules. New submitted baseline for local improvement comparison. |
| 2026-11-22 | 14bc978 (iter-submit, = iter-1 e6768d2) | **3.69** (96 seeds, builders-4) | not shown | entered the final (best) | Candidate A: squad mode (laser first, lethal release, precharge), AIM_PREDICT, explore 25 s, HOLD_DEPTH 0.5. Harsh squad sim said ~2.8-3.0: the real squad is softer. |
| 2026-11-22 | 82af545 (iter-submit, = iter-1 9204adb) | **3.76** (96 seeds) | not shown | entered the final (best) | Candidate B = A + LASER_JUKE (boost-sidestep lasers charging at us). +0.07 vs A (within noise, not worse). |
| 2026-11-22 | 4aae146 (iter-submit) | **3.71** (96 seeds) | not shown | not best | Candidate C = B + SQ_RESET_HP 0.9: -0.05 vs B (noise). Reset does not help. |
