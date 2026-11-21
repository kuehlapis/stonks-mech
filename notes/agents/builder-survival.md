# Builder: survival: journal

Owns: `python/survival.py` and `python/tests/test_survival.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

2026-11-22 brief: R1 funnel + R4 zone lean from `notes/research/online-squad-survival.md`, behind switches off by default (`FUNNEL`, `ZONE_LEAN`); variants `s_funnel`, `s_zone_lean`. Done, awaiting sim results.

## Plan

1. Zone timing: when to leave for the next circle given distance and speed.
2. Retreat rule by HP and threat.
3. Face the strongest threat to avoid rear hits.
4. Pick safe spots with cover.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Funnel untested in sims | R1 expected +0.5 to +1.5 places in squad sims | Tester runs `s_funnel` vs base; check p99 act() | open |
| Zone lean uses only currently visible mechs | Remembered hunters ignored, so lean flips when they hide | Pass perception's tracked hunters if `s_zone_lean` shows promise | open |
| Funnel uses one LOS height (half body) | Top of mech may still be seen | Add the top check only if sims show hits at funnel spots | open |
| Zone handled naively | Zone deaths are the cheapest points to recover | Exact zone timing first | open |

## Lessons

- Timing tests on this machine are noisy under a sim batch: the same code gave 27-55 ms find_cover worst and 0.6-41 ms for a disabled search. Judge by median of several runs.
- Wall-cell normals from `nav.wall_cells` point into the building (find_cover's shadow test), not away from it.

## Log (newest first)

- 2026-11-22, iteration 1: added `FUNNEL`/`FUNNEL_MIN`/`FUNNEL_K`/`FUNNEL_N` and `Survival._funnel` (called inside `find_cover` after the keep-previous step, shares the 1 s cache and `LOS_CAP` budget via `los_calls`), and `ZONE_LEAN` in `_hold_line` (bisects our side and the side away from visible mechs' centroid). Tests: `TestFunnel` (4 tests) pass; funnel median 1.25-2.12 ms over 5 runs, worst 4.6 ms quiet / 26-78 ms under load. `TestTiming.test_timing` fails on every run (load: worst_hold 0.6 vs 41 ms with the search disabled; funnel off there). Variants: `sim/versions/s_funnel`, `sim/versions/s_zone_lean`. Next: sim results.

- 2026-11-21, iteration 0: journal created. Next: start the current task.
