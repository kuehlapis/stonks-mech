# Alternative whole-match strategies

Author: Strategist, iteration 1 (2026-11-21). Status: proposal. The baseline to beat is the **edge-hold plan** in `notes/ideas/game-plan.md` (the GP rules: Z1–Z3, F1–F3, L1, U1, S1, EG1–EG5). The Critic is reviewing that file now; this one does not change it.

Facts used (sources: `protocol.md` §, `notes/research/*.md`):
- **F-burn:** the circle reaches radius 0 at 415 s, then everyone takes 260 HP/s. **HP at 415 s decides 1st** (`zone.md`). Max HP comes from cubes (×1.4 at `cubes.stat_cap` 10) and `plating` (×1.15 per stack, 3 stacks) (`upgrades.md`).
- **F-walk:** walking (`mech.walk_speed` 11.7) always outruns the zone edge (at most 7.2 m/s, `zone.md`). But every mech walks at the same speed, so running never gains distance on a chaser. Only boost does, for 5.9 s per tank.
- **F-laser:** a gun alone loses to gun + laser in the open at about 150 m (4 × 315 laser hits, `stream.md`). The laser is hitscan out to 280 m, beyond `vision.range` 200.
- **F-roofs:** 244 of 250 roofs can be reached with one jet tank (`map.md`).
- **F-cover:** buildings cover 22.8% of the map. The **north-east campus core** (x −100…555, y 30…389) is the densest cover. The **west** (parking, stadium) and **south-east** (the Oval) are open (`map.md`).
- **F-sensors:** proximity sensing (`vision.near_range` 45 m) sees in every direction through anything except buildings, canopy included. Beyond 45 m you are seen only inside the 120° wedge and without a building or dense crown in between (§8).
- **F-time:** observations can arrive seconds apart (a 6.4 s gap in the recording, `stream.md`). Every timer (regen, memory, capture, zone deadline) uses `obs.t`, never a count of ticks.
- **F-regen:** dealing damage also resets the regen timer (`stream.md`).
- **F-rear:** a rear hit does ×`mech.rear_mult` (1.5), confirmed in the stream (67.5 = 45 × 1.5).

Module letters: **W** World, **N** Navigation, **P** Perception, **C** Combat, **E** Economy, **S** Survival, **B** Brain.

Expected scores are reasoned guesses for a fully built version of each style against track-like opponents. Their main value is the ranking. The sim must replace them (the noise per submission is ±0.7, `objective.md`).

---

## 1. Pacifist hider / runner

**Idea:** never shoot a mech. Survive by not being seen, and if seen, by breaking line of sight. Reach the top 3, or the 415 s collapse.

Core rules:
1. Zone: GP Z1/Z2 (inside the next circle before `shrink_start`, nearest edge point).
2. **Hide spot:** inside the next circle minus `margin`, choose the cell with the lowest exposure. Exposure = the share of 16 rays at 100 m with line of sight to our center (offline cover map, GP V1). Prefer NE-core cells when the circle includes them. Prefer cells with a building within 10 m, which halves the directions an enemy can come from inside 45 m.
3. **Silence:** move at `|move| ≤ 0.4` (4.7 m/s < `sound.step_speed` 5) whenever no zone deadline is pressing. Never boost or jet except to escape. Never fire, which also keeps the regen timer running (F-regen).
4. **Seen → break line of sight:** if a mech is visible and either `aimed_at_me`, or within 45 m (its sensors see us too): walk at full speed to the nearest point where `world.los(enemy_eye, our center and top)` is false. Keep moving out of sight for `vision.memory_s` (5 s) after that, then go silent.
5. **Laser charge aimed at us:** if cover is ≤ 1 s away, take it now. Otherwise sidestep perpendicular to its aim (this only helps if it has to re-aim). Accept the hit.
6. **Roof refuge:** if an enemy is inside 45 m on the ground, no ground cover breaks its line of sight, and a reachable roof edge is within 15 m: jet up and step back from the edge. From below, the roof edge blocks the line to us once we are set back about `(roof − enemy eye) × distance / (distance − setback)`; in practice, stand 8 m or more from the edge on the far side. Come down when it has left.
7. **Cornered** (hit in the last 3 s and no cover within 3 s): the only exception, fire back while retreating (GP F1 rule 2).
8. Endgame: GP EG2 (center for the collapse).

