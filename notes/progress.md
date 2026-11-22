# Progress (resume here)

## LATEST (2026-11-22 ~07:40 UTC, moderator session 3) — read first

**Submit this:** commit `e6768d2` (iter-1, squad mode ON + AIM_PREDICT + explore 25 s for a laser + HOLD_DEPTH 0.5). Full check passed 09:20 UTC: 99 tests, check.py direct, Docker sandbox with map (ready 1.7 s, max 1.5 ms). Nothing after squad mode has a track score yet: this submission is the key measurement.
Scoring closes Sun 11:00 AM EST. Leaderboard top ≈ 6.28 (rescoring on 96 seeds, scorer builders-4).

**RULES UPDATE (leaderboard page):** "excessive code reuse may result in disqualification" (including another team's entry). Do NOT submit or vendor giddy/other teams' code. Our squad mode is our own Python implementation of ideas, not their code. Scoring is now 96 fresh random seeds per run (scorer builders-4); identical code keeps its first builders-4 score. Leader 6.74 (Ahmad Suliman) at ~08:10 UTC.

**What changed (all measured on the calibrated squad sim, paired seeds, `sim/bots/squad.py`):**
| Build | Score | Kills/match |
|---|---|---|
| old default (c529ecc/ca4646a, track 1.60 / 1.93) | 2.09 (seed 21) | 0.84 |
| SQUAD_MODE (giddy-style rules: laser first, crate farm, engage/target/lose rules) | 2.55 | 1.52 |
| + LETHAL laser release + SQ_PRECHARGE 6 s (commit 518b8b0) | 2.73 | 1.66 |
| + AIM_PREDICT (commit 73c6302) | 2.52 vs 2.36 base (seed 22) | 1.45 vs 1.25 |

- Squad mode = `python/brain.py` `_decide_squad*`; turns itself off when 5+ mechs die without our kill (free-for-all finals safety, `FFA_DEAD`).
- **Key finding:** we pick up a laser in only 31% of matches; with a laser 3.15 kills/match, without 1.00.
- Adopted later: SQ_HUNT_T 25 s (explore for a laser early: 3.05 vs 2.88, laser deaths 15 -> 11), HOLD_DEPTH 0.5 (outside-zone time halved).
- Tested 09:00 UTC, no gain (kept OFF / unchanged): SQ_FIGHTMOVE (worse, 2.63 vs 2.81), COVER_BFS, SQ_LASER_AVOID, SQ_ENGAGE 35, SQ_MAXT 150, upgrade orders (nanites first: no effect, few offers), SQ_DROPS, aggressive crate farming, lightning-first.
- Tested, no gain (kept OFF): PEEK_LASER, SQ_RESET_HP 0.9, SQ_LOSE2 0.75, SQ_BACKSTAB 150, SQ_OUTGUN, SQ_SCAN 3 (spin-scan), SQ_HUNT_T 150 (explore for lasers; worse).
- Research: giddygiddyboy's MIT Go bot (base of most top-5 entries) studied from source (`charliescull/mech-royale-bot` drivers/giddy, upstream e19e3c8); its squad rules were re-implemented in Python. Building/running their binary was blocked by the safety classifier (third-party code); the user decides that route.


Updated by the moderator after every agent report. A new session reads this first, then `notes/agents/moderator.md` and `notes/decisions.md`.

## Match-run process rule (2026-11-22)

- **New track baseline:** submitted candidate `ca4646a` scored **1.93**. Future
  local and track comparisons use 1.93, not the older 1.60 submission.

- After every 16-match screener or 56-match confirmation, classify wins and
  deaths before any replan or next launch.
- Win categories: direct mech kills, NPC/drone-assisted removals,
  zone-assisted removals, final-burn/placement wins, and HP/position outcomes.
- Death categories: cause; `<120 s`, `120–300 s`, `300–415 s`, or `>415 s`;
  cover/LOS state; zone pressure; hunter/squad count; surprise state; and
  rear/exposed state.
- Select the single strongest evidence-backed counterstrategy, prioritizing
  element of surprise, cover/LOS, short ambush, zone timing/position, safe
  drone use/routing, and isolated squad-hunting adaptations.
- Build exactly one corrective package: one hypothesis, one primary metric,
  guardrails, and an explicit 16/56 screen or confirmation contract. No
  competing package may be built, queued, or stacked for that run.
- Record the result in `notes/reviews/` or `notes/decisions.md` and update the
  Critic and Strategist journals. The rule is documented in `CLAUDE.md`,
  `notes/decisions.md`, and `notes/ideas/iteration-brainstorm-2026-11-22.md`.

## Session 2026-11-22 (later): status
- `c_aim` rebuilt from `s_base2` with only `AIM_PREDICT=True` in
  `combat.py`; normalized isolation and raw diff confirmed. Report:
  `notes/tests/2026-11-22-c_aim-rebuild.md`. Combat tests 18/18 pass and
  the full suite passed 93/93 on rerun. No match batch run.
- Laser-defense A/B: 56 paired seeds 11/`--rotate`, `b_peek` = 1.96 ± 0.26
  vs the completed `s_base2` baseline 2.00 ± 0.25. Paired rerun score difference
  is -0.20 ± 0.20; paired kills -0.14 ± 0.14. Early deaths rose 48.2% to
  51.8%, laser hits fell from 1.20/match to 1.04/match in the rerun, and
  outside-zone ticks rose 0.34% to 0.44%. 0 act errors in both; b_peek had
  3 late answers and squad had 24. Verdict: no benefit; keep PEEK_AFTER_BEAM off.
  Report: `notes/tests/2026-11-22-b_peek56.md`.
- Authoritative current-squad 40-seed calibration completed with paired
  rotated seeds (`--seed 21 --rotate`), 40 matches each:
  sub1 `1.98 ± 0.29`, 0.90 kills, 55.0% early deaths, 0.00% anchor
  outside-zone ticks, 0 pre-415 squad zone deaths;
  s_base2 `2.20 ± 0.29`, 1.05 kills, 55.0% early deaths, 0.37%
  anchor outside-zone ticks, 0 pre-415 squad zone deaths;
  example `1.40 ± 0.28`, 0.45 kills, 67.5% early deaths, 2.95%
  anchor outside-zone ticks, 0 pre-415 squad zone deaths.
- Squad outside-zone ticks: sub1 27.10%, s_base2 27.18%, example 27.84%.
- Raw results: `cal-current-sub1.json`, `cal-current-s_base2.json`,
  `cal-current-example.json`.
- Calibration gate: sub1 and s_base2 exceed the target around 1.6;
  no bot A/B starts. Per handover, the next model-only action is to raise
  squad pressure (earlier hunters or DEFEND_RANGE 60 -> 80), not drone behavior.
- Post-fix 8-seed smoke: 0 pre-415 squad zone deaths, 0 squad/sub1 errors.
- Post-fix 40-seed sub1 rerun: sub1 **1.82 ± 0.27**, 0 pre-415 squad zone deaths,
  0 squad/sub1 errors, squad outside-zone ticks 27.93%, sub1 outside ticks 0%.
- Post-fix 40-seed s_base2: **1.55 ± 0.26**, 0 pre-415 squad zone deaths, 0 errors,
  bot outside-zone ticks 1.09%.
- Post-fix 40-seed example: **1.12 ± 0.22**, 0 pre-415 squad zone deaths, 0 errors,
  bot outside-zone ticks 2.29%.
- The 40-seed run passes the zero-zone-death and zero-error validity gates.
- User target now **mean 10**.
- **Clarified objective (2026-11-22):** zone and NPC/drone effects may support eliminations. The bot must control the match and finish the field, while reporting direct and assisted squad deaths separately. The submitted 1.6 score is the baseline.
- **Strategy direction (2026-11-22):** prefer cover, building geometry, LOS breaks, surprise re-engagement, and short ambushes over open duels. No camping or rear exposure; candidates must be isolated and paired-tested.
- **Priority (2026-11-22):** placement score first, kills second. Direct and assisted eliminations are reported separately and do not outweigh a placement win or survival improvement.
- **Hard-squad idea (2026-11-22):** test whether squad convergence plus lightning/mortar/laser AOE can force lower placement. It must be modeled as a reviewable opponent strategy, not a fake damage multiplier.
- **Maximum-hard-squad directive (2026-11-22):** the local squad should be made as hard as protocol and evidence permit. After every match batch, learn from deaths and enemy counters, change one strong root-cause package, and re-test under the hardest valid model. NPC/zone support may remain in the bot strategy.
- Step 0 done: the map loads under the Docker sandbox. Windows needs `MSYS_NO_PATHCONV=1`, and the check passes `--map-dir` through `abspath`, which breaks `/arena`. Mount `arena/`, not `arena/v2`. `ready` took 6.1 s, over the 5 s guardrail.
- Sim change: squad slots (label `squad*`) take no zone damage (`sim/engine.py`, `sim/inproc.py`), per the user rule.
- Calibration result with zone immunity only (`notes/tests/cal-immune-sub1.json`, 40 seeds): sub1 = **2.05 ± 0.28**, against a target of 1.6. Kills 0.93, median death 80 s. The squad had 0 zone deaths but **123 drone deaths** (about 3 per match), which inflates our score.
- User: squad bots move toward the next ring (they already did). User chose **drone routing**. `sim/bots/squad.py` now has `DRONE_AVOID = 50`: drone homes are shared, goals within 50 m of one are rejected, and bots steer away from any drone within 50 m while in the zone. Smoke test, 4 matches (`cal-route-smoke.json`): drone deaths went from about 3.1 to 2.75 per match, and sub1 scored 2.25. Small effect. Drone deaths at 22–38 s are probably bots already wounded, since one drone alone needs about 56 s.
- The 40-seed run with routing was **stopped by the user before it finished**. No result.

**Next:**
1. Ladder screener prepared: `sim/versions/z_ladder` rebuilt as an exact copy of `s_base2` with only `LADDER=True`; the existing invalid snapshot is replaced. The normalized diff is one Brain assignment, and `python -m unittest discover python/tests` passes 93/93.
2. Run the new 16-match ladder screener next: `python sim/inproc.py --bot z_ladder=sim/versions/z_ladder/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 16 --jobs 4 --seed 11 --rotate --out notes/tests/<ladder-screen-output>.json`.
3. Rejected laser defence remains off: b_peek **1.96 ± 0.26** vs s_base2 **2.00 ± 0.25**, paired -0.20 ± 0.20.

## HANDOVER: 2026-11-22 ~03:30, iteration 3, branch `iter-1` (read this first)

**Track scores:** f803b02 = 1.6, c529ecc (current default bot, all iteration-3 switches off) = **1.60**. 876 lines of fight changes between them did nothing on the track. Leaderboard best ≈ 5.96. Scoring closes **Sun 11:00 AM EST**; 4 submissions/hour; the user submits (give them repo `https://github.com/kuehlapis/stonks-mech` + full commit hash, then wait for the score).

**User rules (standing):**
- Score is placement (16 − place) vs a 15-bot squad (4 easy, 4 medium, 4 hard, 3 expert; shared vision; never fight each other; hunt us weakest first).
- **Squad bots never die to the zone** (user). They **shoot back at whoever shoots them**, and **shooting exposes us** (gun heard 320 m, laser 380 m, beams show the shooter).
- Commit after big changes; push freely to `iter-*` branches, never `main` without asking.
- Run agents as a continuous loop: the moderator evaluates each report and sends feedback.
- Ask the user for a track submission when one is needed, then pause.

**Key finding:** score ≈ kills + ~1 other squad death (drones). Sim s_base2, 56 matches: 1.88 = 0.91 kills + 0.97 other; 36% zero-kill matches; 64% dead before 120 s; 48/56 deaths by gun. So > 6 needs about 5 kills per match and surviving the first 2 minutes. Real house-bot data (`notes/research/house-bots.md`, from one FFA recording): react ~0.6 s, lead with ~0.023 rad error, full-charge lasers hit 4/5 at 100–150 m (90% of our damage), boost, zigzag, jet-hop, retaliate ≥ 31 s.

**Sim is NOT calibrated.** It gives c529ecc 1.88–3.0 against the track's 1.6, and the old squad still died to the zone (548/840). In progress (Tester journal `notes/agents/tester.md`, log `notes/tests/2026-11-22-calibration.md`): tune `sim/bots/squad.py` (the old one is kept as `squad_v1.py`) until, on 40 seeds:
- `sim/versions/sub1` (f803b02) = 1.6 ± 0.2,
- `sim/versions/s_base2` (c529ecc) = 1.6 ± 0.2,
- `example_bot` = 1.15 ± 0.2,
- 0 squad zone deaths before 415 s.

Make it realistic first (boost/zigzag like `squad_chase.py`, retaliate ~30 s, wall-slide unstick fix), then adjust the guessed knobs (DEFEND_RANGE, hunter schedule, 30 s shared memory, aim noise). **No sim result counts until this lands.**

**Built, all OFF by default (switch names in `python/brain.py`, `combat.py`, `survival.py`, `economy.py`), none proven to help:**
- Brain: PEEK_AFTER_BEAM, RELOAD_PUSH, REAR_TURN, BURN_ENDGAME, REGEN_BREAK, REGEN_HIDE, BURN_QUIET, RUN_MODE (+ RUN_HIT_S fix: after a hit, fight back facing the shooter), FIRE_POLICY, LADDER, STRAFE_BOOST_E, STRAFE_JUMP.
- Combat: AIM_PREDICT (strafer hit rate 0.20 → 0.40 in a unit test), mortar arc aim.
- Survival: FUNNEL, ZONE_LEAN.
- Economy: TAKE_MORTAR, CUBE_CAP.

Variants for each are in `sim/versions/` (untracked; rebuild with `python sim/variant.py NAME mod.CONST=val`).

**Measured so far (uncalibrated squad, mostly 8 matches = weak):** run mode alone made us die sooner (back to the shooter, up to 2/3 rear damage; fixed by RUN_HIT_S). Stacking everything (`z_full`) was worse. Nothing beat the default bot.

**Next steps, in order:**
0. **FIRST, cheap and decisive (Critic round 2):** check that the world map actually loads under the scorer's sandbox. `bot.py:10-15` silently falls back to map-free play. Run the Docker full check from CLAUDE.md (`--map-dir /arena`, `--cpus 1`, `--memory 512m`, read-only) on Linux or WSL (on Windows, `/arena` becomes `C:\arena`). Grep stderr for "world load failed" and note the `ready` time. If the map doesn't load there, both 1.60s were map-free play, and that is the bug to fix before anything else.
   - Also from the Critic: the track shows one decimal and its SE over 48 matches is ~0.2, so only changes of ≥ 0.4 are visible.
   - Prime suspects for losing the first fight (`brain.py`):
     - `WEAK_GUN` 0.6 + `OPEN_EDGE` 1.2 make gun-only hard bots look beatable. Test `WEAK_GUN=1.0`, `OPEN_EDGE=0.8`.
     - Kiting to 130 m (`FIGHT_RANGE`) is the laser's best range. Close to < 60 m behind cover, or break LOS, against laser holders.
     - `_ttk_ratio` ignores remembered enemies.
1. Finish calibration (above). **Status at handover (Tester):**
   - Only run c0 is done: sub1 vs the old `squad_v1.py`, 40 seeds, scored 1.23 ± 0.21. It is invalid, because squad bots died to the zone 320 times.
   - `squad.py` v2 is written but has never run a match. v2 adds: RETALIATE_S 30, 0.3–0.6 s jukes, chase boost beyond 40 m, wall slide, and a zone fallback that boosts to the next centre.
   - Next:
     - Run v2 against sub1, example and s_base2, 40 seeds each.
     - Confirm 0 squad zone deaths before 415 s.
     - If sub1 is still below 1.6: DEFEND_RANGE 60 → 45, or move the extra hunter from 150 s to 180 s.
   - The Tester's finding on the floor: score = mechs dead before us ≈ our kills + NPC kills of squad bots before we die (c0: 0.68 + 0.55 at a death around 60 s). Zone deaths come after ours, so they never count. So surviving longer early is the lever.
2. Baseline on the calibrated squad, 56 paired matches (`--seed 11 --rotate`). Then test one switch at a time against it, ranked by kills/match and the share dead before 120 s: laser defence (`s_duck30`, `b_peek`), AIM_PREDICT (`c_aim`), REAR_TURN (`b_rear`), LADDER, STRAFE_BOOST_E (`m_boost`), RUN_MODE (`r_run`).
3. Stack only the winners; re-test; commit with the switches ON; push; ask the user to submit; record in `notes/scores.md`.
4. Discussion round 2 (`notes/ideas/assumptions-discussion.md`, "Round 2: kills"). The Strategist's answer: we lose every even gun duel at range (their lasers land 4 of 5). Ranked:
   1. **K1, lightning ambush** (+1.5–2.5 kills). Lightning shorts their laser for 2 s and we fire every 0.25 s. Pick lightning BEFORE laser, wait 10–25 m past a corner for the hunter walking to our last position. First A/B, flags only: lightning-first pickup + `s_close`.
   2. **K2, peek laser** (+1–1.5): charge behind cover, step out, release, step back. They need ~1.35 s to answer.
   3. **K3, space the kills** (REGEN_BREAK / REGEN_HIDE on s_base2).
   4. **K4, laser damage upgrades first.**
   5. **K5, never open with the gun beyond 60 m on a laser holder.**

   Test K1 and K2 first on the calibrated squad. If neither adds ≥ 0.7 kills/match, suspect the squad model. The Critic's round 2 (challenge "score ≈ 1 + kills"; what loses our first fight) was still running when this was written.

**Pitfalls learned:**
- Never run two batches at once: stale loops overwrote results.
- Pipe test output to a file and check the exit code of the test command itself, not of `tail`.
- 8-match gaps under ~1.5–2 points are noise.
- Timing tests fail under sim load; the conformance check passes (max 4.5 ms).
- Don't edit `squad.py` while a run uses it.

**Key files:** `notes/ideas/assumptions.md` (all assumptions A1–A23), `notes/ideas/assumptions-discussion.md`, `notes/ideas/plateau.md`, `notes/reviews/*-2026-11-22.md`, `notes/decisions.md` (iterations 3–3c).

## Earlier state (local branch, superseded by the next section)

Milestone: **M0 reached** (direct and Docker checks pass); local M1 proxy score 8.73 (iteration 2), track score not submitted. Zone deaths 7% → 1% after the hold-point fix (AAR 2). Bar to beat: 6.00.

| Part | Status | Where |
|---|---|---|
| Research (local) | done | `notes/research/{config,map,zone,upgrades,stream}.md`, `hello.json` |
| Research (online) | done | `notes/research/online-*.md` |
| Game plan | revised after Critic review | `notes/ideas/game-plan.md` |
| Alternative strategies | done (7 styles, A/B plan) | `notes/ideas/strategies.md` |
| Critic review of plan | 1st and 2nd passes done; M1 code N1/N2 fixed | `notes/reviews/game-plan.md` and `python/brain.py` |
| World module | done, committed | `python/world.py` |
| Perception, Economy, Combat | done, committed | `python/{perception,economy,combat}.py` |
| Survival, Nav, Brain | integrated; N1/N2 code fixes validated | `python/{survival,nav,brain}.py` |
| Bot entry + Dockerfile | done | `python/bot.py` |
| Simulator phase 1 | done, committed | `sim/` |
| Simulator phase 2 (weapons, loot, cubes, NPCs, drops) | open; parallel `--jobs` runner done | `sim/` |

## State: 2026-11-21 evening, iteration 2, branch `iter-1`

Track score: **1.6** (first submission, commit f803b02; AAR 3). The squad sim's 1.71–1.74 matched it, so the sim is calibrated. Leaderboard best ≈ 5.96 (baseline example bot 1.15). Scoring closes **Sun 11:00 AM EST**. Up to 4 submissions per hour.

### The most important fact (from the track page, joinbuilders.org/buildathon/tracks/builders)

Practice matches are **us vs 15 house bots (4 easy, 4 medium, 4 hard, 3 expert) acting as one squad**. They share vision, **never fight each other**, and **hunt us weakest first** (one early, more as we kill them, all of them late). So:
- Our place = 1 + squad bots alive when we die. Score = 15 − (squad bots still alive at our death).
- Points are **placement** (16 − place, death order), not kills. Squad bots leave the count by our kills, by the zone, or by burning in the final collapse at 415 s, where the most HP survives longest. **Alive at 415 s with more HP than every remaining hunter = 1st place.** Kills help only by removing mechs that could outlast us.
- Hiding alone does not work; the early version that hid scored about 1.3 in the squad sim.

### How to submit (teammate)

The repo now has a **root `Dockerfile`** (builds `python/`, same image as `python/Dockerfile`) and a `.dockerignore`. So this repo can be submitted directly once `iter-1` is on the default branch (merge `iter-1` → `main`, or set the default branch to `iter-1`). The repo must be public. Checked locally: `check.py` under the Docker sandbox flags passes with the map loaded (ready 1.6 s unloaded, max tick 18 ms, 40 MB).

On Windows, `check.py --map-dir /arena` turns `/arena` into `C:\arena` (abspath), so the world fails to load in that local check. That's a local artifact; on Linux it's fine.

### What is in the bot (`python/`)

| Module | What it does now |
|---|---|
| `nav.py` | 2.5D grid (ground or roof height per 4 m cell). A* walks, drops, and **jets up walls** within energy reach; climbs by jump + jet. Exposure map of wall cells (1 s at startup). Random trips: 40/40 arrive (old nav 37/40) |
| `survival.py` | Zone urgency (travel only preempts fights when needed). Hold point by walking distance, beside a wall, low exposure. Cover = wall cells in the building's shadow at our height |
| `perception.py` | Mech tracks, unseen attackers, NPC tracks apart, danger memory (30 s) |
| `brain.py` | Modes: zone, fight (time-to-kill ratio by weapons, range, HP, cubes; hysteresis), evade to cover (fires all weapons), flee, open fire on lone enemies, NPC fights, farming drones and crates, hide from remembered enemies, final-circle centre. **Strafing** with fast random reversals, **projectile dodging** |
| `combat.py` | Gun lead (intercept), laser charge and release, aim tolerance per target |
| `economy.py` | Upgrade order (plating first), laser pickups |

Guardrails: `python -m unittest discover python/tests` passes (63 tests); the per-tick time guard skips the cover search past 30 ms.

### Simulator (all under `sim/`, never shipped)

- `engine.py`: full rules (phase 2 by the Tester): weapons, loot, crates, cubes, upgrades, drops, NPCs, trees.
- `inproc.py`: fast in-process runner, parallel, traces. Example:
  `python sim/inproc.py --bot new=python/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 112 --jobs 14 --rotate`
- `bots/squad.py`: **model of the house squad** (tiers, shared vision, hunter count grows with squad deaths and time, `DEFEND_RANGE = 60` m for non-hunters). Calibrated on the only real number: the example bot scores 1.01 here vs 1.15 on the track.
- `bots/hunter.py`, `camper.py`, `rusher.py`: free-for-all opponents (older pool, less relevant now).
- `variant.py`: copies `python/` with constants overridden, for A/B sweeps (`python sim/variant.py v_x brain.FIGHT_EDGE=1.2`).
- `versions/m1/`: the iteration-1 bot, as a regression baseline.

### Results (112–140 matches each, SE about 0.13)

| Build | Squad sim (defend 60 m) | Squad sim (non-hunters passive) | FFA pool (hunter/camper/rusher/example) |
|---|---|---|---|
| example bot | 1.01 | 1.70 | ~7 |
| M1 (iteration 1) | 0.80 | – | 8.27 |
| iteration 2, hiding style | 1.3–1.6 | – | 10.49 |
| **current `iter-1`** | **1.8–1.95** (about 1.1 kills/match) | **2.79** (1.56 kills) | **11.21** |

Real track: the example bot scores 1.15, so the real squad sits between the two squad-sim settings.

Tried with no measurable effect (within noise): exposure-weighted hold spots, danger-memory hiding, fight range 100–170 m, supply drops, upgrade order, laser pickup radius, projectile dodge alone. Helped: aggression (fight edge 1.2, opening fire on lone enemies, gun-only enemies treated as weaker), group fights, faster strafing, lightning support, farming.

## Current next steps

1. Six of seven zone deaths fixed (AAR 2). Replay seed 1042 (the one left: 7.5 s outside at 199 s) and fix its cause.
2. Continue simulator phase 2, starting with weapon firing and pickups, then cubes/upgrades, NPCs, and drops.
3. Add passive, aggressive, and camper opponents after phase 2 mechanics are present.
4. Rerun guardrails and proxies after changes.
5. Ask the user whether to submit M1 now for a first real score.

## Original handoff next steps (superseded)

1. **Submit the current `iter-1` build to the track** to get real numbers: the squad model is a guess, and real scores are worth far more than sim tuning.
2. Improve duels against hard and expert: answer `charging: true` lasers by breaking line of sight, get a laser earlier, peek from cover.
3. Survive longer for the final collapse (most max HP wins at 415 s): plating and cubes, regen to full before 390 s.
4. If real scores come back far from the sim, recalibrate `sim/bots/squad.py` (`DEFEND_RANGE`, hunter schedule, tier aims).

## If a session stopped mid-step

Running agents don't survive a stopped session. Check `git status`, run the tests, and rerun the squad benchmark above.
