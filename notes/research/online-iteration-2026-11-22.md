# Outside tactics translation: iteration 2026-11-22

Researcher (online), 2026-11-22. Scope: battle royale, drones/NPCs, zone control,
squad hunting, movement, cover, and weapon triads. This report separates
well-supported findings from likely transfer and names the local evidence that
could falsify each hypothesis.

Evidence labels:
- **[rule]**: direct Mechfight protocol fact.
- **[data]**: measured data or a published experiment.
- **[pro]**: named professional/team guidance.
- **[game-ai]**: published game-AI or Robocode implementation practice.
- **[guide]**: community advice without strong independent validation.

## Executive ranking

1. **M1: rotate early on the dead/quiet side, through cover** — high confidence
   for reducing avoidable damage; test as route choice, not absolute edge.
2. **M2: choose 6–12 candidate positions by LOS count, zone depth and rear wall** —
   strongest geometry translation for the 15-hunter field.
3. **M3: break LOS and stop firing while regenerating** — directly consistent
   with the 5 s regen timer and shared squad vision.
4. **M4: adapt gun aim by observed movement segment** — closed-form intercept
   plus an empirical fallback is cheap and already partially built.
5. **M5: lightning ambush and laser short use** — rules-backed triangle
   counterplay, but need a measured win in a varied opponent pool.