Needs: W cover map + `los`; N silent walking, roof climb and descent, cover-point search; P threat tracking, `aimed_at_me`, sound bearings; C only cornered fire; E none (no farming, U1 picks only); S hide-spot choice, F3 regen; B priorities above.

Weaknesses and counters:
- **The 45 m proximity sensors:** in the last two circles (radius 70 and 25) everyone is within 45–140 m of each other. Hiding stops working exactly when it matters.
- **The F-burn tiebreak:** with 0 cubes and no plating we have 1400 HP. Anyone with 3 cubes outlasts us in the burn, so the hider often places **2nd–4th but rarely 1st**.
- Runner math: we can't outrun a laser (hitscan) or a chaser (same speed). Running only works when it breaks line of sight.
- Hunters that walk toward sounds: we make none, so this counter is weak. Mortar lobs at our tracked position within 5 s of losing sight of us: keep moving (rule 4).

Expected mean: **8–10**, win rate **10–20%**. It avoids most early deaths (the main loss in the recording, place 13 at 37 s), but loses the burn to anyone who powered up.

Sim test: 15 example bots, then 5 laser-competent bots + 5 "hunters" (they walk to the last combat sound) + 5 example bots. Metrics: mean place, win rate, share of ticks visible to any enemy (sim ground truth), time of first damage, HP at ≤ 3 alive (target ≥ 60%), place among the burn survivors. Pair with edge-hold on the same seeds.

---

## 2. Camper / ambusher

**Idea:** hold a strong spot that enemies must pass. When one passes with its back to us, open with a full laser shot to the rear, finish it or leave, then move.

Core rules:
1. **Spot:** inside the next circle, within 30 m of its edge (where latecomers enter) or beside a choke on the route between the outer ring and `next_center`: a building corner, a bridge #4 underpass, or a roof edge ≤ 20 m high. The spot needs cover from at least 2 of 4 quadrants (cover map) and a clear line of sight 50–150 m into the most likely approach (the bearing from `next_center` to the current circle's far side, and the bearings of recent `step`/`boost`/`gun` sounds).
2. **Torso:** aimed along the approach; sweep ±50°. Stand still (silent).
3. **Trigger:** a visible mech e with d ≤ 150 m, our bearing from e outside e's front arc (`|e.aim[0] − bearing(e→us)| > front_arc_deg/2`, so a rear hit), e not `aimed_at_me`, and no other threat within 200 m. Then also require either `e.hp ≤ 0.6 × e.max_hp`, or us holding a laser and `e.weapons` containing neither laser nor lightning (rear laser 315 × 1.5 = 472, which leaves e without a counter).
4. **Opening:** start the laser charge as soon as e is in the trigger (`weapons.laser.charge` 0.75 s), release at full charge, then gun. Only the first hit or two land in the rear: e turns toward us at `turn_rate` 4 rad/s, half a turn in under 1 s.
5. **Continue** only while GP F1's fight test holds (`T_kill ≤ 0.6 × T_die`). Otherwise break line of sight (GP F3) and **relocate at least 60 m**: our laser was heard at 380 m (`sound.range.laser`), and e has a bearing from `damaged.bearing`.
6. **Move with the zone:** a new spot each phase (the holds are 45, 35, 30, 25, 15 s). Never camp a spot that fails Z1.
7. No ambushes in the last circle (25 → 0). Switch to EG2.

Needs: W cover map, `los`, roof heights; N route to the spot, short roof climbs; P each enemy's front arc, hp, weapons, approach prediction from sounds; C laser full-charge release, gun lead, rear-arc test; E laser required (L1), U1 with `laser_damage` higher; S relocation after firing; B a "camp" state with a trigger.

Weaknesses and counters:
- **The zone forces a move every 15–45 s.** The best spot rarely survives two phases, and moving between spots is when we get seen.
- The rear bonus is short-lived (about 1 s). A full-HP enemy with a laser turns and trades evenly, so the trigger must stay strict.
- Firing reveals us to everyone within 380 m: third parties arrive (the vulture beats the camper).
- Proximity sensors: anyone passing within 45 m sees us first, whatever the cover except buildings, so the spot must keep the approach lane 50 m+ away.
- Bots that don't move (other campers) never pass.

Expected mean: **8.5–10.5**, win rate **15–25%**. Same survival as edge-hold, plus cubes from kills (theirs + `cubes.death_drop_extra` 2) that help the burn. Downside: each ambush risks a fight.

