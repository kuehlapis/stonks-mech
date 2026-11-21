# Progress (resume here)

Updated by the moderator after every agent report. A new session reads this first, then `notes/agents/moderator.md` and `notes/decisions.md`.

## State: 2026-11-21 evening, iteration 2, branch `iter-1`

Track score: **not submitted yet**. Leaderboard best ≈ 5.96 (baseline example bot 1.15). Scoring closes **Sun 11:00 AM EST**. Up to 4 submissions per hour.

### The most important fact (from the track page, joinbuilders.org/buildathon/tracks/builders)

Practice matches are **us vs 15 house bots (4 easy, 4 medium, 4 hard, 3 expert) acting as one squad**. They share vision, **never fight each other**, and **hunt us weakest first** (one early, more as we kill them, all of them late). So:
- Our place = 1 + squad bots alive when we die. Score = 15 − (squad bots still alive at our death).
- Points come from **killing hunters** (and from outlasting them in the final zone collapse at 415 s, where the most HP wins).
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

### Results (squad sim, 112 matches each, SE about 0.15)

| Build | Score | Kills/match |
|---|---|---|
| example bot | 1.01 | 0.3 |
| M1 (iteration 1) | 0.80 | 0.14 |
| iteration 2, hiding style | 1.3–1.6 | 0.5–0.6 |
| iteration 2, aggressive (current) | **1.71–1.74** | 0.8 |

1v1 duels: we beat easy bots 100%, but only about 45% against hard and expert, and lasers cause many of our deaths.

## Next steps (in order)

1. **Submit the current `iter-1` build to the track** to get real numbers: the squad model is a guess, and real scores are worth far more than sim tuning.
2. Improve duels against hard and expert: answer `charging: true` lasers by breaking line of sight, get a laser earlier, peek from cover.
3. Survive longer for the final collapse (most max HP wins at 415 s): plating and cubes, regen to full before 390 s.
4. If real scores come back far from the sim, recalibrate `sim/bots/squad.py` (`DEFEND_RANGE`, hunter schedule, tier aims).

## If a session stopped mid-step

Running agents don't survive a stopped session. Check `git status`, run the tests, and rerun the squad benchmark above.
