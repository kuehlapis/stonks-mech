# Upgrades (`config.upgrades`)

Source: `notes/research/hello.json` → `config.upgrades`, 22 entries, printed by a scratch one-liner. Rules: protocol §10 (offer at each cube threshold `1, 3, 6, 10, 15, 21, 28, 36, 45`; 3 distinct choices you can still take; weapon upgrades only for weapons held when the offer is drawn; **no pick by `expires` (5 s) applies choice 0**; upgrades belong to the mech, not the item).

Paths: `mech.X` changes `self.stats.X`; `weapons.K.X` changes `self.weapons[i].stats.X` for the slot holding kind K. `mul` multiplies, `add` adds, per stack.

| id | name | desc | effects (per stack) | max | requires |
|---|---|---|---|---|---|
| `plating` | Composite plating | +15% max HP | `mech.hp` mul 1.15 | 3 | - |
| `armor` | Reactive armor | -8% damage taken | `mech.armor` add 0.08 | 3 | - |
| `servos` | Leg servos | +8% walk and boost speed | `mech.walk_speed` mul 1.08; `mech.boost_speed` mul 1.08 | 3 | - |
| `capacitor` | Capacitor bank | +30 max energy | `mech.energy` add 30 | 3 | - |
| `reactor` | Reactor tune | +30% energy regen | `mech.energy_regen` mul 1.3 | 3 | - |
| `jets` | Efficient jets | -25% boost and jet energy drain | `mech.boost_drain` mul 0.75; `mech.jet_drain` mul 0.75 | 2 | - |
| `nanites` | Repair nanites | +60% out-of-combat regen, starts 1.5 s sooner | `mech.regen_per_s` mul 1.6; `mech.regen_delay` add -1.5 | 2 | - |
| `gyros` | Torso gyros | +30% aim turn rate | `mech.turn_rate` mul 1.3; `mech.pitch_rate` mul 1.3 | 2 | - |
| `sensors` | Sensor suite | +15 m proximity sensors, +25 m vision, halves sound bearing error | `mech.near_range_bonus` add 15; `mech.vision_bonus` add 25; `mech.hearing` mul 0.5 | 2 | - |
| `gun_damage` | Tungsten rounds | +15% arm gun damage | `weapons.gun.damage` mul 1.15 | 3 | gun |
| `gun_rate` | Rotary feed | +15% arm gun fire rate | `weapons.gun.cooldown` mul 0.87 | 3 | gun |
| `gun_velocity` | Rail barrel | +25% arm gun projectile speed | `weapons.gun.speed` mul 1.25; `weapons.gun.range` mul 1.15 | 2 | gun |
| `gun_mag` | Drum magazine | +8 rounds, -20% reload time | `weapons.gun.mag` add 8; `weapons.gun.reload` mul 0.8 | 2 | gun |
| `mortar_splash` | Cluster shells | +30% mortar splash radius | `weapons.mortar.splash_radius` mul 1.3 | 2 | mortar |
| `mortar_reload` | Autoloader | -18% mortar cooldown | `weapons.mortar.cooldown` mul 0.82 | 3 | mortar |
| `mortar_velocity` | Long tube | +20% shell speed | `weapons.mortar.speed` mul 1.2 | 2 | mortar |
| `laser_charge` | Fast capacitors | -25% laser charge time | `weapons.laser.charge` mul 0.75 | 2 | laser |
| `laser_damage` | Focusing lens | +18% laser damage | `weapons.laser.damage` mul 1.18 | 3 | laser |
| `laser_pierce` | Phased beam | Laser passes through one more target | `weapons.laser.pierce` add 1 | 1 | laser |
| `lightning_chain` | Arc relay | +1 lightning chain jump | `weapons.lightning.chain` add 1 | 2 | lightning |
| `lightning_range` | Tesla coil | +20% lightning range and cone | `weapons.lightning.range` mul 1.2; `weapons.lightning.cone_deg` mul 1.2 | 2 | lightning |
| `lightning_efficiency` | Superconductor | -35% lightning energy cost, +10% damage | `weapons.lightning.energy` mul 0.65; `weapons.lightning.damage` mul 1.1 | 2 | lightning |

