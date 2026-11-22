# FPS tactics review: TenZ/Shroud analogies

Date: 2026-11-22
Scope: critic-only; no code and no match launch.

## Bottom line

Peeking, pre-aim, strafing, crossfire, cover, and surprise do not disappear in
Mechfight. They become bounded movement-and-information actions against
protocol-specific geometry and weapon timing. Adjectives such as "jiggle",
"shoulder", "crosshair placement", "flash/smoke", "wall-bang", "spray", "ADS",
"counter-strafe", "bomb setup", and "eco reset" are not importable unless a
rule below supplies the corresponding mechanism.

The highest-risk false analogy is **persistent camp/ambush**: the 15-mech
squad hunts our weakest visible position, remembered targets remain real for
5 s after LOS breaks, death and weapon sounds expose fights over hundreds of
metres, and the zone eventually forces movement. This is not a hide-and-wait
Tactical FPS loop.

## Rejected FPS analogies

| FPS phrase | Why it is rejected or incomplete here |
|---|---|
| ADS / recoil control | No ADS or recoil model. Gun spread exists; aim, lead, reload, and projectile flight are the only gun controls. |
| Smoke / flash / molotov | No smoke or flash item. No concealment field is created. Dense canopy, prisms, terrain, and bridges are geometry; trees do not block shots. |
| Jiggle/shoulder/wide peek as generic timings | A stepout is valid, but the protocol exposes charge and aim: laser charge is visible as `charging`; 0.15 s is minimum charge and 0.75 s is full, followed by 1.65 s cooldown. No fixed human "peek height" or crouch mechanic exists. |
| Crosshair-on-head | Mechs are cylinders and shots go along torso aim. There is no head hitbox. Aiming means yaw/pitch and muzzle/barrel geometry. |
| Wall bang / blind spray | Buildings, terrain and bridges stop gun/laser/mortar trajectories. Tree trunks block sight but not shots, and mortar splash is wall-blocked. Blind shooting into dense cover is not a normal FPS wall-bang. |
| Crossfire as two independent angles | Valid only if two threats can obtain LOS without becoming a shared-LOS stack. The 15-mech squad should normally be treated as one converging hunter set, not a friendly squad that benefits from friendly fire discipline. |
| Pre-aim every corner / 0.4 s counter-strafe | Torso aim where the bot looks (120° wedge at 200 m); aim changes over a 4 rad/s turn limit and pitch over 3 rad/s. The `50 ms` lockstep means movement and aim are continuous decisions, not instant crouch/ADS key frames. |
| Economy "buy" / eco round | There is no purchase economy. Power cubes scale HP/damage to 10; upgrades replace tactical choices; guns spawn only in slots/death, random loot is mortar/laser/lightning. |
| Spray-and-pray / ammo reset | Gun fires 45 damage every 0.24 s for 12 rounds, then reloads 2.4 s. Firing is a position-and-reload decision, not recoil-control practice. |

## Protocol-valid tactics

### Peeking

**Valid use:** briefly break LOS to acquire information or bait a visible laser
charge, then return behind the same or a different LOS blocker. 5 s target
memory means that the target is still known while hidden and a repeated
angle may be hunted. Gun peeking is not as strong: bullets travel 252 m/s,
range 230 m, and moving targets must be led. A mortar/mortar-arc peek is
also a 72 m/s ballistic decision, not a fast hitscan trade.

**Bounded exposure:** start at no more than 0.3 s outside cover at long
range, because that is about three 50 ms decisions and six 100 ms simulation
ticks. End as soon as the result is known: beam fired, laser charge
exposed, gun line/lead acquired, or third-party threat found. Re-expose
from another side or return to LOS only after the enemy cooldown window;
do not set a persistent dwell at the first angle.

**Guardrail:** if two or more enemies have LOS, if no LOS-blocking route
exists, or if HP/cover cannot sustain a follow-up trade, hide/break LOS
instead of "wide peeking". At the final circle, no cover delay can be
allowed to prevent maximum-HP/zone-position planning.

### Pre-aim

**Valid use:** orient the torso toward the latest damage bearing, a
tracked 5 s position, a gun/laser/lightning sound sector, or the shortest
expected exit route. A 180° rear arc makes facing the damage source
worthwhile: rear hits are 1.5×.

**Bounded pre-aim:** pre-aim only one highest-probability threat or the
bisector of two threats; do not keep scanning away from the current threat
long enough to create a rear hit. A 120° 200 m vision wedge means aim is
also vision: spend the last 0.1–0.5 s on target acquisition only after the
shortest route and zone route remain safe.

**Guardrail:** the 5 s track is stale, and 7° sound bearing noise means
sound sectors are not precise aim locks. Never aim to camp a sound; use it
to rotate, find cover, or estimate which weapon/trouble is approaching.

### Strafing

**Valid use:** a gun target at 50–230 m may be led less accurately if
direction reversals are coupled to projectile flight time
`distance / 252 m/s`, with minimum reversal time around 0.25 s from ground
acceleration. Visible projectile trajectory is usable. At close range, use
cover and weapon triangle rather than random strafing; lightning requires
45 m and a 30° cone, and charging a laser halves movement.

**Bounded exposure:** no sustained boost/strafe while it starves escape
energy or causes 5 m/s+ step/boost noise. The protocol makes sustained
randomness less valuable than minimum-risk LOS movement. Avoid stepping
back onto the attacker's 5 s tracked line.

**Guardrail:** strafe only while a LOS-blocking route remains reachable
within 1–2 s and while the route is inside the next zone. If no cover,
zone pressure is high, or the threat count is ≥ 2, execute an exit rather
than continue a strafe duel.

