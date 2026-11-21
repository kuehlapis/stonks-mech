# Online research: top 15 recommendations

Researcher (online), iteration 1, 2026-11-21. Built from `online-battle-royale.md` (BR), `online-bot-competitions.md` (BC), `online-game-ai.md` (AI), `online-mech-games.md` (MG). Ranked by expected gain in mean score per unit of effort, toward M1–M4 in `objective.md`.

**How to read the effect estimates.** No one has measured anything yet, so these are reasoned guesses, not data. Baseline: the track best is 6.00 (≈ 10th of 16). We don't know how the built-in bots play. If they behave like the example bot (walk to the zone center, shoot the nearest mech without lead), they'll kill each other at the center, and a bot that avoids them and the zone climbs fast. The effects don't add up linearly; the first three overlap. Real-match noise is ±0.7 at 48 matches (`objective.md`).

**Precondition, not ranked:** guardrails first (never crash, per-tick time cap with `time.perf_counter()`, map-free fallback, stuck detection). StarCraft AI tournaments were lost to crashes and timeouts more than to bad play (BC §10).

| # | What | Module | Effort | Expected effect on mean score | Simulator measure |
|---|---|---|---|---|---|
| 1 | Zone discipline from travel time | Survival + Navigation | M | +2 to +4 (M1) | zone deaths 0%; ticks outside ≤ 2% |
| 2 | Go/no-go fights, disengage and heal | Brain + Survival | M | +1.5 to +3 (M2) | mean place vs example bot; HP at < 3 alive |
| 3 | Local simulator with varied opponents, deterministic A/B | Tester | H | enabler: makes every other row measurable | — |
| 4 | Face the threat (torso twist rules) | Combat + Survival | L | +0.5 to +1.5 | rear-hit share ≤ 20% |
| 5 | Exact gun lead, fire only when aligned | Combat | L–M | +1 to +2, mostly via wins (O3) | hit rate ≥ 40% at 50–150 m |
| 6 | Inner-edge / deadside minimum-risk positioning, silent hold | Survival | M | +1 to +2 | mean place; % of damage taken before t = 230 s |
| 7 | Endgame HP plan for the 6:55 collapse | Brain + Economy | L | +0.5 to +2 (wins) | win rate; HP at 390 s |
| 8 | Dodging: random strafe reversal + visible-projectile dodge | Survival | M | +0.5 to +1 | enemy hit rate on us |
| 9 | Vision: oldest-scanned sweep inside the front-arc limit; sound sectors | Perception | L–M | +0.5 to +1 | surprise-damage events (first hit from untracked id) |
| 10 | Safe economy: loot on the path, kite NPCs, gun + laser | Economy | M | +0.5 to +1 | cubes at 230 s; damage taken while looting |
| 11 | Supply drops only when uncontested; move inside the ring | Economy + Survival | L–M | +0.3 to +1 | captured when uncontested ≥ 80%; deaths near drops |
| 12 | Target choice with anti-thrash; finish low-HP targets | Combat | L | +0.3 to +0.6 | kills per match; shots per kill |
| 13 | Third-party rule: go only after a death sound, target < 50% HP | Brain + Perception | L | +0.3 to +0.8 | mid-game kills without dropping below 50% HP |
| 14 | Triangle weapon use: laser on mortar holders, mortar on campers/drop holders, lightning ≤ 45 m | Combat + Economy | M | +0.3 to +0.8 | damage dealt per damage taken by matchup |
| 15 | Upgrade picks by playstyle | Economy | L | +0.3 to +0.6 | offers answered; mean place by pick set |

## Details

### 1. Zone discipline from travel time (BR §2, §4)
- **Do:** start moving when `path_len / 11.7 × 1.5 + 5 ≥ shrink_start − t` (use `self.stats.walk_speed`; 1.5 is a detour factor to measure). Target a point inside `next_radius − max(10, 0.2 × next_radius)`. Allowed time outside = `0.15 × hp / dps`, and zero once `zone.dps ≥ 100`. Boost when outside and `energy > 35`.
- **Why:** zone deaths are the cheapest places to lose. Pros rotate early, and "leaving late and slow" is the classic loss. `next_center` is given, so there's no guesswork.
- **Effect:** removes every zone death and keeps us inside as the field thins. This alone likely beats 6.00 if built-ins fight each other.

