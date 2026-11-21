# Review: `notes/ideas/game-plan.md` (survival first)

Critic, iteration 1, 2026-11-21. Method: `ponytail:ponytail-review`. Checked against `protocol.md`, `notes/research/{config,zone,upgrades,map,stream}.md`, `hello.json` values via `config.md`, `notes/interfaces.md` (World budgets), `breakdown.md` §13 (example bot), `objective.md`. One extra check of the recorded stream (command in finding 1).

**What the plan does:** it hides until the endgame. It walks to the nearest point inside each next circle, never starts fights, flees otherwise, takes a nearby laser, and picks upgrades by a fixed list. In the last circle it stands on the final center, because the zone at radius 0 (415 s, 260 HP/s) decides 1st place before the 8:00 HP tiebreak. M1 is the 7-row table in §9.

**What is right (checked, no change needed):** the zone timeline and the 415 s close (`zone.md` table), the proof that a point inside the next circle stays inside through the shrink (§9 + `zone.md` L40), that the burn decides the end (`2980 / 260 = 11.5 s`, 415 + 11.5 < 480), regen rules (§7 Health, and dealing damage resets the timer, `stream.md` L58), the rear arc ×1.5 (§7), laser/gun/lightning/mortar DPS (§7, `upgrades.md` L50), sound ranges (§8), drop timing, ring and value (§7, `config.md` `drops.repair` 1), upgrade effects (`upgrades.md`), and the worst-case walk per phase (fits each hold even at a 1.3 path factor, `zone.md` L35). E1 is correct: we shot first. Our first `hit` on mech 10 was at t = 5.7, 144 m away, and it was a **rear** hit. Mech 10's aim (2.2 rad) pointed about 68° away from us, outside its 120° view wedge, so it had not seen us. Its first damage to us came at 7.9. Not shooting would most likely have kept us hidden.

Severity: **high** = loses many points or breaks the bot; **medium**; **low**.

---

## High

### 1. The M1 fight-back rule repeats the E1 fight (§4 "M1 simplification", §1 "engaged")
- **What it says:** fight back when engaged and `hp_frac ≥ 0.5`, there is exactly one threat, and `e.hp ≤ self.hp`. "Engaged" also includes "a visible `aimed_at_me` enemy within its weapon range".
- **Problem:** the rule ignores weapons. In E1 both mechs had 1400 HP, so `e.hp ≤ self.hp` holds. Mech 10 had gun + laser and we had only the gun, and the plan's own numbers say we lose that trade (fact 4: laser 131 DPS hitscan against gun 102 at a 0.5 hit rate at 150 m, `stream.md` L54: laser hits alone did 1260 of our 1400). The `aimed_at_me` trigger is also bad: an enemy whose torso swings across us (15° cone, any range up to 280 m) counts as engaged, so we fire first at someone who may not have seen us. That is how E1 started.
- **Fix:** in M1, fire only when (a) **cornered** (rule 2), or (b) damaged by `e` in the last 3 s **and** `e` holds no laser unless we hold one too **and** `e.hp ≤ 0.8 × self.hp`. `aimed_at_me` or `charging` alone means hide, never shoot. Keep "never start a fight".
- **If we skip it:** every spawn next to a laser holder plays out like E1: dead by about 40 s, about 3 points.

### 2. The M1 disengage does not break line of sight, so it does not escape a laser (§4 F3 step 1 "M1 without world", §9 row 2)
- **What it says:** without the world model, move straight away from the threat and sideways, inside the zone.
- **Problem:** the laser is hitscan (§7), so moving sideways dodges nothing. Walking away from 150 m to 200 m (vision range) takes 4.3 s at 11.7 m/s. After that the enemy keeps tracking our real position for 5 s (`vision.memory_s`, §8), and we are still inside 280 m laser range (11.7 × 5 = 58 m more puts us at about 258 m). That is about 9 s exposed, 3 to 4 full shots at 2.4 s per cycle: 945–1260 HP, which is E1 again. `python/world.py` already exists with `los` (≤ 0.3 ms, `interfaces.md`), so M1 does not have to go without the map.
- **Fix:** M1 F3 uses `world.los`. Test the 8 compass directions at 15 m and 30 m (16 points). Take the nearest point, inside the zone, where `los(enemy_eye, p + [0,0,4.5])` and `los(enemy_eye, p + [0,0,9])` are both false. Boost to it when the threat holds a laser or `charging` is true. Only when no point qualifies, move straight away while boosting. Keep the torso on the threat (the plan already says so).
- **If we skip it:** the main M1 rule (+1.5 to +3 claimed) saves us only from gun-only enemies.