Sim test: opponent pool with movers (example bots walking to the center) and a few laser-competent ones. Metrics: ambushes started, the share of opening hits that were rear (`hit.rear`), the win rate of ambushes, deaths within 20 s after an ambush, cubes at 300 s, mean place and win rate against edge-hold on paired seeds.

---

## 3. Third-party vulture

**Idea:** let others fight. Go toward fights, not away, stop at the edge of laser range behind cover, and finish the weakened winner.

Core rules:
1. **Detect fights:** two or more combat sounds (`gun`, `laser`, `lightning`, `explosion`) within 3 s from bearings within ±15° of each other, `dist` "mid" or "near". Or visible beams, or two visible mechs aiming at each other.
2. **Approach** to a cover spot 120–200 m from the fight (beyond `vision.range` of mechs facing each other, inside our `weapons.laser.range` 280). Only if the route stays inside the next circle, with `hp_frac ≥ 0.7` and no third threat seen.
3. **Wait** for a `death` sound from that bearing, or a visible fighter at `hp_frac ≤ 0.3`.
4. **Strike** when `T_kill ≤ 2.5 s` (GP F2): the weakened mech is usually at 20–40% HP with its regen timer reset, and it is busy facing the other fighter (often a rear angle for us). Laser first.
5. **Loot** the drop (cubes + weapons) only if no other mech is visible within 150 m of it. Then leave 60 m+ and regen.
6. Abort when a third mech arrives first (two vultures), or when the winner turns to us at full charge.

Needs: P sound clustering, fight detection, hp tracking for unseen mechs (last seen hp); C laser at 150–250 m on a target that is moving, gun lead; N cover approach; E loot pickup; S regen afterwards; B a vulture state.

Weaknesses and counters:
- It goes toward danger: other vultures, and bots that shoot the nearest mech (the example bot) once we are seen.
- Sound gives only a 7° bearing (σ) and a 3-band distance, so the position estimate is rough.
- Finishing the winner doesn't change our place (F: deaths by anyone count equally). Its value is only the loot and one fewer burn rival.
- Few fights to find late in a match, where most of the score is decided.

Expected mean: **8–10**, win rate **20–30%** (more cubes for the burn than the pure hider). It works best as an add-on mode, not a whole-match style.

Sim test: 15 example bots (they fight a lot). Metrics: strikes made, kills per strike, damage taken per strike, cubes at 300 s, mean place and win rate compared with the pure hider on paired seeds.

---

## 4. Roof sniper (laser)

**Idea:** get a laser, climb a mid-height roof inside the next circle, and shoot from 200–280 m, beyond most enemies' vision.

Core rules:
1. Requires a laser (L1). Without one by t = 90 s, fall back to edge-hold.
2. **Roof choice:** a roof inside the next circle minus `margin`, 10–40 m high (one jet tank with spare energy, `mech.jet_drain` 15/s), with lines of sight over the open areas (west and south-east are good targets, F-cover), and no taller roof within 280 m that has line of sight to it.
3. Stand 5–8 m back from the edge facing the open area. The edge blocks low shots from close-in ground mechs.
4. Shoot only targets at d > `vision.range` + 20 (220–280 m) that are not facing us, or targets fighting someone else. One full charge per target, then re-check: if `damaged` from a sniper or mortar, drop off the far side of the roof (break line of sight) and pick another roof at least 80 m away.
5. Leave the roof at Z1 time. In phases 5–6 no roofs (the circle is too small); go to EG2.

Needs: W roof list (prism tops, reachable heights, `map.md`), line of sight from roofs, a precomputed sniper-roof table; N jet climbs, roof landing and drop-off; P long-range tracking; C laser release, 250 m lead not needed (hitscan) but aim `pitch` needed; E laser, `laser_damage`; S roof exit before deadlines; B sniper state.

Weaknesses and counters:
- **Other lasers** reach 280 m too, and a roof mech is visible from far (its eye and body are high, `map.md` says roofs are exposed).
- **Mortars** lob onto roofs, and concussion (`knock` 16 m/s) can throw us off.
- Damage taken gives the victim our bearing (`damaged.bearing`). The laser beam is visible to anyone who sees either end, so each shot advertises us.
- Climbing empties energy (no boost to escape for about 6 s).
- The zone forces us off every 30–45 s, and late circles may contain no good roof.
- Kills at range don't score places by themselves (only loot, which we can't collect from a roof).

Expected mean: **7–9**. Strong mid-game damage, poor survival value per risk taken, no endgame plan.

