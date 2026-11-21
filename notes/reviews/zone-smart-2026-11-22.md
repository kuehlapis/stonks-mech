# Review: plateau.md "Zone-smart squad" (ZS1-ZS3), 2026-11-22

Critic. Directive: squad bots don't die to the zone. Checked against `hello.config` (`cubes`, `upgrades`, `zone`), `protocol.md` §4, §7, §9, `sim/bots/squad.py` `_hunters`/TIER, and `brain.py` at 56025bb (FIRE_POLICY, `_may_fire`, the reveal/reload post-filter).

## Math check

- Burn HP: plating is ×1.15 per level, multiplicative, max 3 → ×1.521. Cubes add +0.04 each, capped at 10 → ×1.4. So 1400 × 1.521 × 1.4 = **2981 HP → 11.5 s** at 260 HP/s, against 5.4 s for a bare bot. **Correct.**
- Getting 3 plating needs 3 of the first 4 upgrade offers (thresholds 1, 3, 6, 10 cubes) to *contain* plating. Offers are a random choice. Expect ~1–2 plating, so plan for about 2300–2600 HP, not 2980. Nanites (+60% regen, 1.5 s sooner) help only for the refill before 375 s; at the burn there is no regen (outside the zone).
- Zone end: radius 0 at **415 s** (cumulative phases 110/195/265/325/375/415). Correct. At 415 s everyone is outside the zone, so survivors die in order of HP. Correct.
- Score identity: score = mechs dead before us = (our kills) + (drone deaths before us) + (survivors with less HP at the burn). Correct.
- **But**: under the directive, nearly all non-killed squad bots are alive at 415 s, and from 300 s *all* of them hunt us (`HUNT_ALL_T`; the track says "all of them late"). "25% alive at the burn" with 10–14 hunters for 115 s is not supported by anything measured. Our best run so far (RUN_MODE) has its median death well before 300 s. Treat ZS2's +1.5–3 as an upper bound until the zone-smart baseline gives % alive at 300 s.

## Findings, ranked

1. **"Gun-only = easy" is not a safe gate.** Every tier *starts* gun-only (`protocol.md` §7: start with only the gun). Medium, hard and expert carry a laser only after they find one (`squad.py` `wants_laser` and the pickup loop). So before about 150 s most hard and expert bots are also gun-only, and those have lead 0.9–1.0 and aim error about 0.006–0.011 rad.
   - **Fix:** gate by the hunter ladder itself, not by weapons. The hunters are the weakest alive, so a hunter is easy while `squad kills so far + time bonus < 4` (sim). On the track this mapping is a guess.
   - **Better, observable gate:** the target's shots at us miss while we strafe. Track hits ÷ shots heard from that id. With easy bots (no lead) that should be ≈ 0 at 130 m. Abort after 2 hits in 3 s. Combine it with "no `charging` / no laser seen", as planned.
2. **The ladder is self-defeating after kill 2.** `n = 1 + dead (+1 at 150 s, +2 at 240 s)`, taking the weakest first:
   - After 1 kill: easy 2 and easy 3.
   - After 2 kills: easy 3, easy 4, **medium 1**. After 150 s, add medium 2.
   - After 3 kills: easy 4 plus 2–3 mediums (lead 0.6, want a laser).
   So kills 3 and 4 are not "easy bots in groups of 1–3". They are fights against groups that are mostly medium. That fits the doc's own stop rule (stop at the first laser holder or ≥ 4 visible), but then expect **~2 ladder kills, not 3–4**.
   - **Fix:** cap the ladder at 2 kills (`RUN_KILLS_MAX`-style), and end it at 150 s, not 240 s, since at 150 s and 240 s hunters join without any kill.
   - Expected ZS1 score: about 2 kills + baseline ≈ **3, not 4–5**.
3. **Conflict: FIRE_POLICY's post-filter blocks every ladder shot** (`brain.py:137` at 56025bb). `_may_fire` allows only return fire, or a one-mag kill (hp ≤ 45 × 12 = 540, or ≤ 315 with a laser) and `_kills < RUN_KILLS_MAX`. A ladder opener against a 1400 HP easy bot at 130 m fails both, so `fire` is zeroed.
   - **Fix:** have ZS1 set a `self._ladder_id`, and make `_may_fire` return True for it.
4. **Conflict: FIRE_POLICY blocks reloading while exposed** (`brain.py:152`). A ladder fight strafes in the open, so after 12 rounds it can never reload, and it stalls at 2.4 s × ∞.
   - **Fix:** skip that rule when the mode is ladder. One condition.
5. **Order conflict with RUN_MODE.** Step 1d returns `_hide` whenever a non-virtual hunter is tracked. ZS1 must sit before 1d (the doc says "in front of", which is right) and reuse `_fight`. Also, with RUN_MODE, firing marks us as seen (`_revealed_t`) and starts 30 s of run-wait after the ladder kill. That blocks picking up the victim's cubes (+2 each, the point of ZS2).
   - **Fix:** allow the cube step for ~5 s after a ladder kill if `_exposed` is False.
6. **ZS2's cube cap is right, with a nuance.** `stat_cap` 10 caps the HP and damage gain, and size grows +5% per cube with no cap. But cubes past 10 still count toward the upgrade thresholds (15, 21, ...), and plating or nanites from them add HP.
   - **Fix:** cap at 10 *unless* the next threshold is ≤ 2 cubes away, or simpler: keep the cap at 10. The cost is small either way.
7. **ZS3 (drone bait):** agree, low priority. Drones do 25 HP/s and squad bots fire back, so a drone rarely kills a hunter. Don't build it yet.
8. **AIM_PREDICT stacking.** The 0.20 → 0.40 hit rate is against *strafers*. Easy bots don't strafe (`TIER` strafe False), so it adds little to the ladder's early kills, and it helps against the mediums that finding 2 says we should avoid. It doesn't hurt. Just don't credit the ladder's A/B gain to it, and run the A/B with AIM_PREDICT fixed on both arms.

## Needed first

The zone-smart squad (`ZONE_SMART` in `squad.py`) plus a re-run of the baseline. Report % alive at 150, 240, 300 and 415 s, kills before 150 s, and the HP rank at 415 s. Without % alive at 300 s, ZS2 can't be sized.

## Verdict

Build ZS1 with fixes 1–5 (an observable easy gate, cap 2 kills / 150 s, FIRE_POLICY exemptions for the ladder target and for reload, cube pickup after a kill). Expect about +1, not +2–3. ZS2 is flags only, and its effect depends on % alive at 300 s. Drop ZS3 for now. Realistic total ≈ 3–4, still short of 6. The burn is the only path to > 6, and it needs survival past 300 s against the full squad.
