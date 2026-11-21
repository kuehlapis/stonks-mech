# Progress (resume here)

Updated by the moderator after every agent report. A new session reads this first, then `notes/agents/moderator.md` and `notes/decisions.md`.

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
