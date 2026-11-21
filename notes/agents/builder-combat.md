# Builder: combat: journal

Owns: `python/combat.py` and `python/tests/test_combat.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

2026-11-22 brief: mortar arc aiming behind `economy.TAKE_MORTAR` (off by default); A/B variant `sim/versions/c_mortar`. Done, awaiting sim result.

Previous: Iteration 1 brief (M1 rows 3-4): `Combat.attack` (gun lead, firing discipline, laser charge/release, reload) and `Combat.face`, per `notes/interfaces.md`. Done: `python/combat.py`, `python/tests/test_combat.py`.

## Plan

1. Gun intercept with lead from target velocity.
2. Mortar ballistic pitch for a given range.
3. Laser charge and release timing.
4. Lightning cone check.
5. Reload when safe.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No lead, laser never released | Low hit rate loses fights | Gun intercept first | done (iter 1, miss <= 0.07 m in tests) |
| Lead ignores our own velocity, aim slew time and obs age | Misses on fast strafes or when obs arrive late; check `hit` events per shot in the sim | Extrapolate target by obs age; confirm in sim whether bullets inherit shooter vel | open |
| Mortar arc, lightning cone | Mortar A/B | Arc solver done (2026-11-22); next: sim A/B c_mortar, then lob at sound/last-seen targets behind walls | in progress |
| High arc needs >= ~150 m (max_pitch 1.3) | Lobbing over walls only works at long range | Accept; or step back to lob | open |
| Mortar error tol is a fixed 3 m, ignores turn rate | May fire late or skip snap shots | Tune from sim hit/splash events | open |
| Laser start ignores whether target is about to break los | A charge started then lost auto-fires after hold_s, wasted | Only start when target is >= N m from cover edge (needs world) | open |
| Aim tolerance 0.6 x radius untested in the real game | Too tight = few shots, too loose = misses | Tune from sim hit rate | open |

## Lessons

- The laser can't be cancelled (protocol §7: any release fires, at min_charge at least; full charge auto-fires after hold_s). So `face()` always releases; Brain should call `face()` only when it accepts losing the shot.
- Real laser weapon dicts are not in `check/stream.jsonl.gz` (we never held one); tests build one from `cfg.weapons.laser`.

## Log (newest first)

- 2026-11-22: mortar. `combat.arc_pitch` (closed form, low/high), `Combat._mortar` (lead by flight time x3, tube at pos.z+height+0.5 with r0 offset x2, aims at target feet, pitch limits). Fires when err x range <= 3 m, cooldown <= dt, dist >= 12 m; takes the torso from the gun only when cooldown <= 0.5 s. `economy.TAKE_MORTAR=False` adds mortar last in WANT. No brain edit: brain already routes all slots through `attack()`. Tests: `python -m unittest python.tests.test_combat python.tests.test_economy` -> 26 OK; landings < 3 m at 40/100/180 m low arc, 180 m high arc; 1000 attack calls < 1 s. Variant: `sim/versions/c_mortar`.

- 2026-11-21, iteration 1: built `python/combat.py` (intercept solves |d + v t| = r0 + s t with r0 = radius + 0.5, muzzle at pos.z + muzzle_height, target center pos.z + height/2 x size; gun fires when lead aim within max(0.004, atan(0.6 r / dist)) of actual aim, in range (bullet travel <= range), cooldown <= decide interval, ammo > 0, los; laser starts when los and dist <= range, holds until charge >= stats.charge, aim on and los, aim direct while charging; reload when empty, or ammo <= 50% mag and target out of range; `face()` also reloads at <= 50% mag). Evidence: `python -m unittest python.tests.test_combat -v` → 9 OK on 3.13 and 3.12; miss distances [0.008, 0.046, 0.027, 0.064, 0.028] m; attack+face 0.03 ms (fake world, real `los` adds up to 0.3 ms). Extras beyond interface: `face()` returns `reload`; optional `target["size"]` (default 1). Next: tune tolerance and lead from sim hit rate.

- 2026-11-21, iteration 0: journal created. Next: start the current task.