Sim test: needs the sim to model roofs and jets correctly. Opponents: example bots plus laser-competent bots. Metrics: laser hit rate at 200–280 m, damage dealt vs taken per minute on roofs, deaths on roofs, mean place against edge-hold.

---

## 5. Supply-drop chaser

**Idea:** take every supply drop: 3 drops × (`drops.cubes` 3 + full HP), so up to 9 cubes, 3–4 upgrade offers, and three full heals.

Core rules:
1. On each `obs.drops` call: go to a cover spot 30–50 m from it if `eta ≤ lands_in + 20`.
2. Enter when `lands_in == 0`. If a single mech holds the ring and its `hp_frac ≤ 0.5`, attack it from cover (laser). If two or more mechs fight there, wait as the vulture does (§3), then take the drop.
3. Capture (`capture_s` 4 s), then leave and regen.
4. Between drops: edge-hold.

Needs: E drop logic; P counting mechs near the ring; C fights at 30–80 m; N fast routes (boost allowed); S, B as edge-hold.

Weaknesses and counters: every mech sees every drop from the call (§6 `drops`), and the landing sound reaches 600 m, so drops are the most contested spot on the map. Lightning holders (240 DPS within 45 m) dominate the 8 m ring. Drop 1 comes when 13–16 mechs are alive.

Expected mean: **6–8**, high variance. Each capture is worth a lot, but each contested one is often a death. Better as the GP S1 rule (only uncontested drops) than as a style.

Sim test: metrics: drops captured, deaths within 15 s of a ring, cubes at 240 s, mean place against edge-hold with S1.

---

## 6. Farmer, then turtle

**Idea:** power up early and quietly on crates and NPC drones (36 crates × 1 cube, 12 drones × 2 cubes per match), reach 6–10 cubes and 2–3 plating by t ≈ 230 s, then play the pacifist hider until EG2. It aims straight at F-burn: the most HP at 415 s.

Core rules:
1. **Phase A–B (0–230 s): farm.** Targets: crates (`crates.hp` 300 = one full laser shot) and drones (350 HP, shoot from 60–90 m, GP G3). Take a target when: no threat in the last 10 s (by `obs.t`), the target is inside the next circle, `eta ≤ 15 s`, and `hp_frac ≥ 0.7` (drones only). Prefer targets in the NE core (cover next to the noise). After each kill, move 40 m before the next target (the crate sound reaches 220 m, the laser 380 m).
2. **Weapon:** a laser first (one shot per crate, fewer noisy shots), else the gun.
3. **Cubes:** up to `cubes.stat_cap` 10; beyond that only to reach a threshold (GP G1). U1 order: plating first.
4. **Drops:** GP S1 (uncontested only). Drop 3 at 235 s is the last top-up.
5. **From t = 230 s or 10 cubes: turtle.** Pacifist hider rules (§1), with full HP by 375 s (GP EG3), then EG2.
6. Abort farming at any threat: GP F3.

Needs: P crate and NPC tracking, threat timer by `obs.t`; C crate shots (aim at `pos.z + crates.height/2`), NPC kiting; E target choice, cube count, U1; N routes inside the circle; S/B hide mode after the switch.

Weaknesses and counters:
- Noise: every crate and drone fight is heard at 220–380 m. A laser bot that comes to the sound catches us mid-farm.
- Size: at 10 cubes we are 1.5× bigger (`cubes.size_per_cube`), easier to hit and to see over cover (worse hiding in the turtle phase).
- Drones shoot back (25 DPS) and chase up to 60 m from home.
- Crates may be on roofs or outside the circle; supply varies per match.

Expected mean: **9–11**, win rate **25–40%**. It is the only style that both survives early and wins the burn. The risk is the noise during farming.

Sim test: the sim must spawn crates and drones per the config. Metrics: cubes and plating stacks at 230 s and at 375 s, deaths while farming, HP at 415 s against the other survivors, win rate, mean place against the hider and edge-hold on paired seeds.

---

## 7. Adaptive (switch style by state)

**Idea:** one bot whose Brain picks the style each tick from the state. Each style above becomes a mode.

Mode table (first match wins):

