# Game plan: survival first

Author: Strategist, iteration 1 (2026-11-21). Status: revised after the Critic's review (`notes/reviews/game-plan.md`); see "Changes after review" at the end.

**All score deltas in this plan are reasoned guesses, not measurements** (review #9). They rank the work. They don't add up (several rows describe one behavior). The sim and the first M1 submission replace them; §10 lists the measurement order.
Sources: `protocol.md` (§ numbers below), `notes/research/config.md` (config verified: no value differs from protocol.md), `notes/research/zone.md` (phase table, worst-case gaps, latest safe departure), `notes/research/upgrades.md` (stacked values, plating first), `notes/research/map.md` (22.8% of the map is building footprint; 1,524 of 1,560 trees have crowns below 9 m, so canopy can hide a mech; bridge #4 is the only underpass), and the recorded match in `check/stream.jsonl.gz` (evidence E1 below).
Every number is a default; code reads it from `hello.config` (base) or `obs.self.stats` / `obs.self.weapons[i].stats` (after upgrades). Config paths are in `code` style.

## 0. What the score rewards (the facts the plan is built on)

1. **Place is death order** (§4). Our place is `obs.alive` at the moment we die. Anyone dying, killed by anyone, moves us up the same amount. Kills give nothing except loot (cubes `cubes.death_drop_extra` + theirs, weapons). So we never fight to score; we fight only to stay alive or to get loot that keeps us alive later.
2. **The 8:00 HP tiebreak almost never applies. The final zone burn decides.** The zone reaches radius 0 at Σ(`hold_s` + `shrink_s`) over `zone.phases` = 415 s, and then everyone stands outside at 260 HP/s (`zone.phases[-1].dps`). The most HP a mech can have is about 1400 × 1.4 (10 cubes) × 1.15³ (3× plating) ≈ 2980, which lasts 11.5 s. 415 + 11.5 < 480 (`match.duration_s`). So the last mechs die in the burn, in order of **HP when they leave the circle** and **how long they stay inside**. Armor does not reduce zone damage (§7 Health). Code check: `burn_decides = t_close + max_hp_seen / last_dps < duration_s`. If it is false (a config change), switch to the HP tiebreak at `match.duration_s`.
3. **Early fights kill.** E1: in the recorded match, our mech (gun only, the example bot) shot first at mech 10 (gun + laser) about 145 m away at t = 5.7 s. Mech 10's laser hit for 315 at t = 7.9, 10.6, 19.3 and 35.9 s, and its gun hit often. We died at about t = 37 s and placed 13th. Three mechs were already dead by t = 27 s. (Reproduce: print the `events` of each obs in the stream.)
4. **Laser beats gun at range.** Laser: 315 hitscan per full shot, up to 280 m, 315 / (0.75 + 1.65) = 131 DPS, no lead needed. Gun: about 102–107 DPS sustained (45 × 12 per mag cycle; `zone.md`/`upgrades.md` count 11 intervals and get 107) at 100% hits, and it has to lead targets and lose hits to spread. Range order: laser (`weapons.laser.range` 280) > gun (`weapons.gun.range` 230) > vision (`vision.range` 200). Vision, not weapon range, limits what anyone can aim at, except a laser or mortar fired at a remembered or heard position.
5. **Being inside the next circle is safe through the whole shrink.** The next circle lies inside the current one, and center and radius move linearly, so any point inside the next circle stays inside every in-between circle. (Proof: |p − c(s)| ≤ r₁ + (1 − s)|c₁ − c₀| ≤ r₁ + (1 − s)(r₀ − r₁) = r(s).) So the zone rule is just: **be inside `zone.next_center/next_radius` minus a margin before `zone.shrink_start`.**
6. **Firing is loud.** Gun is heard at 320 m, laser 380 m, crate break 220 m, mortar 420 m (`sound.range`). Walking above `sound.step_speed` (5 m/s) is heard only at 40 m, boosting at 90 m. A hider who does not shoot is nearly invisible beyond 45 m (`vision.near_range`) when out of an enemy's 120° view wedge or behind a building.

### Zone timeline (defaults, computed from `zone.phases`)

| Phase | Hold (circle still) | Shrink | Radius after | dps | Supply drop called / lands |
|---|---|---|---|---|---|
| 1 | 0–60 | 60–110 | 560 → 380 | 20 | 70 / 95 |
| 2 | 110–155 | 155–195 | 380 → 240 | 35 | 140 / 165 |
| 3 | 195–230 | 230–265 | 240 → 140 | 60 | 210 / 235 |
| 4 | 265–295 | 295–325 | 140 → 70 | 100 | |
| 5 | 325–350 | 350–375 | 70 → 25 | 160 | |
| 6 | 375–390 | 390–415 | 25 → 0 | 260 | |

Researcher to confirm (open): when `zone.next_*` updates (assumed at the previous `shrink_end`; `zone.md` makes the same assumption, the stream only covers phase 1), whether `in_zone` uses feet-center distance ≤ radius, and whether dps stays 260 after 415 s.

---

## 1. Shared definitions (used by every rule)

| Name | Definition |
|---|---|
| `hp_frac` | `self.hp / self.max_hp` |
| `margin` | `self.stats.radius + 12` m (14.5 m at 0 cubes; scales with cube size, §10). It keeps a full body inside the circle against drift and a mortar knock (`weapons.mortar.knock` 16 m/s). Lower it only if the sim shows no edge exits. |
| `eta(p)` | path length to p / `self.stats.walk_speed`. Before nav gives path lengths: straight distance × 1.3. |
| `hold_point` | §2, rule Z2 |
| threat | a visible or remembered (`vision.memory_s`) mech, or a combat sound (`gun`, `laser`, `laser_charge`, `lightning`, `mortar`, `explosion`) with `age` ≤ 3 s and `dist` "near" or "mid" |
| `aimed_at_me(e)` | the angle between `e.aim[0]` and the bearing from e to us is ≤ 15°, and e has line of sight to us (`world.los` eye to our center) |
| engaged | we took a `damaged` event with `by` a mech id (0–15) in the last 3 s (by `obs.t`). **Nothing else counts.** |
| threatened | a visible enemy is `aimed_at_me`, or `charging: true` and `aimed_at_me`. It means **hide (F3), never shoot** (review #1: E1 began with us shooting a mech that had not seen us). |
| `unseen_attacker` | a `damaged` event whose `by` is not in `obs.mechs`. Treat it as a virtual threat on the line along `bearing`: 150 m away for `weapon` laser, 100 m for gun, eye at `world.ground + 8`. For `weapon` mortar the bearing points at the blast, not the shooter (§7): step 20 m sideways and don't aim along it. |
| `t_close` | Σ(`hold_s` + `shrink_s`) over `zone.phases` (415 s) |

DPS table (per weapon, from config; multiply by `1 + cubes.damage_per_cube × min(cubes, cubes.stat_cap)` and by `1 − target armor`):

| Weapon | Sustained DPS formula | Default | Effective range |
|---|---|---|---|
| gun | `damage × mag / (mag × cooldown + reload)` | 102 | `range` 230, hit rate falls with distance |
| laser | `damage / (charge + cooldown)` | 131 | `range` 280, hitscan |
| lightning | `damage / cooldown`, until energy runs out (`energy / (energy_cost / cooldown)` s) | 240 for 8.3 s | `range` 45, `cone_deg` 30 |
| mortar | `(damage or splash) / cooldown` | 62–77 | to about `speed² / gravity` = 235 m, arcs over walls |
| npc | `npc.damage / npc.cooldown` | 25 | `npc.aggro_range` 45 |

Hit-rate assumptions until the sim measures them: gun 0.8 at < 50 m, 0.5 at 50–150 m, 0.25 at 150–230 m; laser 0.9 within range with line of sight; lightning 1.0 within range and cone; mortar 0.3. For enemies, assume the same (competent) rates. This is deliberately pessimistic about them.

---

## 2. Phase plan

### Phase A: spawn to the first supply drop (0–70 s)

- **Goal:** take no damage, pick up a laser if one is close, reach the hold point inside the first next circle (380 m) quietly.
- **Where:** the `hold_point` (Z2), on the side of the next circle we already stand on. Not the center. Everyone else (the example bot, and probably most built-in bots) walks to `next_center` (`breakdown.md` §13), so the center is where the brawl is.
- **Do:**
  - t = 0: spin the torso 360° once (`turn_rate` 4 rad/s gives about 1.6 s) to see pickups, crates and mechs within 200 m, then aim along the walking direction, swinging ±50° to scan.
  - Take a **laser** pickup if `eta` ≤ 6 s and no mech is seen within 120 m of it (L1).
  - Walk (no boost) to the hold point. Stay inside the current circle.
- **Avoid:** shooting (gun noise reaches 320 m: E1 shows a 145 m opener losing to a laser), long-range duels, open fields when a building edge is near, the next center, mortar pickups (L1), boosting (90 m noise, drains the energy we need to flee).

### Phase B: mid game (70–265 s, circles 380 → 240 → 140, drops 1–3)

- **Goal:** grow without fights we might lose: reach 3–6 cubes, keep HP high, capture uncontested drops, move with the zone early.
- **Where:** the hold point of each new next circle (Z2), next to a building wall or under dense canopy (M2 cover map, V1). Move to the new hold point as soon as the new next circle appears (`zone.next_*` changes).
- **Do:**
  - Break crates and farm NPC drones only when quiet (G2, G3).
  - Contest supply drops only under rule S1.
  - Regen to full after any fight (F3): `mech.regen_per_s` 45 HP/s after `regen_delay` 5 s.
  - Watch fights from cover and finish a weak survivor only under F2 (M3).
- **Avoid:** crossing the middle of the circle, the ring of a contested drop, standing still in open ground in view of a road, fights with two or more enemies, taking zone damage after phase 2 (dps 60+ and no regen outside).

### Phase C: the last three circles (t ≥ 265 s, circles 70 → 25 → 0)

- **Goal:** enter each circle before rivals with full HP, keep every enemy in front, and own the center for the final collapse.
- **Where:** "back to the wall": just inside the next circle's edge (distance `next_radius − margin` from `next_center`), facing `next_center`. From the edge, the whole circle lies inside our 180° front arc (`mech.front_arc_deg`), so no one inside can hit our rear (`mech.rear_mult` 1.5). This holds only once the shrinking edge has passed us. During a hold the outer ring is safe ground and mechs still arrive through it from behind, so facing follows Z4.
- **Do:**
  - Be at full HP before t = 375 s (phase 6 hold). Disengage and regen (F3) whenever that is possible inside the circle.
  - Phase 6 (next_radius = 0): move to `next_center` during the hold (at most 25 + 25 = 50 m, 4.3 s walking). In the last 10 s before `t_close`, stand on the exact center. Each meter off center leaves the circle about 1 s early (radius shrinks 25 m in 25 s), and 1 s = 260 HP.
  - The final burn: EG2.
- **Avoid:** being the only mech in the open between two others; turning the torso away from the nearest enemy to loot; fighting in the last 10 s when we already have more HP than every visible rival.

---

## 3. Zone rules

- **Z1 Move with the zone (M1, one rule).** Start moving to the new hold point the moment `zone.next_*` changes. If `self.in_zone` is false, the top goal is to walk toward `next_center` (boost if `zone.dps × eta > 0.2 × self.hp`). `self.in_zone` is the truth for "inside now". Never re-interpolate `obs.zone.center/radius`: they may already move during a shrink. Where a live circle is needed (Z4), interpolate only from the `center`, `radius` and `next_*` saved at `shrink_start` (review #5). The Tester logs `zone` once per second in the first run to settle both points. F3 escapes may leave the circle only in phases 1–2 (zone dps ≤ 35) and for ≤ 5 s. `notes/research/zone.md`'s latest-safe-departure rule is an M2 option if leaving early proves to cause encounters. With defaults the worst-case walk fits in the hold time of every phase: worst move = 2 × (R_n − R_next) − margin = 265, 200, 140, 90, 50 m for phases 2–6, which is 23, 17, 12, 8, 4 s against holds of 45, 35, 30, 25, 15 s.
- **Z2 Hold point (M1).** `hold_point = next_center + unit(pos − next_center) × min(|pos − next_center|, max(0, next_radius − margin))`. The `max(0, …)` stops the point from passing the center when `next_radius ≤ margin` (phase 6: radius 0 would otherwise put us 14.5 m past the center, about 3800 HP of extra burn; unit-test it with `next_radius = 0`). Then snap it: if `world.blocked(hold_point, radius, height)` is true, step 2 m at a time toward `next_center` until it is false (at most 30 steps, then use `next_center`). It is the nearest point of the next circle on our side, never deeper than needed. Shortest walk (fewer encounters), away from the center brawl, and from the edge all of the circle is in front of us. Check (from config): the worst move to the following circle, 2 × (next_radius − following_radius) − margin, must be ≤ 0.6 × following `hold_s` × walk_speed. If it is not, pull the hold point in toward the center until it is.
  M2 refinement: search within 40 m of that point, inside the circle, for the lowest exposure score (V1).
- **Z4 Hold facing (M1; review #3).** At the hold point, while the live edge is more than 30 m behind us (`dist(pos, c(t)) ≤ r(t) − 30`, with c(t), r(t) from Z1), aim rule 5 faces **outward** (away from `next_center`), sweeping ±60°. Reason: during the hold the outer ring is safe ground, and the mechs that will pass us are the ones walking in from it toward the center (the example bot does exactly that). Mechs already inside heading to the center are moving away from us, and any that come within 45 m are seen by our proximity sensors whatever our facing. Once the live edge is within 30 m (a shrink is passing us, or phase ≥ 4 when the circle is small), face **inward**: now everything behind us is outside and burning. I chose facing over "back against a wall" for M1 because it needs no cover search; M2's V1 adds the wall by preferring hold cells with a building directly on the outward side, which then lets us face inward all the time.
- **Z3 Never fight outside (M1).** In phase ≥ 3, the zone beats every other goal except "laser aimed at me with cover ≤ 1 s away".

- **N1 Stuck rule (M1; review #8).** Stuck = less than 3 m of progress toward the current goal in 2 s (by `obs.t`) while commanding a move. Then: (1) jump and jet toward the goal (`boost` in the air) if energy ≥ 40 — 244 of 250 roofs are within one tank (`map.md`), so this climbs most walls; (2) if still stuck 2 s later, walk 10 m along the wall to the side that is closer to the goal direction (try left, then right), then resume. Never target the dorm towers at (−460, −50) and (−467, −225) or the two chimneys (`map.md`: out of jet reach). Grid A* is the Nav builder's choice; this rule is the floor that must exist anyway. Measure: stuck events per match and ticks outside the zone (target ≤ 2%).

Expected effect (guess): **+0.5 to +1.5** mean score. The example bot heads for `next_center` but has no map, so it slides along walls (`breakdown.md` §13); a stuck mech can die to the zone. No zone death has been observed yet (E1 died to a laser), so the low end is more likely. Zone deaths drop to 0% (objective proxy). Measure: zone-death share and ticks outside the zone, over 100+ sim matches, with and without Z1 (Z1 off = walk to `next_center` like the example bot).

---

## 4. Fight-or-flee rule

Evaluated every decision tick against each visible or remembered enemy e. Inputs: `self.hp`, `self.max_hp`, `e.hp`, `e.max_hp` (shown while `vision.show_enemy_hp`), distance d, `self.weapons`, `e.weapons`, `self.cubes`, `e.cubes`, the number of other threats, rear exposure, zone position.

```
my_dps(e)    = Σ over my usable weapons w:  dps(w) × hit(w, d) × cube_mult(self.cubes) × tri(w, e) × rear_bonus(e)
their_dps(e) = Σ over e.weapons w:          dps(w) × hit(w, d) × cube_mult(e.cubes) × tri(w, me) × rear_risk(e) × (1 − self.stats.armor)
T_kill = e.hp / my_dps(e)
T_die  = self.hp / Σ their_dps over every threat with line of sight and range to us
```

- `tri(w, target)`: our laser against a mortar holder ×(1 + `weapons.laser.cookoff`) = 1.6. Our laser against a lightning holder within its `range` + 10 m: 0 (it will be shorted, `short_s` 2 s). Their laser against us when we hold a mortar: ×1.6. Mortar against a lightning holder: lightning DPS ×0.5 (concussion keeps it away and drains energy). Otherwise 1.
- `rear_bonus(e)` = 1.5 when our bearing from e is outside e's front arc (e is facing away). `rear_risk(e)` = 1.5 when the bearing to e is more than 90° from our torso aim and turning there (angle / `turn_rate`) takes longer than 0.5 s; otherwise 1. With two threats, aim at the bisector of their bearings: two bearings are at most 180° apart, so both stay in the 180° front arc. With three or more threats, or two whose gap is over 170° (no slack to turn), disengage.
- `hit(w, d)`: the assumptions in §1 until measured.

**Decision (first match wins):**

1. **Zone first.** If the fight would hold us outside the next circle past `shrink_start − eta(hold_point) − 5`, or outside the current circle in phase ≥ 3: disengage toward the hold point.
2. **Cornered:** engaged, and no cover point (below) reachable within min(3 s, 0.3 × T_die). Fight: aim at e, fire everything in range, move along a wall or toward the nearest cover. Never turn the back to run (legs and torso are independent, §6 `move` vs `aim`).
3. **Laser about to hit:** a visible e is `charging` and `aimed_at_me`, and a cover point is ≤ 1 s away: step behind it now (a full charge is 315).
4. **Fight** (M1: only when engaged; M3: also when we choose it) if all of these hold:
   - `T_kill ≤ 0.6 × T_die` (the margin covers model error and a third party arriving),
   - no other threat within 200 m (M1), or the other threats' DPS is in T_die (M3),
   - `hp_frac ≥ 0.4`,
   - in phase A, not at all unless engaged.
5. **Otherwise disengage (F3).**

**M1 simplification** (before Perception has DPS estimates; review #1). Never start a fight. Threatened (`aimed_at_me` or charging) means hide, never shoot. Fire only when:
- (a) **cornered**: engaged, and `find_cover` (F3) returns nothing; or
- (b) engaged by e in the last 3 s, AND (`'laser' not in e.weapons` OR we hold a laser), AND `e.hp ≤ 0.8 × self.hp`, AND `hp_frac ≥ 0.5`, AND e is the only threat, AND we don't hold a laser while e holds lightning within `weapons.lightning.range` + 10 m (lightning beats laser).
Everything else: disengage (F3). In E1 (gun only against gun + laser) this rule hides instead of trading.

**NPC drones in M1 (review #14).** Never shoot drones in M1 (gun noise reaches 320 m). A `damaged` event with `by ≥ 100` is not engaged: keep walking (drones move at `npc.speed` 5 m/s, we walk at 11.7), and route 50 m wide of visible drones (`npc.aggro_range` 45).

**F2 Vulture (M3).** Two other mechs are fighting each other (their `aim` points at each other, or `beams` or `hit` events between them), and one of them has `hp_frac ≤ 0.3` and `T_kill ≤ 2.5 s` from our position with cover next to us: shoot it, take its drops (its cubes + 2, its weapons) only if the other fighter is dead, gone, or below 0.3 too. Otherwise keep watching from cover.

**F3 Disengage and regen (M1 basic, M2 with the world model).**
1. **`find_cover(threats)` (M1; review #2, #6).** One shared function, used by F1 rules 2–3 and F3. Candidates: the 8 compass directions at 15 m and 30 m (16 points), nearest first, skipping points that are outside the zone (by Z1's circle) or `world.blocked`. A candidate qualifies when `world.los(threat_eye, p + [0,0,4.5])` and `world.los(threat_eye, p + [0,0,9])` are both false for every threat (visible mechs, remembered mechs, `unseen_attacker` virtual threats). **Cap: 32 `los` calls per search** (about 10 ms at the 0.3 ms budget in `notes/interfaces.md`); stop at the first qualifying point. Run it when a threat appears; reuse the result for 1 s (by `obs.t`) unless a threat moves more than 10 m. If no point qualifies within the cap, return none: the caller treats that as cornered (F1 rule 2), and while not cornered it moves straight away from the strongest threat while boosting. If `world` failed to load, return none (map-free fallback, `CLAUDE.md`).
   Boost to the cover point when the threat holds a laser or is `charging`: the laser is hitscan, so only line of sight saves us (E1: 9 s of exposure walking away = 3–4 shots).
2. Move there with the torso aimed at the strongest threat. While disengaging, fire the **gun only** and only if engaged: charging the laser halves move speed (`mech.charge_move_mult` 0.5), so release or stop any charge before moving (review #13).
3. Once out of sight, keep moving away for `vision.memory_s` (5 s): enemies keep tracking our true position that long (§8), and a mortar can arc over the wall at it.
4. Then walk below `sound.step_speed` (move length ≤ 0.4, about 4.7 m/s) or stand. Don't shoot: dealing damage resets the regen timer.
5. Regen: `mech.regen_delay` (5 s) after the last damage dealt or taken, then `regen_per_s` (45) HP/s. 30% to 100% of 1400 HP takes 5 + 22 = 27 s.
6. Resume the phase plan at `hp_frac ≥ 0.9`, or earlier if Z1 forces a move.

Expected effects:
- **Never start fights, fight back only when cornered (M1): +1.5 to +3.** E1 shows early fights end the match before 40 s. Each early death costs about 13 points (place 13 → 0–3 left of a possible 15). Even a small cut in early deaths is worth a lot. Measure: share of matches where we die before 120 s, and mean place, toggling this rule against "shoot the nearest mech" (example bot behavior).
- **F3 disengage + regen (M2): +0.5 to +1.5.** Every fight we leave alive at 30% HP becomes a full-HP mech again in about 27 s, instead of a weakened mech that the next enemy finishes. Measure: HP at ≤ 3 alive (target ≥ 60% of max), the count of deaths within 30 s after a previous fight.
- **Full DPS model and F2 vulture (M3): +0.5 to +1.** More fights won, loot from kills. Measure: win rate of fights we start (target ≥ 80%), cubes at t = 300 s.

---

## 5. Loot and growth

### L1 Weapon pair: gun + laser

- **Why laser:** hitscan, so it needs no lead and can't be dodged except by cover; 315 per shot (×1.4 at 10 cubes); range 280 m, beyond everyone's vision; one full shot kills a crate (300 HP). It beats mortar (cook-off ×1.6), which is the one weapon that can reach us behind a wall. E1: a gun + laser mech beat our gun-only mech at 100–150 m.
- **Why keep the gun:** neutral against everything, fires while the laser charges and cools down (102 DPS sustained), works when lightning has shorted the laser.
- **Never carry a mortar.** Holding one makes every enemy laser do +60% to us, its splash hurts us, and it needs an arc aim. Loot weights are 1:1:1 (`loot.weights`), so lasers are a third of all floor loot.
- **Lightning: fallback only.** If slot 1 is still empty at t = 60 s and a lightning is within `eta` ≤ 4 s, take it (240 DPS within 45 m, and it shorts lasers). Swap it for a laser when one comes within reach under the L1 conditions.
- **Take rule:** walk to a laser if `eta` ≤ 6 s (phase A) or ≤ 10 s (later), no mech seen or heard "near" within 120 m of it in the last 5 s, and the detour keeps Z1. Send `take` within `loot.pickup_radius`; with both slots full, `drop` the lightning slot. Never swap while engaged: a taken weapon can't fire for `max(loot.equip_s, cooldown)` (1.65 s for a laser).
- **M4 test:** laser + lightning (dropping the gun) for the last two circles, where every rival is within about 50 m. Measure it in the sim before shipping it.

Expected effect: **+0.5 to +1** (wins forced fights, makes M3 fights possible). Measure: mean place with "take laser" against "keep gun only", and the share of matches with a laser by t = 120 s.

### G1 Cube value and the size penalty

- Each cube up to `cubes.stat_cap` (10): +4% max HP (healed) and +4% damage, and upgrade offers at 1, 3, 6, 10 (`cubes.upgrade_thresholds`). At 10 cubes: ×1.4 HP, ×1.4 damage, 4 upgrades.
- Cost: +5% radius and height per cube, no cap (`cubes.size_per_cube`). At 10 cubes we are 1.5× wider and taller: about +50% gun hits at long range, where spread decides, and less at short range; the laser hits anyway. We also see over more cover, but can be seen over more cover too.
- **Rule:** seek cubes up to 10. Above 10, stop seeking them (they add only size) unless one cube reaches the next threshold (15), whose upgrade is worth the +5%. Never avoid a cube we walk over.

### G2 Crates (M2)

Break a crate when all hold: no threat in the last 10 s, the crate is ≤ 60 m off our route, inside the next circle, and ground level (roof crates only if a wall-free jet climb of ≤ 50 m is found by nav). Use one full laser shot if we hold one (one shot, one 380 m sound), else the gun (7 shots, 320 m sound). Wait 1 s for the cube and pickup to appear, collect, move on. Then move about 40 m away: the 220 m crate sound brings visitors.

### G3 NPC drones (M2)

350 HP, 2 cubes, 25 DPS with 2.5° spread at 90 m/s. Farm one when: no threat in the last 10 s, `hp_frac ≥ 0.7`, we hold a laser, and we can shoot from 60–90 m with line of sight (outside `npc.aggro_range` 45, inside `npc.deaggro_range` 90). Laser plus gun kills it in about 2.5 s. If it chases, back away (it moves at `npc.speed` 5 m/s, we walk at 11.7). Skip when another mech is within 200 m: drone fights are loud and the cubes go to the closest mech within `cubes.pickup_radius`.

Expected effect of G1–G3: **+0.3 to +1.** 3–6 cubes by mid game means +12–24% HP and damage and 2–3 upgrades, which counts in every later fight and in the final burn. The cost is noise. Measure: cubes at t = 200 s and t = 300 s, and the change in mean place with farming on against off.

### U1 Upgrade pick order (M1)

Always answer an offer within `bot.offer_timeout_s` (otherwise choice 0 applies). Take the first id from this list that is among `offer.choices`:

`plating > nanites > armor > laser_damage > sensors > laser_charge > servos > gun_damage > gun_rate > gun_mag > gyros > jets > reactor > capacitor > gun_velocity > lightning_efficiency > lightning_range > lightning_chain > mortar_* > laser_pierce`

- `plating` (+15% max HP, 3 stacks): counts against weapons **and** the zone, so it is the final-burn tiebreak (fact 2).
- `nanites` (+60% regen, starts 1.5 s sooner): F3 loops go from 27 s to 17 s.
- `armor` (−8% weapon damage): slightly less than plating, and nothing against the zone.
- `laser_damage` +18% beats `laser_charge` (+8% DPS, but shorter exposure while charging).
- `sensors` (+25 m vision, +15 m proximity, half bearing error): we see first and hide sooner.
- Weapon upgrades for weapons we may drop: lower. Upgrades stay with the mech (§10), so a lightning upgrade still counts if we pick lightning up again.

Expected effect: **+0.1 to +0.3** (small: only 2–4 offers per match). Measure: compare with "always choice 0".

---

## 6. Supply drops

**S1 Contest rule (M2).** Every tick, for each drop in `obs.drops`:

Go (move to a cover point 30–50 m from the drop with line of sight to the ring) when all hold:
- `holder` is null or us,
- `eta(drop) ≤ lands_in + 20 s` and the drop is ≤ 200 m away (don't cross the map),
- going keeps Z1 (drops land inside the circle the zone is closing to (§7), so this usually holds),
- no mech seen within 100 m of the drop in the last 5 s, and no combat sound "near" or "mid" from within ±20° of the drop's bearing in the last 3 s,
- if `hp_frac ≥ 0.9` and `cubes ≥ 10`, only when no mech has been seen in the last 15 s at all (the prize is smaller then).

Enter the ring (`drops.radius` 8) when `lands_in == 0` and the conditions still hold. Stand still in the ring (the clock needs `capture_s` 4 s alone), torso toward the most recent threat bearing, or else sweeping the 120° wedge across the most open side. Leave for cover as soon as the `drop` event arrives.

Abort (back to cover, F3 if engaged) when another mech enters the ring or comes within 60 m, when we are damaged, or when a visible enemy is `charging` and `aimed_at_me`.

Skip outright: drop 1 (95 s, about 13–15 mechs alive) unless it lands within 120 m of us; any drop with `holder` someone else; any drop we can only reach by crossing the circle center.

**Late chance:** an untaken drop stays in `obs.drops`. A drop still untaken 20 s after landing with no recent threat near it is the safest one to take: everyone who wanted it has fought or left.

Value: 3 cubes (`drops.cubes`), full HP (`drops.repair` 1) and full energy. To a hurt mech that is about 1000 HP of regen it doesn't have to wait 27 s for, plus 12% HP and damage, plus 1–2 offers. Drop 3 (lands at 235 s, about 30 s before the endgame) is the most valuable.

Expected effect: **+0.3 to +0.8.** Measure: drops captured when uncontested (target ≥ 80%), deaths within 15 s of entering a ring (target ≈ 0), and mean place with S1 against "skip all drops".

---

## 7. Endgame (t ≥ 265 s)

- **EG1 Back to the wall (M4; M1 has it implicitly via Z2).** Hold at the next circle's edge (`next_radius − margin`) with the torso aimed at `next_center` or at the nearest enemy. Choose the point on the edge farthest from visible enemies, among points with cover from at least one side (M2 cover map). Expected rear-hit share ≤ 10%.
- **EG2 The final burn (M4).** Phase 6: go to `next_center` during the hold. In the last 10 s before `t_close`, hold the exact center (mechs push each other apart, §7, so get there first). After `t_close` everyone burns at 260 HP/s: we win if our HP is the highest. Then:
  - If a visible rival has `hp > self.hp`, shoot it (laser + gun, 233 DPS at short range): every point of its HP we remove counts as much as one of ours.
  - If every visible rival has less HP than us, stop shooting and face them. Shooting only helps when we are behind.
  - `obs.alive` tells us who is left: with `alive == 2` and the rival far behind on HP, just avoid it.
- **EG3 Full HP at 375 s (M2+).** Disengage and regen (F3) whenever it is possible inside the circle between 265 and 375 s. Regen works inside the zone only. Each 100 HP extra at the collapse is about 0.4 s more life in the burn.
- **EG4 The HP tiebreak at 8:00.** Applies only if `burn_decides` is false (fact 2). Then from `match.duration_s − 15` s, stop shooting unless cornered, break line of sight and regen. Survivors rank by HP at the end.
- **EG5 Weak-finish (M4).** In circles 25 and 0, a rival at `hp_frac ≤ 0.25` within laser range and `T_kill ≤ 2 s` is shot even if it isn't engaging us: one fewer mech in the burn, and its cubes (+HP) if they land in reach.

Expected effect: **+1 to +2** at M4, mostly from converting top-3 places into wins. Win rate ≥ 50% needs it: the last 3 mechs are decided by center position and HP, not by aim. Measure: HP at ≤ 3 alive (≥ 60%), win rate among matches where we reach t = 375 s alive, distance to the center at `t_close − 5`.

---

## 8. Aim and facing (cross-cutting, M1)

Torso aim is both the shooting direction and vision (§8). Priority each tick:
1. a visible enemy that is `charging` and `aimed_at_me`,
2. the bearing of the latest `damaged` event (≤ 3 s old),
3. the nearest visible enemy within 200 m,
4. the latest combat sound "near" or "mid" (≤ 3 s old),
5. otherwise: at the hold point, Z4 (outward ±60° while the live edge is > 30 m away, inward once it is within 30 m); while traveling, the walking direction swept ±50°.
With two threats, aim at the bisector (§4).

Expected effect: **+0.3 to +0.8.** Rear hits cost 50% extra (`mech.rear_mult`). Target rear-hit share ≤ 20% (objective proxy). Measure: the rear share of damage taken, from `damaged.rear`.

---

## 9. Staging for the builders

### M1: smallest bot that should beat 6.00 (aim ≥ 7)

| # | Rule | Module | Expected Δ mean score |
|---|---|---|---|
| 1 | Z1 move on announce + Z2 hold point (clamped, snapped off buildings) + N1 stuck rule | Survival + Nav | +0.5 to +1.5 |
| 2 | Never start a fight; M1 fight-back rule with weapons (§4); threatened = hide; F3 with `find_cover` (World `los`, capped at 32 calls) and boost to cover from lasers; ignore drones | Brain + Survival + World | +1.5 to +3 |
| 3 | Aim priority list (§8) with Z4 outward/inward hold facing, bisector for two threats, retreat facing the threat | Combat + Brain | +0.3 to +0.8 |
| 4 | L1 take a nearby laser (eta ≤ 6 s), never a mortar; fire the laser properly (release at full charge) | Economy + Combat | +0.5 to +1 |
| 5 | U1 upgrade priority list | Economy | +0.1 to +0.3 |
| 6 | Walk, don't boost (except Z1 late or F3) | Nav | small, part of row 2 |
| 7 | Phase 6: stand on `next_center` for the collapse | Survival | +0.2 to +0.5 |

M1 uses `python/world.py` for `los` (cover) and `blocked` (hold-point snap). If the world fails to load: walk straight, slide along walls, N1 stuck rule, and `find_cover` returns none (fallback per `CLAUDE.md`). Deferred out of M1 (review, wasted complexity): the L1 lightning fallback, the DPS table / `tri()` / `rear_bonus` (M3), the M4 laser + lightning test.

Row deltas are guesses and overlap (rows 2, 3 and 6 are one behavior); don't add them.

**Why M1 should beat 6.00 (a guess, no source).** Rough model: if M1 dies before 120 s in ≤ 20% of matches (place about 12, 4 points), mid game in 40% (place about 8, 8 points) and reaches the last circle in 40% (top 5, about 12.5 points), the mean is 0.2 × 4 + 0.4 × 8 + 0.4 × 12.5 = 9.0. The example bot style (E1: died at 37 s, 13th) scores about 3–6. Even if this model is too kind by 2 points, M1 still clears 7.

### M2 (≥ 8): safe growth and regen

- F3 disengage with the world model: cover points from `world.los`, the 5 s memory rule, silent movement, regen to 90%.
- V1 cover map: the map is the same every match (§11), so precompute offline an exposure score per 5 m cell (the share of 16 rays at 100 m with line of sight to our center, plus canopy cover) and ship it as a small data file (about 31k cells, under 100 KB). Z2 then picks the lowest-exposure cell within 40 m of the hold point. Zero startup cost. Expected: **+0.5 to +1** (fewer first contacts). Measure: the share of ticks we are visible to an enemy (sim ground truth), and the time of first damage.
- G1–G3 crates, cubes and NPC farming when quiet.
- S1 supply drop rule.
- Sound threat map: avoid bearings with recent combat sounds when choosing routes and hold points.

### M3 (≥ 10): win the fights we take

- The full fight-or-flee model (§4) with measured hit rates, triangle, cubes, rear exposure.
- Gun lead (intercept against `vel`), laser release discipline, lightning cone use.
- F2 vulture finishing.
- Weapon swaps by the triangle (laser against mortar holders; distance > `lightning.range` + 10 from lightning holders).

### M4 (≥ 12, ≥ 50% wins): endgame

- EG1 back to the wall, EG2 final center and burn targeting, EG3 full HP at 375 s, EG5 weak-finish.
- Test laser + lightning for the last circles.
- Tune every threshold in this plan from sim sweeps (one at a time, paired seeds).

---

## 10. How to measure in the local simulator

- **Opponents:** 15 copies of the example bot (the baseline), then mixes with earlier versions of ours. Built-in track bots are of unknown strength: E1's mech 10 used a laser well, so add at least one "laser-competent" opponent variant (releases at full charge, aims straight) to the pool.
- **Paired seeds:** run each A/B pair on the same match seeds, so that spawn and loot luck cancel out. The place spread per match is about ±4.5 (a guess). Unpaired, 200 matches give an SE of 0.45 per arm, too much for a 0.5 change. Pairing should cut it, but by an unknown amount: the Tester measures the paired SD on the first A/B and sets N from it.
- **First measurements, in order (review #9):** (1) death-time histogram and cause (zone vs weapon) for M1 against 15 example bots and against the laser-competent variant; (2) A/B of the M1 fight-back rule, old vs fixed; (3) rear-hit share and time to first damage with Z4 facing vs inward-only facing; (4) zone-death share and N1 stuck events. Then the first real M1 submission (48 matches, ±0.7) is the measurement that counts.
- **Per rule:** toggle one rule off (ablation) against the full current build, and report Δ mean place with its standard error.
- **Proxies per match (log them):** time of death, cause (zone or the weapon that killed us), ticks outside the zone, first-damage time, the share of ticks visible to an enemy, rear share of damage taken, cubes at 200 s and 300 s, laser held by 120 s, drops captured or aborted, HP at ≤ 3 alive, distance to center at `t_close − 5`.
- **Guard against sim bias:** a change that helps only against example bots but hurts against the laser-competent variant is suspect. The track score is the final judge (`objective.md`).

---

## 11. Biggest uncertainties

1. **Built-in bot strength and behavior.** If they hunt (seek out sound sources or hidden mechs) instead of converging on the center, the hold-at-edge rule (Z2) helps less. One recorded match (E1) is all the evidence there is.
2. **Whether hiding works against vision.** The 45 m proximity sensors see through canopy, and a 9 m mech next to low buildings may still be visible. V1 has to be measured.
3. **Zone details** (open with the Researcher): when `next_*` updates, the exact `in_zone` test, and dps after `t_close`.
4. **The hit-rate numbers** in §1 are guesses; M3 must replace them with sim measurements.
5. **Whether we can fire the gun while charging the laser** (`fire: [true, true]`); assumed yes, not confirmed.
6. **Whether plating heals the max HP it adds** (cubes do, §10; plating is not stated).

---

## Changes after review

Review: `notes/reviews/game-plan.md` (Critic, iteration 1). All high and medium findings are fixed; all low findings are fixed.

| # | Sev | Finding | What I did |
|---|---|---|---|
| 1 | high | M1 fight-back ignores weapons; `aimed_at_me` counted as engaged | "engaged" = damaged by a mech in 3 s only; new "threatened" = hide, never shoot; M1 rule (b) needs: no enemy laser unless we hold one, `e.hp ≤ 0.8 × self.hp`, `hp_frac ≥ 0.5`, one threat, no laser-vs-lightning within its range (§1, §4) |
| 2 | high | M1 disengage doesn't break line of sight | `find_cover` with `world.los` on 16 points (15 m, 30 m × 8 directions), center and top rays; boost to it from lasers; straight-away boost only as the fallback (§4 F3 step 1) |
| 3 | high | Edge hold exposes our back to arrivals during holds | New Z4: face outward ±60° while the live edge is > 30 m away, inward once within 30 m. Chose facing over a backed wall spot for M1 (no search needed); V1 in M2 prefers hold cells with a building on the outward side. Phase C text corrected |
| 4 | med | Z2 passes the center at radius 0 | `max(0, next_radius − margin)` + a required unit test (Z2) |
| 5 | med | `obs.zone` during a shrink unclear | Z1 uses `self.in_zone` as truth and interpolates only from values saved at `shrink_start`; Tester logs `zone` per second |
| 6 | med | Cover search can break the time budget | One shared `find_cover`, capped at 32 `los` calls (about 10 ms), cached 1 s unless a threat moves > 10 m |
| 7 | med | No rule for unseen attackers | `unseen_attacker` virtual threat along `bearing` (150 m laser, 100 m gun); mortar: step 20 m sideways (§1) |
| 8 | med | No stuck rule; hold point inside buildings | Z2 snaps off `world.blocked` cells toward the center; new N1 stuck rule (3 m in 2 s → jump + jet, then 10 m along the wall), towers excluded |
| 9 | med | Score estimates are guesses | Labeled as guesses at the top, in §3 and §9; deltas marked non-additive; SE text corrected; measurement order added to §10 |
| 10 | low | Three versions of Z1; double 1.3; margin small | Z1 is one rule (move on announce); deadline formula removed; `margin` = radius + 12 |
| 11 | low | "Two threats > 180° apart" impossible | Replaced by the bisector rule; disengage with 3+ threats or a gap over 170° |
| 12 | low | Range order wrong | Fact 4 now reads laser 280 > gun 230 > vision 200 |
| 13 | low | Laser charge halves retreat speed | Gun only while disengaging; release or stop the charge before moving |
| 14 | low | Drones and standing still in M1 | Never shoot drones in M1, keep walking, route 50 m wide. Silence at the hold point is already in F3 step 4 and applies at the hold point too: stand, or move slower than `sound.step_speed` |

Disagreement: none on substance. On #3, the Critic offered facing outward or a backed spot; I took facing outward for M1 (cheaper) and kept the wall for M2.
