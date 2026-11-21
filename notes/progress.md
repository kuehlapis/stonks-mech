# Progress (resume here)

Updated by the moderator after every agent report. A new session reads this first, then `notes/agents/moderator.md`.

## State: 2026-11-21, iteration 2, branch `iter-1`

Iteration 2 (new session): sim phase 2 done (`sim/engine.py`), in-process runner `sim/inproc.py`, opponent pool `sim/bots/`, M1 snapshot `sim/versions/m1/`. Brain/nav/survival rewritten; sim phase 2 vs pool: 10.49 (M1 8.41). Benchmark command: `python sim/inproc.py --bot new=python/bot.py --count 1 --bot m1=sim/versions/m1/bot.py --count 1 --bot hunter=sim/bots/hunter.py --count 5 --bot camper=sim/bots/camper.py --count 3 --bot rusher=sim/bots/rusher.py --count 3 --bot ex=python/example_bot.py --matches 160 --jobs 14 --rotate`.

## State before (iteration 1)

Milestone: **M0 not yet reached** (M1 bot being assembled). Track score: not submitted. Bar to beat: 6.00.

| Part | Status | Where |
|---|---|---|
| Research (local) | done | `notes/research/{config,map,zone,upgrades,stream}.md`, `hello.json` |
| Research (online) | done | `notes/research/online-*.md` |
| Game plan | revised after Critic review | `notes/ideas/game-plan.md` |
| Alternative strategies | done (7 styles, A/B plan) | `notes/ideas/strategies.md` |
| Critic review of plan | 1st pass done; 2nd pass (vs online research) **running** | `notes/reviews/game-plan.md` |
| World module | done, committed | `python/world.py` |
| Perception, Economy, Combat | done, committed | `python/{perception,economy,combat}.py` |
| Survival, Nav, Brain | **running** (not committed) | `python/{survival,nav,brain}.py` |
| Bot entry + Dockerfile | done | `python/bot.py` |
| Simulator phase 1 | done, committed | `sim/` |
| Simulator phase 2 (weapons, loot, cubes, NPCs, drops, `--jobs`) | **running** | `sim/` |

## Next steps (in order)

1. Collect Survival, Nav, Brain reports; commit each after its tests pass.
2. Full check on `python/bot.py` (CLAUDE.md "Full check"), record a guardrail row in `notes/results.md`.
3. Sim: M1 ×1 vs example ×15, 100 matches; record a proxy row; write the first after-action review `notes/reviews/aar-2026-11-21-1.md`; replan.
4. Read the Critic's 2nd pass; fold M1-blocking items in before submitting.
5. Ask the user to submit M1 (outward-facing).

## If a session stopped mid-step

Running agents don't survive a stopped session. Files they half-wrote may be uncommitted: check `git status`, run that module's tests, and re-brief the agent from its journal (`notes/agents/<name>.md`) if the tests fail or the file is missing.
