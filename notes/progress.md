# Progress (resume here)

Updated by the moderator after every agent report. A new session reads this first, then `notes/agents/moderator.md` and `notes/decisions.md`.

## Session 2026-11-22 (later): status
- User target now **mean 10**.
- Step 0 done: the map loads under the Docker sandbox. Windows needs `MSYS_NO_PATHCONV=1`, and the check passes `--map-dir` through `abspath`, which breaks `/arena`. Mount `arena/`, not `arena/v2`. `ready` took 6.1 s, over the 5 s guardrail.
- Sim change: squad slots (label `squad*`) take no zone damage (`sim/engine.py`, `sim/inproc.py`), per the user rule.
- Running: calibration with squad v2 at 40 seeds each for sub1, s_base2 and example. Output goes to `notes/tests/cal-immune-*.json`.

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
