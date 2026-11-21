# Progress (resume here)

Updated by the moderator after every agent report. A new session reads this first, then `notes/agents/moderator.md`.

## State: 2026-11-21, iteration 2, branch `iter-1`

Milestone: **M0 reached** (direct and Docker checks pass); local M1 proxy score 8.58, track score not submitted. Simulator target still misses 0% zone deaths at 7%. Bar to beat: 6.00.

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

## Current next steps

1. Investigate the seven M1 zone deaths from the 100-match run; inspect Nav and zone transitions and fix the cause.
2. Continue simulator phase 2, starting with weapon firing and pickups, then cubes/upgrades, NPCs, and drops.
3. Add passive, aggressive, and camper opponents after phase 2 mechanics are present.
4. Rerun guardrails and proxies after changes; then decide whether M1 is ready to submit.

## Original handoff next steps (superseded)

1. Collect Survival, Nav, Brain reports; commit each after its tests pass.
2. Full check on `python/bot.py` (CLAUDE.md "Full check"), record a guardrail row in `notes/results.md`.
3. Sim: M1 ×1 vs example ×15, 100 matches; record a proxy row; write the first after-action review `notes/reviews/aar-2026-11-21-1.md`; replan.
4. Read the Critic's 2nd pass; fold M1-blocking items in before submitting.
5. Ask the user to submit M1 (outward-facing).

## If a session stopped mid-step

Running agents don't survive a stopped session. Files they half-wrote may be uncommitted: check `git status`, run that module's tests, and re-brief the agent from its journal (`notes/agents/<name>.md`) if the tests fail or the file is missing.
