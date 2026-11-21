# Review: `git diff 5bc9b89 65bd2fe -- python/` (RUN_MODE, hide, funnel, zone lean, mortar), 2026-11-22

Critic, ponytail-review. Read the diff plus `_decide` (`brain.py` at 65bd2fe, lines ~166-345) and `perception.danger`. Load assumed: one bot, a 50 ms tick budget.

What this change does: it adds flag-gated behaviors, all off by default. RUN_MODE (on contact: hide from hunters, run to the far side of the next circle, then wait quietly for 30 s), REGEN_HIDE and BURN_QUIET (both reuse `_hide`), drop-safety gates, a funnel cover pick and a zone-lean hold point in survival, and mortar aiming in combat. With the flags off, the bot changes only in strafe boost (now ground-only) and the hold-search switch.

## Must fix

1. **Run-wait hides exactly where the squad is heading** (`brain.py` 1d, `run-wait`)
   - What: after breaking LOS, we stand still at `_run_spot` for 30 s.
   - Problem: squad hunters walk to our last known position plus 3 s of our velocity (`squad.py:127`). Our hide cell is a few metres from that point, so they walk round the corner into us at under 45 m. Near-range sight sees through everything except buildings. Then we fight at close range anyway, under 40% of the time with a covered back. This is the "holding in the open" failure in another form.
   - Fix: once hidden, walk quietly (< 5 m/s) away from the last sighting, behind the building. A target such as `_far_point` or a cover cell ≥ 40 m from the last sighting, then hold. That is a few lines: in run-wait, use `self._far_point(obs, dg)` (or `find_cover` from `dg`) instead of `self._run_spot`.
   - If we skip it: P1's survival gain is mostly lost in the sim; on the track it depends on whether the hunters search.

2. **Stale `_run_spot` can send us across the map** (`brain.py` `_hide` sets it, run-wait reads it)
   - What: `_run_spot` is only ever overwritten, never cleared.
   - Problem: if the latest sighting happened while another branch ran (zone-urgent, burn, a fight), run-wait walks back to a spot from minutes ago. That spot may be outside the next circle and through the squad.
   - Fix: store `(t, spot)` and use it only if `t - spot_t < RUN_HIDE_S`, otherwise `pos`. One line.
   - If we skip it: occasional long walks into the crowd. Rare, but each one costs a lot.

3. **Run-wait blocks non-urgent zone travel for 30 s after every sighting** (step 1d runs before step 5 `travel`)
   - Problem: with shared vision, sightings keep coming, so we move to the zone only once `zone_urgent` fires. Then step 1 boosts us in late, in the open, at the time hunters converge. That breaks "regen in zone before 375 s" (plateau fix 5a).
   - Fix: in run-wait, if `zg` exists (zone travel wanted), return the `travel` action with `quiet=True` instead of holding. Two lines.
   - If we skip it: late, loud zone arrivals and lost regen at the burn.

## Should fix

4. **No cover means walking across open ground at 11.7 m/s under fire** (`_hide` while exposed)
   - What: boost is allowed only when `cover` exists. Without cover we walk to `_far_point`.
   - Problem: the open is where hard and expert bots hit almost every shot. Walking is the slowest way out.
   - Fix: `boost = obs["self"].get("energy", 0) > reserve` whether or not cover exists. Plateau fix 1 meant "spend boost on breaking LOS", and getting out of the open is that.
5. **`run-finish` starts a fight that adds a hunter** (`len(visible) == 1`)
   - Problem: "one visible" is not "alone". The squad shares vision and others may be 50 m behind a building. Each kill also raises the hunter count (`n = 1 + dead`).
   - Fix: also require `not self._call(P, "danger", t, pos, 150)` beyond that one id, and that it is the first or second kill only (P4's cap). Leave RUN_FINISH as is otherwise.
6. **No test for run-wait's zone or stale-spot cases.** `test_brain.py` adds 134 lines but nothing covers "run-wait while zone travel is wanted" or "old `_run_spot`". Add one test each for findings 2 and 3.

## Nice to have

7. The `farm = None if RUN_MODE ...` gate (step 6) is reached only when the foe is virtual. With no foe, run-wait returns first in the same 30 s window. It is not wrong, but the gate mostly duplicates run-wait.

## Checked, fine

- Crash paths:
  - `_hide`'s `min(hunters)`: always non-empty (`hs = hunters or [foe]`, and foe is non-virtual).
  - `_far_point`: always has at least one point; `next_center` and `next_radius` being None is handled.
  - `danger` returns dicts with `pos`.
  - `arc_pitch` guards `dx ≈ 0` and a negative discriminant.
  - `cos(pitch)` is never 0, because atan < π/2.
  - `max_hp` is in the obs mechs (`protocol.md:158`), so the `run-finish` 1e9 fallback is never used.
- Timing:
  - `_hide` runs ≤ 5 los calls per tick in `_exposed` (not cached). `find_cover` and the funnel share one `LOS_CAP` = 40, cached 1 s, and are skipped when `_slow()`.
  - Worst case on a fresh search is ≈ 45 los calls ≈ 13.5 ms at the 0.3 ms cap; typical ≈ 2 ms. No path to > 50 ms found.
  - `HOLD_SEARCH` off removes the known 50-62 ms path.
- Zone: urgent zone travel (step 1) still runs before RUN_MODE, so run-wait can't stall us outside the circle once the zone is urgent. Only the non-urgent margin is lost (finding 3).
- Funnel: the normal test matches find_cover. `seen ≤ 2` gate; it falls back to the shadow-side search.
- ZONE_LEAN uses only mechs visible now, and only moves the hold-point direction. It does not conflict, because P3 is not built.
- Mortar: the 12 m minimum keeps our 7 m splash off us. It only takes the torso when the mortar is ≤ 0.5 s from ready.
- Strafe boost is now ground-only (`grounded` is in obs, `protocol.md:147`). With the flags off this is a behavior change, but a correct one: boost in the air is a jet.

Verdict: fix 1, 2 and 3 first (all in run-wait, ~10 lines), then 4.
Not checked: the unit tests' contents beyond their size, and the mortar/gun torso hand-off in real sims.