| Condition | Mode |
|---|---|
| Z1 deadline pressing (`eta × 1.3 + 5 ≥ shrink_start − obs.t`) | **Move** (zone) |
| engaged and cornered | **Fight back** (GP F1 rule 2) |
| engaged, not cornered, or `hp_frac < 0.5` | **Disengage + regen** (GP F3) |
| `next_radius == 0` (phase 6) | **Collapse** (EG2: center, burn targeting) |
| `obs.t ≥ 265` or `obs.alive ≤ 5` | **Turtle** (hider §1 + back to the wall EG1, full HP by 375 s) |
| uncontested drop under S1 | **Drop** |
| a fight detected, `hp_frac ≥ 0.7`, holding a laser | **Vulture** (§3) |
| ambush trigger met (§2 rule 3) | **Ambush** (opening shot, then F1 test) |
| `obs.t < 230`, `cubes < 10`, quiet for 10 s, target available | **Farm** (§6) |
| otherwise | **Hide** at the edge-hold spot (GP Z2 + cover map) |

Weapon-based switches (from `mechs[].weapons` and sounds):
- An enemy with a laser seen at > 45 m and we have no laser: break line of sight now (F-laser).
- An enemy with lightning within 60 m: keep it beyond `weapons.lightning.range` + 10 m. Don't charge our laser near it (`short_s` 2 s).
- An enemy holding a mortar: our laser does ×1.6 (`cookoff`). A good ambush or vulture target.

Needs: everything above, but each mode is small and reuses the same modules. B is the only extra: a priority table, plus hysteresis (stay in a mode at least 2 s by `obs.t`) to avoid flapping.

Weaknesses: the most code and the most thresholds to tune; mode flapping; harder to test. It needs the single styles to exist first.

Expected mean: **10.5–13**, win rate **35–55%** once tuned. This is the only plan that reaches the objective (≥ 12, ≥ 50% wins), because winning needs both early survival (hide) and burn HP (farm, drops, plating).

Sim test: ablate one mode at a time against the full adaptive bot, 200 paired matches per ablation; the opponent pool includes copies of the adaptive bot itself (mirror matches), since rival teams' track bots will converge on similar ideas.

---

## 8. Against copies, and the metric a review judges

The track field includes other teams' AI-designed bots. Assume they read the same protocol and find the same ideas: edge-holding, early lasers, plating first, hiding, rushing the final center. A style that only works while others brawl loses value as the field gets smarter, so prefer styles that stay good when copied. Each style also gets **one primary metric with a pass line**, so the after-action review (`CLAUDE.md`) can judge it as went right or went wrong without arguing.

| Strategy | In a field of copies or counters | Primary review metric (pass line) |
|---|---|---|
| Edge-hold (GP) | 8 bots on one circle's edge are 2π·R/8 apart: 55 m at R = 70, inside the 45 m sensors by R = 25. All of them face inward, so the whole circle is in everyone's front arc: no free rear hits for anyone, and the last circles turn into face-to-face trades decided by HP and weapons. **Neutral when copied**: it costs nothing but stops being an edge. | alive at t = 265 s in ≥ 70% of matches; median first-damage time ≥ 120 s |
| 1 Pacifist hider | If many hide, few die early, and 8–10 mechs reach the last circles. Hiders all sit at 1400 HP with no cubes and lose the burn to anyone who farmed; hiders who burn on the same tick share a place (§4). **Degrades badly when copied**: its edge came from others dying, and copies stop dying. | deaths before 265 s ≤ 20%; share of ticks visible to an enemy before 265 s ≤ 10% |
| 2 Camper/ambusher | Campers don't pass campers, so the only movers are mechs on zone moves, and every camper fires at the same moments (phase changes). Bots that expect campers hug walls and clear corners with their 45 m sensors, which see a camper before it gets its rear angle. **Weak when copied or expected.** | ambushes won ≥ 70%; deaths within 20 s after an ambush ≤ 10%; net cubes per ambush ≥ 1 |
| 3 Vulture | A field of patient bots has fewer brawls to feed on, and several vultures arrive at the same fight and meet each other. **Weak when copied.** | kills per strike ≥ 0.6; HP lost per strike ≤ 20% of max |
| 4 Roof sniper | Sniper roofs see each other: laser duels at 280 m, and mortars lob onto roofs. **Weak when copied.** | damage dealt ÷ taken while on roofs ≥ 2 |
| 5 Drop chaser | Every bot sees every drop. More chasers means more fights in an 8 m ring. **Worst when copied.** | captures per attempt ≥ 0.7; deaths within 15 s of entering a ring ≤ 5% |
| 6 Farmer → turtle | Loot is limited: 36 crates + 12 drones ≈ 60 cubes for 16 mechs, so copies take the near loot first. But **HP at 415 s is the one test no bot can avoid** (F-burn): the smarter and more patient the field, the more matches reach the burn, and the more the farmer's extra HP decides 1st. **Gets better when the field hides.** | median cubes at 230 s ≥ 6; deaths while farming ≤ 10%; most HP among survivors at 415 s in ≥ 50% of matches where we reach 415 s |
| 7 Adaptive | It re-reads the field each tick: it hides when the field brawls and farms when the field hides, and its endgame rests on burn HP. **The most robust when copied**, if its mode table is tuned against mirror fields as well as example bots. | mean place and win rate against pool (d) below; each mode is judged by its own row above |