### 2. Go/no-go fights, disengage and heal (BR §1, MG §2)
- **Do:** fight only if ≥ 2 of {HP ≥ 60%, favorable triangle or enemy has only a gun, we have cover or they face away, we're inside the next circle} hold and no third mech is tracked within 160 m. Otherwise turn the legs away, keep the torso on the threat, break LOS, and wait `5 + (max_hp − hp)/45` s.
- **Why:** placement is almost all the points in BR tournaments, and regen (45 HP/s) refills 50% HP in ~21 s once hidden (5 s delay + 15.6 s).
- **Effect:** fewer early deaths; arriving at the endgame with high HP.

### 3. Local simulator with varied opponents (BC §9)
- **Do:** seeded, deterministic matches. Opponents: example bot, a camper, a rusher, a zone-walker that leads its shots. ≥ 100 matches per comparison; report mean place ± CI.
- **Why:** every competition winner I read credits local testing first. reCurse warns that local gains against self-play hid an overfit, and XSquare's biggest mistake was not testing against the meta.
- **Effect:** indirect but large. Without it, 48-match noise (±0.7) hides most single changes.

### 4. Face the threat (MG §1)
- **Do:** keep aim within ±90° of the top threat at all times, legs free. Pre-twist toward the latest damage or weapon-sound bearing. On `damaged.rear`, snap to `bearing`. With two threats, aim at the bisector or back toward a wall.
- **Why:** rear hits do ×1.5; facing turns each rear hit into a front hit, 33% less damage.
- **Effect:** depends on how often built-ins catch us from behind. Easy to build.

### 5. Exact gun lead, fire only when aligned (BC §1–2, AI §3)
- **Do:** quadratic intercept against `vel` with `weapons.gun.speed`. Origin is muzzle + 3 m along the aim; aim at center of mass scaled by cubes; clamp the intercept to walls. Fire only when the *actual* `self.aim` error < `atan(r/d)` + spread. Reload when no target and ammo < 6.
- **Why:** at 100 m a walking target moves 4.6 m during bullet flight, about 2× its radius, so unled shots mostly miss. Linear lead is enough against simple movers.
- **Effect:** turns the fights we choose into wins; needed for ≥ 50% wins.

### 6. Inner-edge / deadside positioning, silent hold (BR §2–3, §6; BC §3, §8)
- **Do:** minimum-risk scoring of 12–24 candidate points: enemies with LOS, being some enemy's nearest mech (×2), inside the next circle at 0.6–0.85 × `next_radius` on the side with the fewest tracked or heard enemies, static cover value, +15% hysteresis. While holding, move at ≤ 0.4 move length (< 5 m/s is silent).
- **Why:** Robocode melee's best movers use minimum-risk; BR pros use the deadside; solos are told to play the edge.
- **Effect:** fewer third-party deaths mid-game. Edge vs center is opinion, so make the radius fraction a parameter and test it.

### 7. Endgame HP plan for the 6:55 collapse (BR §7)
- **Do:** from phase 4 (~295 s), avoid trades that don't kill. Be at full HP by 390 s. Prefer `plating` in offers and fill cubes up to 10. In the last circle stay as central as possible.
- **Why [rule, verify]:** the final radius is 0 at 415 s, but matches last to 480 s, so survivors all take 260 HP/s with no armor and no regen. If no one kills, the biggest HP pool wins: 1400 HP lasts 5.4 s; 10 cubes + 3× plating ≈ 2980 HP lasts 11.5 s.
- **Effect:** converts "top 3 alive at the end" into wins. Cheap.

### 8. Dodging (BC §5, AI §4)
- **Do:** in fights, strafe perpendicular and reverse at random every 0.4–1.5 s. Each decision, simulate 9 move options for 0.6 s against visible `projectiles` and pick the one with the largest miss distance when a hit is predicted. Stop-and-go on heard `gun` sounds.
- **Why:** linear and circular guns lose to direction changes, and we can see bullets, which Robocode bots can't.
- **Effect:** cuts damage taken at range. Bullets seen from ≳ 110 m are dodgeable from a standstill; closer, only pre-emptive strafing helps.

### 9. Vision management (BC §6)
- **Do:** when not about to fire, turn aim toward the oldest-information bearing, limited to ±90° of the top threat. Lock on only for the last 0.2–0.5 s before a shot. Keep a 16-sector sound histogram with 5 s decay.
- **Why:** aim is our only eye (120°); tracks expire after 5 s; Robocode melee bots use oldest-scanned for exactly this.

### 10. Safe economy (BR §8, MG §4)
- **Do:** loot crates, cubes and pickups within ~60 m of the path to the next circle, before the departure time. Kill NPCs from 100–150 m while strafing (their bullets are 90 m/s). Take a laser in slot 1; keep the gun.
- **Why:** pros loot inside the circle instead of running long distances. The cube buffs (+4% HP and damage each, to 10) feed #7.

### 11. Supply drops (BR §9)
- **Do:** go only if no mech is tracked or heard within 120 m of the drop in the last 5 s and we can arrive ≤ 10 s after landing. Keep moving inside the 8 m ring and face the likely threat. Never stand still for the full 4 s.
- **Why:** every mech sees drops and hears them land at 600 m. A full heal + 3 cubes is big, but the holder is a slow target for mortars and lasers.

### 12. Target choice (BC §7)
- **Do:** score = hit probability × (2.5 if HP < 300) × (2 if it hit us in the last 3 s) × triangle bonus; switch only for ≥ 1.2× better.
- **Why:** Robocode melee: nearest, weakest, and whoever shoots you; avoid thrashing.

### 13. Third-party rule (BR §5)
- **Do:** treat a cluster of weapon sounds as a fight spot. Approach only if we're ≥ 70% HP and a `death` sound came from there; engage the survivor from 100–150 m only if it's < 50% HP.
- **Why:** fights are public (gun 320 m, death 600 m). Arriving right after a fight ends catches the winner before it heals.

### 14. Triangle weapon use (MG §4, AI §3)
- **Do:** laser on mortar holders (+60% cook-off = 504 at full charge). Mortar low arc on campers and drop holders, aiming at the ground for splash, never within 7 m of ourselves. Lightning only ≤ 45 m in the cone.
- **Why:** the rules, plus our DPS table (`online-mech-games.md` §4).

### 15. Upgrade picks (MG §2–3)
- **Do:** order roughly `plating` > `armor` > `nanites` > `gun_velocity` > `gun_damage` > `sensors`. Energy upgrades only if the bot uses jets.
- **Why:** HP pool for the collapse (#7), regen for poke-and-heal, bullet speed for lead accuracy. Opinion until measured; the other Researcher's `upgrades.md` has the full list.

## Not recommended

- RL or neural nets: no training infrastructure, standard library only, and rule-based aim and pathing are what winners use for this layer (BC §11–12).
- GOAP or a full influence-map grid per tick: too heavy for Python at 15 ms mean (AI §1–2).
- GuessFactor targeting: only if lead accuracy stalls below the 40% proxy (BC §1).
