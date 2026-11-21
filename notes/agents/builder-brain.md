# Builder: brain: journal

Owns: `python/brain.py` and `python/tests/test_brain.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Add five OFF-by-default moves to brain.py (moderator brief 2026-11-22, from notes/ideas/movesets.md and mechanics.md): PEEK_AFTER_BEAM, RELOAD_PUSH, REAR_TURN, BURN_ENDGAME, REGEN_BREAK; variants b_peek, b_reload, b_rear, b_burn, b_regen for A/B.

## Plan

1. Goal priority: zone > retreat > fight > loot > roam.
2. Combine move, aim and fire from the modules.
3. Stay inside the time budget.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No arbitration | Modules would fight each other | Simple fixed priority list | done |
| Reload estimate sees only hits on us | Misses are invisible, so the window is timed, not counted | Use visible gun projectiles near the enemy if A/B shows promise | open |
| RUN_MODE untested; far point not walkability-filtered | Main P1 lever on death time | A/B r_run vs current; filter points with nav.free_at if units stall | open |
| REGEN_HIDE/BURN_QUIET untested in sim | Aimed at death time toward ~400 s | A/B b_regen_hide vs b_regen, b_burn_quiet vs b_burn | open |
| Five new moves untested in sim | Unknown effect on mean placement | A/B b_peek/b_reload/b_rear/b_burn/b_regen vs s_base | open |

## Lessons

- world.los ignores canopy: tree hides need a world change first.
- Sounds carry no `by`, so per-enemy shot counts must come from `damaged` events (hits only).

## Log (newest first)

- 2026-11-22: shots reveal us. Any fire (RUN_MODE or FIRE_POLICY) sets _revealed_t/_revealed_pos and refreshes _seen_t; _far_point avoids the firing spot; run-wait never rests within 40 m of it. Return fire masks the laser slot when we have a gun, unless the laser kills (_prefer_gun). FIRE_POLICY drops early reload while a hunter has LOS. test_brain 27 OK. Rebuilt r_run, r_run_end.

- 2026-11-22: diff-65bd2fe fixes: hidden _hide walks quietly to the fallback (far point) and stores (t, spot); run-wait uses spot only if < RUN_HIDE_S old, does quiet zone travel when zone_goal exists; _hide boosts whenever energy > reserve; run-finish needs no other remembered enemy within 150 m and < RUN_KILLS_MAX kills (counted from `kill` events). FIRE_POLICY: act() post-filter via _may_fire on the last _attack target (return fire within FIRE_MEMORY 10 s only while exposed; else only a one-shot kill: HP <= laser damage or a gun magazine, alone, under kill cap). test_brain 26 OK. Rebuilt r_run, r_run_end with FIRE_POLICY on.

- 2026-11-22: Critic fixes (notes/reviews/plateau-2026-11-22.md): RUN_HIDE_S 30 "run-wait" (stay at the LOS-break spot, quiet, after the last sighting), boost only toward cover (walk to far point), farming off within RUN_HIDE_S of a sighting, DROP_SEEN_S gate. Trees: world.py has no canopy model, so find_cover is buildings-only; needs a world canopy LOS + survival option (not done). BURN_LEAD 45 => hidden from 370 s. test_brain 24 OK. Rebuilt r_run, r_run_end.

- 2026-11-22: plateau.md P1/P2. RUN_MODE (step 1d: cornered fight, finish lone < RUN_FINISH of max HP, else _hide with fallback _far_point = 12 points at 0.6 x next radius farthest from tracked+remembered enemies, boost only above RUN_ENERGY 40). DROP_SAFE_R gate via perception.danger. Plating late: already first in economy.ORDER, no economy edit. 23 tests OK. Variants r_run, r_run_end.

- 2026-11-22: REGEN_HIDE (step 1c, needs REGEN_BREAK) and BURN_QUIET (in 1b) via new _exposed (world.los from 5 nearest hunter eyes; map-free: any visible) and _hide (boost to find_cover while exposed, gun-only if engaged; quiet walk, no fire once hidden). Specs: notes/research/online-squad-survival.md R3/R6, notes/reviews/squad-survival-2026-11-22.md. `python -m unittest python.tests.test_brain`: 21 tests OK. Variants sim/versions/b_regen_hide, b_burn_quiet. Next: A/B vs b_regen / b_burn (regen cycles, HP at 415 s).

- 2026-11-22: added _track_shots/_push_window (peek + reload push, also a "push" branch before evade), rear-hit aim override in act(), burn step 1b (t >= sum(zone hold+shrink) - BURN_LEAD), regen gate on step 3 (regen_delay from config). 5 tests in TestMoves; test_brain: 19 tests OK, act mean 0.18 ms. Variants built via sim/variant.py. Next: A/B results.

- 2026-11-21, iteration 0: journal created. Next: start the current task.