The final-center rush (GP EG2) when copied: everyone arrives at the 25 → 0 circle at once. Mechs push apart, lightning (240 DPS within 45 m) dominates, and the center goes to whoever has the HP to stand there. So EG2 only pays off with an HP lead, which again points to the farmer's HP (and to lightning as an endgame weapon, GP L1 M4 test).

Add a fourth sim opponent pool: **(d) mirror field**: 4 edge-holders, 4 hiders, 4 farmers, 3 adaptive copies of our previous best. A candidate that wins on pools (a)–(b) but loses on (d) is likely to fall on the track as rival teams improve.

## 9. Comparison

Edge-hold row: `game-plan.md` M1–M4 as staged (M1 alone about 8–9).

| Strategy | Expected mean (built) | Win rate | Build cost | Main counter | When copied | Fits objective? |
|---|---|---|---|---|---|---|
| Edge-hold (GP baseline) | 9–11 at M4 | 25–45% | medium | late-circle contact, burn HP | neutral | close |
| 1 Pacifist hider/runner | 8–10 | 10–20% | **low** (subset of GP M1–M2) | 45 m sensors late, burn HP | degrades badly | no (few wins) |
| 2 Camper/ambusher | 8.5–10.5 | 15–25% | medium | zone forces moves, third parties | weak | no alone |
| 3 Vulture | 8–10 | 20–30% | medium | other vultures, rough sound positions | weak | no alone |
| 4 Roof sniper | 7–9 | 10–20% | high (jets, roof geometry) | other lasers, mortars, beam reveals us | weak | no |
| 5 Drop chaser | 6–8 | 10–25% | low | everyone sees drops | worst | no |
| 6 Farmer → turtle | 9–11 | 25–40% | medium | noise while farming | **improves** | close |
| 7 Adaptive | **10.5–13** | **35–55%** | high (needs 1, 2, 3, 6 as modes) | tuning, flapping | **most robust** | **yes** |

## 10. Recommendation

**Build these three first as A/B candidates against edge-hold** (ordered by robustness to copies, then cost):
1. **Farmer → turtle (§6).** The style that stays good when copied (§8): it attacks the burn-HP test that every match ends with. It tests whether cubes and plating bought early with noise win more burns than they cost in early deaths (review metric in §8).
2. **Pacifist hider (§1).** Cheapest: edge-hold minus fight-back, plus silence and the cover map. Weak when copied, but it measures the base fact every other style relies on: does hiding work (ticks seen, time of first damage)? It also becomes the turtle half of §6 and of the adaptive bot, so nothing built for it is wasted.
3. **Camper/ambusher as an add-on to edge-hold (§2 rules 3–5 only).** Tests whether rear first strikes (`hit.rear`) gain cubes without raising deaths. Keep it only if it passes on pool (d), where bots expect it.

Skip as styles: roof sniper (high cost, low survival value) and drop chaser (keep GP S1 instead). Keep the vulture as a later mode.

**The best final bot is an adaptive mix (§7)**, not one style, because it is the one that holds up when copied: hide early and when hurt, farm when quiet, ambush or vulture only under strict triggers, turtle from 265 s, and own the center at the collapse. A single style either survives without winning the burn (hider) or fights its way into early deaths (sniper, drop chaser). Each A/B above decides which modes earn a place in the mix, and in what order.

How to run the A/Bs: 100 paired-seed matches each for a first read (detects Δ ≥ 1 in mean place), 200 to confirm Δ ≈ 0.5. Opponent pools: (a) 15 example bots; (b) 5 laser-competent + 5 hunters + 5 example bots; (c) later, copies of our previous best. (d) the mirror field of §8. A candidate must win on pools (a), (b) and (d). Metrics: mean place, win rate, zone deaths (0%), ticks outside the zone (≤ 2%), rear-hit share (≤ 20%), HP at ≤ 3 alive (≥ 60%), drops captured when uncontested (≥ 80%), plus each style's own metric above.