## Stacked values (base numbers from `config.mech` / `config.weapons`)

| id | 1 stack | full stacks |
|---|---|---|
| plating | 1400 → 1610 HP | ×3: 1.15³ = 1.521 → 2129 HP |
| armor | weapon damage ×0.92 (effective HP ×1.087) | ×3: ×0.76 (eff. HP ×1.316); marginal stacks ×1.087, ×1.095, ×1.105. **Not zone damage** (§7) |
| nanites | 72 HP/s after 3.5 s | ×2: 115.2 HP/s after 2.0 s |
| servos | walk 12.6, boost 21.1 m/s | ×3: walk 14.7, boost 24.6 |
| capacitor | 130 energy: 8.7 s jet ≈ 86.7 m climb | ×3: 190 |
| reactor | energy regen 23.4/s | ×3: 39.5/s |
| jets | boost drain 12.75/s, jet 11.25/s | ×2: 9.56/s, 8.44/s (100 energy ≈ 118 m climb) |
| gyros | turn 5.2 rad/s, pitch 3.9 | ×2: 6.76, 5.07 |
| sensors | near 60 m, vision 225 m, bearing σ 3.5° | ×2: near 75, vision 250, σ 1.75° (assuming `hearing` scales the 7° noise) |
| gun_damage | 51.75 | ×3: 68.4 (×1.521) |
| gun_rate | cooldown 0.209 s | ×3: 0.158 s (DPS ×1.519) |
| gun_velocity | 315 m/s, range 264.5 | ×2: 393.8 m/s, range 304 |
| gun_mag | 20 rounds, reload 1.92 s | ×2: 28 rounds, 1.54 s |

Reference DPS at 0 cubes: gun 187.5 in a burst, about 107 sustained (12 × 45 = 540 per 2.64 s firing + 2.4 s reload); laser 315 per 2.4 s (0.75 charge + 1.65 cooldown) ≈ 131, hitscan to 280 m.

## Which look strongest for a survival-first bot

1. **`plating` (take every stack).** ×1.15 per stack beats `armor` on every stack (1.15 vs 1.087/1.095/1.105 effective HP), and unlike armor it also counts against zone damage and in the HP tiebreak at 8:00 (§4). It decides the end: the last circle has radius 0 by 415 s (`zone.md`), after which every survivor bleeds 260 HP/s with no regen, so **whoever has the most max HP at that moment wins**: 1400 HP lasts 5.4 s, 2129 HP 8.2 s, and 10 cubes (×1.4) on top give 2981 HP = 11.5 s. Open question: whether plating heals the added HP (cubes do; §10 doesn't say for upgrades). Check `self.hp` after the first plating pick.
2. **`nanites`.** The plan "disengage, break line of sight, regen" (objective priority 3) gets 2.5× faster: full heal from 0 takes 36.1 s base, 22.9 s at 1 stack, 14.2 s at 2 stacks. Worthless outside the zone and in the last circle, so it ranks below plating.
3. **`armor`.** Solid second-tier defense against weapons; weaker than plating per stack and does nothing against the zone.
4. **`gun_rate` / `gun_damage`.** Always offerable (every mech holds a gun unless it drops it) and +15% DPS each; winning fights faster also means taking less damage. `gun_velocity` helps hit rate at 100–200 m (flight time to 150 m drops from 0.60 s to 0.48 s) and may matter more than raw damage for a bot whose aim is the weak point.
5. Situational: `servos` (zone escapes, kiting), `sensors` (see a laser mech before it sees you: +25 m vision), `capacitor` (one stack makes the 72–76 m dorm-tower roofs reachable: 76.3 m rise needs ≈ 7.4 s of jet after the 2.75 m jump = 111 energy).
6. Weak for this bot: `reactor`, `gyros`, `jets`, mortar and lightning upgrades unless those weapons are kept.

Because a missed pick applies choice 0, **the bot must always send `pick`** within 5 s, ranking the 3 choices by a fixed priority list like the one above.