6. **M6: avoid NPC homes, decide loot by threat-adjusted value** — medium
   confidence; drone route smoke was small (+0.25 on sub1's 2.00 base).
7. **M7: stagger/alternate movement and face threats** — low/medium confidence;
   useful against projectiles, but visible trajectories make exact dodging better.
8. **M8: focus fire after isolation, not indiscriminately** — useful only while
   the target is killable within 2–3 weapon cycles.
9. **M9: capture drops only when uncontested and near the route** — medium
   confidence; stationary capture may leak too much exposure.
10. **M10: use the weapon triangle as a procurement preference** — high confidence
    mechanically, but low confidence without a side-by-side local A/B.

## 1. Battle royale and zone control

### Proven outside idea

Dignitas describes a “deadside”: player congestion forms on the side of the next
circle that is forced into the zone, while the opposite side is quieter. It
recommends a route with buildings/terrain and rotating early in stacked
tournaments. [pro] A professional PUBG guide likewise starts next-rotation
planning quickly and warns that crossing open ground late is especially risky.
It also prefers the centre only when loot, teammates and terrain permit; edge
play is a fallback. [pro]

Sources:
- https://dignitas.gg/articles/everything-you-need-to-know-about-positioning-and-rotation-in-fortnite
- https://dignitas.gg/articles/professional-pubg-movement-positioning-and-rotations-with-ziphon

### Mechanic hypothesis

`H-ZONE-DEADSIDE`: plan a route to the next circle as soon as the next centre/
radius are known. Use the side away from the hunters' centroid for the
destination, then follow wall and rooftop cells with cover instead of the
straight line. Start at `shrink_start - 1.5 * travel_time - 5 s`, using at least
a 10 m radius margin.

Discriminating test: four variants, 56+ matched seeds: exact centre, 0.6 radius
inner edge quiet side, 0.85 radius quiet edge, and current `next_center` route.
Measure outside-zone ticks, hunter LOS at arrival, and HP at 120 s. A benefit
needs at least -5 percentage points in early losses or +0.4 mean place.

### Disconfirming evidence

- The Fortnite source's congestion model assumes many distributed players and
  changing player distributions; Mechfight has 15 known hunters, shared vision,
  and a 16-mech team-vs-solo geometry. `deadside` can become a hunter ambush if
  the centroid shifts or a hunter arrives first.
- PUBG's centre recommendation depends on squadmates and compounds; the bot has
  no teammates and no friendly-fire cover benefit.
- Mechfight zone damage is only 20–35 HP/s in early phases [rule], so entering
  early is not always worth an exposed late route.
- Local data: zone immunity alone changed sub1 to 2.05 in a 40-seed squad run,
  while 123 drone deaths remain; the result is not enough to infer that zone
  routing alone wins. Sim calibration is only one model.

## 2. Drone/NPC use and loot value

### Proven outside idea

BR/NPC systems work as autonomous roles: drones or units detect, chase,
patrol and return to a leash; in a few war/drone examples, reconnaissance and
remote assistance support a fight rather than replacing positioning. This is
role separation, not a reason to charge every nearby object.

The strongest local fact is not external: drones are 350 HP NPC mechs that shoot
when attacked or near a home, deal 25 damage per 1 s shot, chase to 90 m and
return at 60 m from home, then drop 2 cubes [rule]. Drones cannot die to the
zone.

### Mechanic hypotheses

`H-DRONE-HOMES`: never select a movement/loot goal within 50 m of a drone home
unless the bot already has a protected lane and no visible mech threat.
The 50 m number is a local hypothesis, not game balance.

`H-DRONE-FARM`: attack an NPC only when:
- it is isolated and the nearest visible mech is outside 80–120 m;
- the route remains inside the next zone;
- a route can be broken to cover in under 5 s;
- the gain is 2 cubes and roughly 2×350 HP of expected damage;
- no supply/drop or better cube is closer.

Do not use a drone as a body shield or assume allied firing creates no exposure.
NPC bullets have a sound model and engagement reveals the bot to the squad.

Discriminating test: paired 56+ seeds for 50 m / 30 m / no drone avoidance and
0 / 80 / 120 m minimum threat distance. Report drone-assisted kills separately
from direct mech kills, as requested. The local metric should include:

- drone deaths attributable to our bot vs zone-only/independent;
- mech damage taken during drone fight;
- cubes gained per 100 s;
- net place delta.

### Disconfirming evidence

- Avoidance is not automatically good. Drones drop 2 cubes, and cubes heal and
  increase damage 4% each; they can be worth a controlled fight.
- Drones do not have the 15-hunter lethality of a mech, but 12 of them make
  close terrain combat noisy and can expose the bot.
- Local smoke: adding `DRONE_AVOID=50` reduced estimated squad drone deaths
  from about 3.1 to 2.75 per match, while sub1 scored 2.25; this is small and
  not a completed 40-seed result. It does not prove the routing gain was positive
  in a real calibrated match.
- A 350 HP drone takes repeated hits and can delay the zone or get the squad
  called in by gunfire. A “free 2 cubes” claim is false if the pursuit takes
  >10 s or resets regen.

## 3. Multi-enemy hunting squads

### Proven outside idea

In a bounded planar pursuit-evasion game with full camera visibility, Klein,
Suri and colleagues prove that three pursuers with equal evader speed are
sufficient and sometimes necessary to capture an unpredictable evader [data].
The result assumes the pursuers know the evader and each other, can close in,
and is about worst-case capture; it does not compute a damage-based FFA.

Source: https://arxiv.org/abs/1110.4838

Horde/fighting-circle systems solve multi-attacker combat by limiting active
attackers or distributing targets into attack lanes. Where the track lacks such
limits, a bot can achieve the same result with geometry: place a wall behind
it and let only one hunter approach a lane.

Sources:
- https://code.tutsplus.com/battle-circle-ai-let-your-player-feel-like-theyre-fighting-lots-of-enemies--gamedev-13535t
- https://www.strayspark.studio/blog/attack-token-system-ue5-group-combat-that-feels-fair
- https://www.oreilly.com/library/view/unity-2018-artificial/9781788626170/d9807718-33bb-41f9-884e-59caf70dc0ac.xhtml

### Mechanic hypothesis

`H-FUNNEL`: when at least 3 hunters are tracked, score 6–12 wall-adjacent
candidate points by:

`score = LOS_count_of_nearest_5_trackers * 100 + distance_to_point`

Reject candidates that would make the bot face open ground, and require a wall
with a normal away from the hunter centroid. Prefer LOS count 0–1. Cache for 1 s
and invalidate if a threat moves >10 m. It should be cheap: at most 40 LOS calls.

`H-FOCUS`: once isolated behind a funnel, commit to the lowest reachable
`ttk = hp / expected_damage_per_s`, not the nearest target. A target with
another hunter nearby is not automatically valuable if those hunters can
establish a crossfire.

`H-RESET`: after a damaging event, break LOS and stay quiet for 5 s before
voluntary engagement. This directly protects the regen timer [rule].

### Disconfirming evidence

- Three pursuers guarantee capture only under full information and equal speed.
  It does not prove 15 will kill a lower-speed/cover bot. Mechfight sight and
  memory are not full camera surveillance: enemies lose view after 5 s, and
  cover matters.
- H-FUNNEL can create a hunter-proof box that is mortally exposed to mortar
  shots over cover. Mortar direct damage is 200 and splash 160 to 7 m [rule].
  This hypothesis must have a mortar-to-cover test.
- Focusing low HP can be wrong if that enemy is too far, behind cover or draws
  no extra damage from our weapon. Access and TTK should multiply, not just HP.
- H-RESET can lose the zone or a supply drop; it should trigger only when in-zone
  and a valid cover route exists.
- Local data: current uncalibrated squad is 1.98–2.20 for sub1/s_base2 while
  example is 1.40. These are a model result, not a track result.

## 4. Movement

### Proven outside idea

Robocode minimum-risk movement does not pick a point by brute force or anti-
gravity alone: it samples useful candidate points and scores enemy distance,
targeting geometry and wall behavior [game-ai]. Guess-factor targeting records
which prediction offsets hit and segments results by range, velocity and wall
proximity [game-ai]. This is a strong analogue for adapting aim to each enemy.

Sources:
- https://robowiki.net/wiki/Minimum_Risk_Movement
- https://robowiki.net/wiki/GuessFactor_Targeting

Ziphon’s PUBG advice is to dash sideways, crouch-speed variation and zigzag
against distant predictable fire [pro]. It is weak evidence for exact phase
timing because PUBG vehicles, crouch and projectile models differ.

### Mechanic hypotheses

`H-INTERCEPT`: solve gun intercept against target velocity and retain a 0.3 s
acceleration-aware fallback for turns. This is already supported by the gun
unit test's reported 0.20→0.40 hit rate improvement when prediction is enabled.

`H-RANDOM-PHASE`: at 60–150 m, switch horizontal direction every 0.3–0.6 s
rather than every 0.1 s; 0.3 s is below a gun cooldown (0.24 s), 0.6 s gives
at least one or two gun cycles between reversals [rule]. Be a 1.5 s floor for
running between walls to avoid local dithering.

`H-MOVE-DODGE`: with visible projectiles, predict 9 command options over 0.6 s
and choose maximum miss distance. This should only override strategic movement
when a projectile is predicted to reach us; it avoids changing goals every tick.

`H-REAR`: after a `damaged.rear` event, face the bearing immediately. Rear damage
is 1.5× [rule].

### Disconfirming evidence

- Fast fixed reversals are predictable and can be modeled by hunters. Robowiki
  explicitly warns that linear/circular targeting can be defeated by head-fakes;
  a virtual gun/segmented hit table is safer than a hard reversal schedule.
- In a 2.5 m radius mech, 0.3–0.6 s is a 2.5–14 m move depending on acceleration.
  Extreme zigzag can run into walls and drain boost.
- A gun bullet travels 252 m/s [rule]; visible projectile dodge is exact enough
  that 9 candidate commands should beat a periodic random phase at 100 m.
- Local uncalibrated result: run mode died sooner with rear/back-to-shooter
  behavior; it was fixed by facing the shooter after hit. There is no result
  showing `RUN_MODE` itself helps yet.

## 5. Cover and line-of-sight

### Proven outside idea

Killzone's dynamic tactical position evaluation rates candidate points for cover
from primary/secondary threats, preferred fighting distance and proximate
movement; modular influence maps similarly support threat, friendly, objective
and cover layers [game-ai]. This is closer to Mechfight than static camping:
candidate points are evaluated against live threats and geometry.

Source:
- https://gdad.wiki/wiki/programming/game-ai/influence-maps

FPS and tactical sources recommend wide swings only after an information peek,
which is analogous to the mechfight laser: charge is visible, but a quick peek
can gather information and bait release [guide].

### Mechanic hypotheses

`H-COVER-CANDIDATE`: build 12–24 candidates: current position, 30–60 m wall
cells, next-circle edge positions and a few high-ground sites. Score:

- +LOS blocked against every recent threat;
- +inside next zone;
- +preferred weapon range;
- +wall behind, especially opposite the damage bearing;
- -distance beyond 80 m;
- -mortar visibility or roof eave exposure.

`H-JIGGLE-LASER`: if holding a laser, do a short 0.3 s exposed charge? No:
the protocol reports `charging` to enemies and firing is visible. Keep charge
behind cover, step out only after expected LOS, release at ≥0.75 s or
immediately after 0.15 s if line is about to break.

`H-PEEK-PUNISH`: use a quick move/LOS check when near a corner; do not commit
a full 45 m lightning swing until a target is in the 30° cone. The outside
peeking source recommends low-risk info, then high-risk commit [guide].

### Disconfirming evidence

- Trees do not stop gun, laser or mortar [rule]; blind firing at a sound through
  trees can break a hiding position.
- A wall that reduces LOS can reduce our own view and expose us to mortar or
  a second hunter outside the first hunter's lane.
- Cover candidates based on last-known threats can be wrong after 5 s because
  the tracker's memory decays.
- `find_cover` and similar searches have timing limits in the repo. Any update
  must stay below 15 ms mean / 35 ms p99.

## 6. Weapon triads

### Proven outside idea

BattleTech and mech literature consistently divide combat by range and role:
long-range precision, mid-range sustained fire and close-range burst; terrain
and cover decide how that triangle is used. This is broad mech experience, not
direct numerical evidence for Mechfight [guide].

Sources:
- https://comstar.home.blog/2023/04/30/a-mechwarriors-guide-to-long-ranged-weapons-part-1/
- https://gamefaqs.gamespot.com/pc/63435-mechwarrior-3/faqs/82593/weapon-and-equipment-appraisal

### Mechanic hypotheses

The protocol makes a formal triangle [rule]:

1. `laser beats mortar`: 315 damage at full charge, cook-off adds 60% against
   a mortar holder, and laser outranges mortar.
2. `mortar beats lightning`: 200 direct / 160 splash, concussion throws mechs
   and drains 45 energy.
3. `lightning beats laser`: 60 damage plus up to 2 chains and a 2 s laser short.
4. `gun is neutral`, with 45 damage, 252 m/s, 12-round magazine and 0.24 s cycle.

`H-TRIAD-PICK`: use observed enemy weapons to prioritize:
- kill/short a visible laser user with lightning within 45 m;
- carry mortar or laser pickup against a mortar holder, prefer laser due the
  cook-off and triangle;
- against a lightning holder, keep outside 45 m or carry mortar;
- close to <60 m only with a range advantage or cover; do not kite an open
  gun duel at 130 m with a gun-only matchup.

`H-LIGHTNING-AMbush`: wait behind a wall/corner and stop/ambush as the hunter
walks to the last known position. Fire every 0.25 s only while the target is in
a 30° cone within 45 m and LOS is true. Bonus for 2–3 targets within 14 m.

`H-LASER-PEEK`: charge behind cover, step enough to see and release, then break
LOS. Start no charge in open ground if a mortar holder has predictable splash.

### Disconfirming evidence

- A triangle is not a one-dimensional sidegrade. Gun fire can be more reliable
  against moving targets than a fully charged laser. The gun has 12 shots and
  reload 2.4 s; laser has a 1.65 s cooldown and visible charge [rule].
- Lightning is short-range and a missed 3-energy shot still costs energy [rule].
  Chasing it to 45 m can abandon zone and expose the bot to a third hunter.
- Mortar can hit cover and rooftops with splash, but own splash hurts at 50%
  and recoil/concussion affects our energy [rule].
- Lightning chain bonus is small unless 2–3 enemies remain within 14 m. With
  15 hunters but mostly dispersed, it may be noise.
- Mechfight laser has no lock-on and the charge remains visible. A predictable
  peek will be dodged; the advantage is timing and target isolation, not
  “always charge 0.75 s.”
- Local evidence: house-bot data says full-charge lasers hit 4/5 at 100–150 m;
  if real, the bot should break LASER LOS or hold a triangle counter before
  opening a gun duel. This is an opponent observation, not track-measured data.

## 7. Cross-domain negative controls

These ideas should **not** become bot behavior until they pass local A/B:

1. **Static edge camping.** It avoids rotations but invites hunters in the next
   ring and gives mortar a stationary target.
2. **Always center in late game.** LLM/BR guides suggest it may be safe, but
   full squads converge there and cover can be contested.
3. **Hunt the weakest visible target.** If it is still behind cover or has
   allies ready to crossfire, target access dominates low HP.
4. **Drone-farm for cubes.** Direct cube value ignores revealed position,
   incoming damage and zone travel.
5. **Fixed zigzag.** Predictable reversal gives trackers enough time to lead;
   outcome must be tested with the `AIM_PREDICT` switch and 9-projectile dodge.
6. **Always enter supply drops.** Four? The actual Mechfight capture requires
   4 s alone in an 8 m ring [rule], making it a high-exposure stationary action.
7. **Perfect zone edge for whole match.** It reverses in every ring and the
   final circle has radius 25 and then 0 [rule].
8. **Carry all weapon types.** Mechfight has two slots plus a gun, and ammo,
   laser charge and switching can waste combat time.

## 8. Proposed A/B order

The following is the evidence-first test order. It is research-only; no code
change is requested or made.

| Hypothesis | Local switch / variant concept | First metric | Falsify if |
|---|---|---|---|
| H-ZONE-DEADSIDE | route mode `NEXT_DEADSIDE` | outside-zone ticks, early HP | no +0.4 place / no -1.0 early outside-tick pts |
| H-FOCUS/H-FUNNEL | `s_funnel`, `CHAIN_PICK` only later | LOS count, TTK, place | LOS count not reduced or p99 >35 ms |
| H-RESET | `b_regen_hide` | regen cycles, repeat shots | fewer regen cycles or slower zone |
| H-INTERCEPT | `AIM_PREDICT=True` only | gun hit 50–150 m | hit rate <40% and no place gain |
| H-TRIAD/LIGHTNING | lightning-first + `s_close` | kills and death rate | <+0.7 kills/match, target result not persist |
| H-LASER-PEEK | `s_peek` if a laser charge switch exists | laser hits / laser TTK | no hit improvement; p99/late answer risk |
| H-DRONE-HOMES | 30/50/80 m avoid bands | drone deaths, assisted/total kills | no net place gain in 56 paired seeds |

Guardrails for every test:
- 56 matched seeds minimum; rotate.
- Report direct mech kills, NPC-assisted deaths and zone deaths separately.
- Reject any result based on one 8-seed batch.
- Stop two A/Bs running concurrently because stale loops and result overwrite are
  known project risks.

## 9. Source audit and confidence

Strongest:
- Mechfight protocol and config facts [rule].
- Klein/Suri complete-information pursuit-evasion [data].
- Robowiki minimum-risk and guess-factor explanations [game-ai].
- Dignitas/Ziphon professional rotation writing [pro].

Moderate:
- Fighting-circle/attack-token implementations [game-ai].
- Influence-map and position-evaluation methods [game-ai].

Weak:
- Fortnite/PUBG single guides and forum advice [guide].
- Cross-game weapon triangle articles [guide].
- “AI Battle Royale” and hero drone marketing pages; not used as evidence.

No outside source was treated as empirical validation of Mechfight. It was
translated into one testable mechanic hypothesis and one falsification.

