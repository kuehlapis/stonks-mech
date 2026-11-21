# Every mechanic the brain can use

Strategist/moderator, 2026-11-22. One row per mechanic from `protocol.md` §6–10. "Used" is from a grep of `python/*.py` on this date. The goal is for the brain to weigh every one of these, not just a few.

## Actions (the full output space)

| Action | What it can do | Brain uses it | Gap / idea |
|---|---|---|---|
| `move` (legs independent of torso) | Strafe, backpedal while facing, circle, sprint to cover | yes (strafe, flee, travel, farm) | Pick the strafe axis so cover is on the side we move toward |
| `boost` on the ground | 19.5 m/s, 17 energy/s | flee and cover only | Boost-strafe in fights (`STRAFE_BOOST_E`, A/B running) |
| `boost` in the air = jet | Climb roofs, about 60 m on 100 energy | nav only (ledges, roofs) | Roof escape when two or more hunt us; jet over walls to break line of sight |
| `jump` | 1 s hop, 2.75 m high | **never in fights** | Hop on strafe reversal (`STRAFE_JUMP`, A/B running); jump over a mortar's splash |
| `aim` (turn 4 rad/s, pitch −0.7…1.3) | Face the shooter so its hits land on the front | yes | **Rear hits ×1.5 are never tracked.** When `damaged.rear` arrives, turn to `bearing` first |
| `fire` slot 0 / 1 | Hold to fire, laser charge and release | yes | Blind fire into trees at a sound (trees don't stop shots) |
| `reload` early | Start the 2.4 s reload before the magazine is empty | yes | Reload whenever out of sight with < 6 rounds |
| `pick` upgrade | Spend cubes on upgrades | yes (fixed order) | Order by phase: plating and nanites first for the burn HP |
| `take` + `drop` | Swap loot; `drop` alone empties a slot | take only | **Drop the gun to carry laser + lightning** (only 2 slots); A/B it |

## World rules

| Mechanic | Rule | Brain uses it | Gap / idea |
|---|---|---|---|
| Rear armor | Hits from outside the front 180° do ×1.5 | partly (faces the fought enemy) | With 2+ threats, face the one doing the most damage and put a wall at our back |
| HP regen | 45 HP/s after 5 s with no damage dealt or taken | implicitly (HP fraction gates) | Disengage for 5 s and wait to regen before re-peeking; regen does not run outside the zone |
| Energy | Regen 18/s after 0.6 s; boost, jets and lightning share it | gates only | Budget: keep ≥ 40 for an escape jet, spend the rest strafing |
| Line of sight | Buildings and terrain block; **trees block nothing** | yes (`los`, cover) | Never treat a tree as cover; shoot through trees |
| Vision memory | Seen mechs tracked for 5 s after leaving view | yes (perception) | Their memory works the same: move at least 5 s out of sight before settling |
| Sound | Steps > 5 m/s, boost, each weapon has its own sound | perception (bearings) | Walk under 5 m/s when hiding. Learn enemy weapons from sound kinds before we see them |
| Overlap push | Mechs push apart | no | Ignore |
| Mortar concussion | Throws mechs (16 m/s, 9 m/s up), drains 45 energy | dodge only | Stay off roof edges near mortar holders |
| Lightning short | Takes a laser offline for 2 s | yes (pickup order, range pref) | Fire lightning at a charging enemy first, then the laser |
| Laser cook-off | +60% to a mortar holder | yes (fight model) | Target mortar holders first |
| NPC drones | 350 HP, 2 cubes, aggro at 45 m, leash 30/60 m | yes (farm) | — |
| Crates | 1 cube, half drop a weapon | yes (farm) | — |
| Supply drop | Stand in the 8 m ring alone for 4 s: 3 cubes, full HP and energy | yes (`DROP_ON`) | Late-game full heal before the burn |
| Zone | Shrinks; outside = damage and no regen | yes | — |
| Final burn | Radius 0 at 415 s, 260 HP/s, most HP wins | **not as a plan** | From about 375 s: full HP, plating, hold the final center, avoid all damage |

## Highest-value gaps (proposed order)

1. **Rear-hit turn:** on `damaged.rear`, turn to the bearing before anything else. Cheap; halves extra damage.
2. **Burn endgame:** from 375 s, regen to full and stop fighting unless cornered. Placement is decided at 415 s.
3. **Regen discipline:** after a trade, break line of sight for 5 s before re-engaging.
4. **Drop the gun for laser + lightning** once both are on the map nearby.
5. **Blind fire through trees** at sound bearings.

Each becomes a switch (off by default) and an A/B against the squad, like `m_boost` and `m_hop`.