### 3. Holding at the edge leaves our back open to the mechs still arriving (§2 Phase C "anyone behind us is outside the zone and burning", §8 aim rule 5, Z2)
- **What it says:** hold just inside the next circle's edge, face `next_center`, so everyone is in front of us.
- **Problem:** during the **hold** part of each phase (60, 45, 35, 30, 25, 15 s: more than half the match), the ring between the next circle and the current circle is inside the zone and takes no damage (§9: the circle holds still before `shrink_start`). Mechs walking to `next_center` from our side of the map (the example bot does exactly that, `breakdown.md` §13) cross the edge right where Z2 puts us, because Z2 takes the point on the line from us to the center. They come from behind, where we can't see them (120° wedge). They see us from up to 200 m and hit our rear for ×1.5 (`mech.rear_mult`): a laser does 472 instead of 315. The claim "behind us is burning" holds only once the shrinking edge has passed us.
- **Fix:** before the shrinking edge reaches us, aim rule 5 faces **outward** (away from `next_center`), sweeping ±60°: that is where unseen traffic comes from. Inside the circle, mechs heading to the center pass within 45 m only if they pass us, and proximity sensors see all around. Switch to facing inward when `dist(pos, c(t)) > r(t) − 30` (the live edge is within 30 m). M2's V1 cover map should prefer hold cells with a building wall directly on the outward side.
- **If we skip it:** most first contacts start with a hit in the back while we hold still. The objective's rear-hit target (≤ 20%) is unlikely to hold. The size of the loss is a guess, and the sim should measure it first (see "Estimates" below).

---

## Medium

### 4. The Z2 formula puts us on the wrong side of the center in phase 6 (Z2, §2 Phase C)
- **Problem:** `min(|pos − next_center|, next_radius − margin)` with `next_radius = 0` gives −10.5 m: a point 10.5 m past the center. At 1 m/s of shrink that leaves the circle about 10 s early, about 2700 HP of burn at 260 HP/s, so we die first among the finalists. Row 7 overrides it in phase 6, but a builder who applies Z2 every phase hits this.
- **Fix:** `max(0, next_radius − margin)`, plus one unit test with `next_radius = 0`.

### 5. The plan is unclear on what `obs.zone` means during a shrink (Z1 "interpolated during a shrink", §0 open questions)
- **Problem:** §9 says `zone` "always gives the current circle". If `center/radius` already move tick by tick during a shrink, interpolating them again shrinks the circle twice (too cautious, and it pushes us toward the center brawl). If they don't move, the bot must interpolate. Also unconfirmed: when `next_*` updates (assumed at `shrink_end`, `zone.md` L36).
- **Fix:** use `self.in_zone` as the truth for "inside now". Interpolate only from values saved at `shrink_start` (`center`, `radius`, `next_*`). The Tester checks both questions in the first sim or real run and logs `zone` once per second.

### 6. The cover search can blow the time budget (§4 F3 step 1, rule 2 and 3 "cover point reachable")
- **Problem:** "a reachable point within 40 m ... `los` false for center and top for every known threat". Without a cap: 16 points × 3 threats × 2 rays = 96 `los` calls × 0.3 ms = 29 ms. That is over the 15 ms mean and near the 35 ms p99 (`objective.md` guardrails), and rules 2, 3 and F3 each search.
- **Fix:** one shared `find_cover(threats)` capped at 32 `los` calls (about 10 ms). Run it when a threat appears and reuse the result for 1 s unless a threat moves more than 10 m. The Tester times it on the stream.

### 7. No rule for an attacker we can't see (§4 F3, §8 rule 2)
- **Problem:** F3 needs the enemy's eye position, but a `damaged` event gives only a `bearing` (§6), and the shooter may be outside our wedge or behind canopy. This happens in most fights: E1's first laser hit came as a `damaged` event.
- **Fix:** for an unseen attacker, place a virtual threat along `bearing` at 150 m (laser) or 100 m (gun, mortar), eye at ground + 8 m. Turn toward it (rule 2) and run the cover search against it. For mortar damage the bearing points at the blast, not the shooter (§7 rear armor): move 20 m sideways, don't aim there.

### 8. M1 nav has no stuck rule, and the hold point can land inside a building (§9 "walk straight, slide along walls, jump when stuck")
- **Problem:** 22.8% of the map is building footprint (`map.md` L60), and 59 prisms have holes (courtyards). Straight-line walking toward a hold point behind a concave building gets stuck. From phase 3 on, 60+ HP/s outside gives 23 s of life (`zone.md` table). The plan claims the example bot loses points this way, but gives our own fallback no numbers.
- **Fix:** snap `hold_point` to the nearest cell where `world.blocked` is false, stepping toward `next_center`. Stuck = under 3 m of progress in 2 s while moving: jump, then jet toward the goal. 244 of 250 roofs are within one tank (`map.md` L34). The towers at (−460, −50) and (−467, −225) are not. Grid A* is the nav builder's call, but these two numbers belong in the plan.