### Crossfire

**Valid use:** momentary numerical advantage exists only when cover, the
weapon triangle, or low HP can make a weak third party the next valid
target. Arrival after a fight or after a death sound can catch a weakened
survivor. Two+ bodies can be used to force a target to choose LOS lines,
but no friendly crossfire effect or communication discipline exists.

**Bounded exposure:** approach a fight only at ≥ 70% HP and only if the
survivor is estimated below 50% HP or a death sound confirms a removal.
Keep a route to cover and do not enter a radius where multiple LOS paths
converge. Treat 120 m tracked/heard threat distance as a hard drop zone
around a supply capture unless there is a known exit.

**Guardrail:** a crossfire/corner cannot be a passive hold. Re-evaluate
every 0.5 s and leave as soon as third-party LOS rises or the zone
deadline arrives. The 15-member hunting squad is adaptation-sensitive:
one visible ambush can turn into 2–4 converging threats.

### Smoke/cover and LOS

**There is no smoke mechanic.** "Smoke" is a protocol misnomer unless it
means a building/terrain LOS break or dense canopy. That break is real:
walls stop gun, mortar and laser shots, and a 5 s track does not prevent
cover from stopping shots. Trees provide soft/dense vision behavior but
trunk shots are not blocked.

**Valid use:** break LOS before the 5 s regen timer, not merely run around
at the last-seen position. Face the threat while moving, turn inward only
while the next exit remains available, and alternate exit angles. Cover
must lead to a walkable route, not merely to a corner.

**Bounded exposure:** rear-hit share should remain a late-loop proxy
≤ 20%, as defined in `objective.md`. Use ≤ 0.3 s peek windows for laser
acquisition, ≤ 1.5 s for a punished laser reset, and never exceed a
trade/heal calculation by persistent holding. For zone and supply
deadlines, cover is subordinate to travel time.

### Surprise

**Valid use:** short re-peeks, alternate the exposed angle, approach only
after death/weapon clues, use terrain rather than repeated linear
strafe, and strike low-HP targets from 100–150 m if triangle and cover
permit. Surprise is strongest before an enemy settles on the last angle.

**Invalid use:** no-LOS/unknown enemy is not "surprise". A 600 m death
sound and 320/380/420 m weapon sounds reveal fight positions. Gun shots,
laser charges/beams and movement make the hunter visible and noisy.
Sparse 45 m proximity sensing does not remove squad convergence.

**Guardrail:** one removal or one gun/laser acquisition is not a reason to
stay exposed. Element-of-surprise ends after 5 s of track persistence or
when a second LOS line appears.

## HP and economy guardrails

- Start HP is 1400. Regen is 45 HP/s after 5 s with no damage dealt or taken,
  and is impossible outside the zone or while zone damage continues.
- At `≥ 60%` of max HP a fight is not mechanically ruled safe; it is only
  one necessary threshold. Cover, third-party LOS, weapons, and zone position
  can still dominate.
- NPC drones are 350 HP and shoot for 25 damage at 90 m/s; crates are
  300 HP and cubes/loot create buffs. Low-Hp target choice is bounded by
  protocol values. No protocol rule defines a general 12–1400 HP tier or
  a 12-HP class, and simulation traces containing 12.0 do not create one.
  Use the live
  `obs.self.hp`, `obs.mechs[].hp`, max HP and config numbers.
- Supply capture is 4 s in an 8 m ring alone, yields 3 cubes and full HP.
  It is not free: hold it only when uncontested for at least 80 m/10 s
  departure logic and a post-capture exit are available.
- With 260 HP/s outside the final circle after 415 s, armor and regen do
  not help. Final-burn position and HP outrank extra peeking.

## Zone and tick guardrails

- `50 ms` answer is two simulated ticks; missing answers coast for 1 s
  before idling. Keep decisions below the 15 ms mean / 35 ms p99 budget.
- Default 0.3 s peeks are 3 decisions (6 ticks) and should be measured,
  not treated as event-free.
- Zone radii/shrinks are 560→380→240→140→70→25→0 m, with the last circle
  closing at 415 s. The 20–260 HP/s outside-zone damage is not coverable
  by armor or regen. Enter the next circle before the shrink; never trade
  exposure for a fight outside it.

## Findings ranked

1. **Reject persistent corner/smoke/crossfire camps.** Real cover is valid,
   but five-second tracking, shared-convergence risk, and zone deadlines
   turn long holds into the highest rear/third-party exposure.
2. **Define peeking with laser timings, not FPS labels.** ≤ 0.3 s acquisition
   and alternate/exit angles can be useful; full laser charge can be observed
   and 1.65 s cooldown provides a bounded reset.
3. **Keep strafing secondary to LOS.** Gun lead and projectile dodging are
   valid, but minimum-risk cover position cuts multi-threat damage more than
   random motion.
4. **Pre-aim damage/sound sectors; do not turn every unknown bearing into a
   rear exposure.** Face the source, but preserve zone and escape routes.
5. **Reject smoke, ADS, wall-bang, headshots and eco-round analogies.**
   They imply mechanics absent from `mechfight/1`.

## Testable next package

No match or code is proposed. If a run needs this class of change, test one
bounded candidate: **laser-aware cover peek** against the calibrated squad.
Primary metric: laser damage taken/dealt during LOS-break cycles. Guardrails:
no exposure window over 0.3 s to acquire, no persistent hold over 1.5 s
after a reset, no reveal outside the next zone, rear-hit share ≤ 20%, and
no staged trade with ≥ 2 LOS threats. Reject if zone deaths or outside-zone
ticks rise.
