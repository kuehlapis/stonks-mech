# Review: `notes/research/online-squad-survival.md` (rev 2) vs the floor effect, 2026-11-22

Critic. Lens: `squad-sim-2026-11-22.md` finding 1. Score only rises when squad bots die before us, and in the sim they die mostly in the final burn (~395 s median, 19/30 zone). So an idea is worth building only if it moves our death time toward ~400 s or adds kills. Small sample (2 matches); the moderator's calibration runs will confirm.

## Ranked

1. **R6 BURN_QUIET: keep, but fix the rule.** Directly on the lever: HP when the 260 HP/s burn starts (`protocol.md:418`) is the time we outlast the squad. Misread: "don't fire when engaged" only helps if we also stop *taking* hits. Regen needs 5 s with no damage dealt **or taken** (`protocol.md:291`). Under fire, holding fire just loses the trade. Fix: no fire only once LOS is broken (in cover); return fire while still exposed. Measure HP at 415 s and the % still alive at 400 s.
2. **R3 REGEN_HIDE: keep. Second-best lever.** Breaking LOS is the only way regen (45 HP/s) runs against shared vision, and each full cycle is +225 HP per 10 s. Rule facts are right: quiet = ground speed under `step_speed` 5 m/s (`protocol.md:397`). Risk: a slow walk to cover in the open stretches exposure. Use quiet only once in cover; move at full speed to reach it. Measure regen cycles per match and median death_t against `b_regen`.
3. **R1 s_funnel: keep. Already in code, timing is safe.** `survival.py:223` resets `los_calls` once per search, and the funnel (`:277`) and the fallback (`:250`, `:301`) share one `LOS_CAP` = 40 counter. So the funnel plus its fallback is ≤ 40 los calls in total, not 80. That is ≤ 1.6 ms typical and ≤ 12 ms worst case at the 0.3 ms cap, run at most once a second (`CACHE_S`). Within `act()` p99 ≤ 35 ms if nothing else heavy runs on the same tick. Ask the Tester for p99 on the ticks where the search runs. Logic caveats:
   - `world.los` is not the same as vision. Inside `near_range` buildings still block, but outside it the hunter's 30° fov wedge also limits what it sees. Counting LOS over-counts exposure, which is the safe direction.
   - The 5 nearest hunters are not necessarily the ones that will reach us. A flanker 6th-nearest is ignored. That is fine at a 1 s refresh.
   - The +0.5 to +1.5 estimate assumes the hunter count is ≥ 3 while we are alive. Early on there is only 1 hunter (+1 at 150 s in the sim), so the funnel may rarely trigger before ~150 s. Report its trigger rate.
4. **R4 s_zone_lean: split it.** (a) Holding on the side of the next circle away from the hunters is cheap and on the lever, so keep it. (b) The `OUTSIDE_BONUS` for engaging hunters outside the zone is mostly wasted. A trade resets our regen, and a hunter outside the zone dies to the burn anyway (19/30 already do in the sim). That is a squad death we get for free without fighting. Drop (b), or test it only after (a).
5. **R2' CHAIN_PICK: wasted for now.** It only adds kills, and only with lightning, which is rare (our causes in the sims show almost no lightning use). Expected +0.1 to +0.3 is within noise. Build last or drop.

## Rule checks

- Rear ×1.5 outside a 180° front arc (`protocol.md:295`): cited correctly.
- Lightning nearest-target and chain 2 within 14 m, ×0.7 (`protocol.md:306`): correct. 60+42+29 = 131 is right before cubes.
- "Bullets are not stopped by mechs" is unknown from the protocol (`:317`). The research drops body-shield, which is correct.
- Placement = death order (`protocol.md:90`). The zone goes to 0 m, so everyone dies. HP at the burn is time survived, which is what R6 measures.

## Verdict

Build order: R6 (with the fix in 1), R3, R1 (already built, just A/B it), R4a. Drop R4b and R2'. Judge every A/B on death_t (median, % alive at 300/400 s), not on score alone.