### 9. The score estimates are guesses (§3, §4, §5, §9 "Why M1 should beat 6.00")
- **Problem:** the M1 model (20% early deaths / 40% mid / 40% top 5 → 9.0) has no source. The row deltas (+3.1 to +7.1 in total) overlap (rows 2, 3 and 6 are one behavior) and can't be added. The +0.5 to +1.5 for Z1 assumes example bots die to the zone, which nothing shows: E1 died to a laser. The hit rates in §1, rear-hit ≤ 10% (EG1), "+50% gun hits at 10 cubes" (G1) and "200 paired matches for 0.5" (§10) are guesses too. With unpaired SD 4.5, 200 matches give an SE of 0.45, not a significant 0.5.
- **Fix:** label them as guesses. The sim measures these first, in this order: (1) death-time histogram and cause (zone vs weapon) for M1 against 15 example bots **and** against the laser-competent variant; (2) A/B of fight-back rule 1 (old vs fixed); (3) rear-hit share and time-to-first-damage with inward vs outward hold facing (finding 3); (4) zone-death share. Then the first real submission of M1 is the measurement that counts (48 matches, ±0.7).

---

## Low

### 10. Three versions of Z1 (Z1 text)
The deadline formula multiplies `eta` (already × 1.3) by 1.3 again. Then comes "simpler M1 form", then `zone.md`'s latest-departure rule. **Fix:** M1 ships only "move to the new hold point as soon as `next_*` changes". Delete the formula from M1. Margin: `radius + 8` (10.5 m) is below `zone.md`'s 15–20 m. Mortar knock is 16 m/s (§7). Use `radius + 12` until the sim shows edge exits.

### 11. "Two threats more than 180° apart" can't happen (§4 `rear_risk`)
Two bearings are at most 180° apart, and the front arc is 180° (±90°). Aiming at the bisector keeps any two threats in front. Three may not fit. **Fix:** "with two threats, aim at the bisector. Three or more, or a gap over 170°: disengage."

### 12. Range order in fact 4 is wrong
The plan writes "vision > gun". In fact gun 230 > vision 200 (`config.md`). Effect: vision limits every weapon, not range. Fix the text so no one writes a range check that never triggers.

### 13. The laser charge halves speed while retreating (§4 F3 step 2)
"Fire only if in range and engaged" while moving to cover: charging halves move speed (`mech.charge_move_mult` 0.5). **Fix:** while disengaging, gun only. Release or cancel any charge before moving.

### 14. NPC drones and standing still aren't covered in M1
A `damaged` event from `by ≥ 100` is not "engaged", so M1 does nothing when a drone hits it. **Fix:** never shoot NPCs in M1 (gun noise reaches 320 m), keep walking (drone 5 m/s vs our 11.7), and route 50 m wide of visible drones. At the hold point, stand still or move slower than 5 m/s. Steps carry 40 m (§8). The plan says this for F3 only.

---

## Wasted complexity for M1 (cut or defer)

- L1 lightning fallback and the M4 laser + lightning test: defer, since they are rare and untested.
- The Z1 deadline formula (finding 10).
- §1 DPS table, `tri()` and `rear_bonus`: already marked M3. Builders should not build them in M1.
- Keep: U1 (one list, avoids choice 0), the t = 0 spin (1.6 s, free), the laser pickup at `eta ≤ 6 s`. A laser is about a third of floor loot (`loot.weights` 1:1:1), but with about 13 floor lasers on 770k m², the chance of one within 70 m at spawn is about 25% (estimate). So expect the row 4 gain to be small in M1.

## Gaps that happen every match (and where they are covered)

| Situation | Covered? |
|---|---|
| Spawn outside the next circle | yes: Z1 moves at once. The worst gap of 360 m takes 31 s (40 s with the path factor) of a 60 s hold |
| Shot while walking to the edge | partly: F3 needs findings 2 and 7 |
| Unseen attacker | no: finding 7 |
| Stuck on a building | no: finding 8 |
| Mechs arriving behind the hold point | no: finding 3 |
| Final-center crowding: bodies pushed apart, 2.5–3.75 m off center = 650–975 HP of extra burn | named (EG2 "get there first"), not solved. M1 is fine. M4 needs the shooting rule to settle it |
| Drone aggro on the route | no: finding 14 |

## Comparison with online research

`notes/research/online-recommendations.md` did not exist when this review was written (only `config, hello, map, stream, upgrades, zone` in `notes/research/`). A second pass comes later.

---

## Verdict

**Ready for M1 builders with listed fixes.** Fix 1, 2 and 3 (high) and 4, 6 and 8 (medium, cheap) in the plan before the Survival, Brain and Nav builders start. 5 and 7 can be decided by the builders with the rules given here. 9 sets the Tester's first measurements. The rule facts are sound. The errors are in the M1 shortcuts, which were written as if `world.py` did not exist and leave out enemy weapons.

Not checked: whether `fire: [true, true]` fires gun and laser together, whether plating heals, `in_zone` details (open with the Researcher). Built-in track bot behavior: one recorded match is all the evidence, and the plan's edge-hold depends on it.
