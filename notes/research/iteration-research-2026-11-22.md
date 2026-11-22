# Iteration research: score above 10

Date: 2026-11-22

## Executive answer

The first 120 s and the final 25 s decide this proxy. In the latest valid
40-seed run, sub1 and s_base2 live outside the zone 0% and 1.09% respectively,
yet still lose early: sub1 70.0% before 120 s and s_base2 72.5%. The highest
priority is therefore **survival against the squad pressure**, not zone routing:
zone routing is already nearly solved, while gun/laser/NPC pressure remains
fatal. The direct bot-kill/NPC-assist split is secondary to staying alive long
enough to reach loot, upgrades, drops, and the HP tiebreak.

## 1. Zone timing

**Evidence/config**

- `hello.json`: `config.zone.start_radius` 560; phases are
  380/240/140/70/25/0 m with DPS 20/35/60/100/160/260.
- Exact cumulative windows are in `notes/research/zone.md` and agree with
  `protocol.md §9`:
  phase 1 hold/shrink 0–60/60–110 s;
  phase 2 110–155/155–195 s;
  phase 3 195–230/230–265 s;
  phase 4 265–295/295–325 s;
  phase 5 325–350/350–375 s;
  phase 6 375–390/390–415 s.
- `protocol.md §9`: inside the next circle at `shrink_start` keeps you inside
  through the linear shrink.
- `protocol.md §7 Health`: zone damage is not reduced by armor and resets
  regeneration.
- `protocol.md §4` and `§9`: the circle reaches zero at 415 s; the match has
  480 s, and every remaining mech then takes 260 HP/s until HP or death decides
  it.

**Latest result**

- A wall/zone-priority fix reduced one replay's outside-zone wedge by 1,086
  ticks (`-24.5%`) in
  `notes/tests/2026-11-22-pre415-squad-zone-trace.md`.
- `cal-postfix-sub1-40.json`: sub1 0% outside-zone ticks, 0 pre-415 squad zone
  deaths.
- `cal-postfix-s_base2-40.json`: s_base2 1.09% outside-zone ticks, 0 pre-415
  squad zone deaths.
- Therefore zone death is no longer a valid explanation for the low scores.

**Expected behavior**

- Depart from a position outside the next circle early enough for the configured
  11.7 m/s walk or 19.5 m/s boost.
- Prioritize `zone_exit` over wall-slide side goals.
- From roughly phase 4 (295 s) onward, stop zone exposure and avoid trades that
  do not kill; the 100+ DPS zones make HP loss irreversible quickly.

## 2. NPC/drone behavior and kill assistance

**Evidence/config**

- `hello.json`: `config.npc.count=12`, `hp=350`, `aggro_range=45`,
  `deaggro_range=90`, `chase_leash=60`, `damage=25`,
  `cooldown=1`, `projectile_speed=90`, `cubes=2`.
- `protocol.md §7 NPC drones`: drones shoot at attackers or visible aggroed
  targets, chase until the 90 m / 60 m limits, drop 2 cubes, do not take zone
  damage, and no-zone damage is paired with 350 HP.
- Drones have no zone damage, so their killings can continue to remove squad
  members after the user chose to make squad bots immune to the zone.

**Latest result**

- `cal-immune-sub1.json`, 40 seeds:
  123 of 600 squad deaths were NPC, 34 gun, 13 laser. That is 20.5% NPC,
  5.7% gun, 2.2% laser of all squad slots.
- `cal-postfix-sub1-40.json`: 103 NPC / 33 gun / 9 laser squad deaths.
- `cal-postfix-s_base2-40.json`: 89 NPC / 29 gun / 7 laser / 3 lightning.
- One recorded immune-trace replay seed 2100025/slot 13 had sub1 die to squad
  gun at 35.95 s and 6 squad bots die to NPC 101/others early.

**Causality rule**

- `protocol.md §6 Events` distinguishes `damaged.by`, `weapon`, and `kill.target`.
- Local result JSON has `cause` and `killed_by`; it is not enough to call every
  NPC death an assisted bot kill. For score research:
  - **Direct kill:** bot's own `kill.target` event or `killed_by: bot`.
  - **Environment assist:** squad/NPC death caused by drone, zone, or other
    squad while the bot remained alive.
  - **No-goal benefit:** a death occurring after the bot dies has zero placement
    benefit for this match.
- The 56-seed s_base2 baseline gives 0.98 kills/match and a 131.15 s standard
  median death, while squad NPC deaths were 146/840 (17.4%). The ratio of our
  direct kills to later NPC-only removals must be retained in match reporting;
  current aggregate data does not prove that NPC pressure was caused by us.

**Action**

- Fight or bait drones only for short, visible returns: 350 HP and 25 damage
  are a poor exchange if they reset regeneration or pull hunters into line of
  sight. Never let a drone fight become an extra threat under hunter pressure.
- Taking a drone's 2 cubes is strong only if it is close and contest-free;
  cubes improve damage/HP as `×(1+0.04×min(cubes,10))` in
  `protocol.md §10`.
- The previous DRONE_AVOID 50 smoke reduced modeled drone deaths from about
  3.1 to 2.75 per match and recorded sub1 at 2.25 in only 4 matches, too weak
  a sample to recommend for real track use.

## 3. Kill causality and score

**Latest direct evidence**

- `cal-current-s_base2.json`, 40 seeds: s_base2 2.20, 1.05 kills/match,
  55.0% early deaths.
- `cal-postfix-s_base2-40.json`: s_base2 1.55, 0.85 kills/match,
  72.5% early deaths.
- `cal-postfix-sub1-40.json`: sub1 1.82, 0.88 kills/match,
  70.0% early deaths.
- `cal-postfix-example-40.json`: example 1.12, 0.38 kills/match,
  72.5% early deaths.
- The 56-seed s_base2 baseline: 2.00 ± 0.25, 0.98 kills/match, 48.2% early
  deaths. It was median at 131.15 s and lost mostly to guns (42) and lasers
  (12), plus one NPC and one zone.

**Inference**

- A 1.05 vs 0.38 kill difference did not imply a proportionate score in the
  example comparison: 2.20 vs 1.12 while early-death rates were 55.0% vs 72.5%.
- This supports the progress handover: survival of the first 120 s is the
  current dominant factor. Squad NPC deaths and squad combat deaths only remove
  enemies that could later outlast us; kills do not add placement directly.

## 4. Upgrades

**Evidence/config**

- `hello.json` has thresholds 1,3,6,10,15,21,28,36,45; protocol `§10` states
  offers queue for 5 s and unpicked choice 0 is applied.
- Plating: +15% max HP per stack, 1.15^3=1.521×.
- Armor: effective max health ×1.087/1.095/1.105 per stack and 0.76 damage
  multiplier full, but it does not reduce zone damage.
- Nanites: +60% regen and delay -1.5 s per stack.
- Gun damage/rate/velocity/mag are exact in `notes/research/upgrades.md`.
- Cubes heal the difference to the new max and add damage by 4% per cube up to
  a 10-cube cap.

**Priority**

1. Plating: only upgrade that expands the HP pool used in the 415 s HP tiebreak
   and against zone damage. The open question is whether it heals added HP;
   bot data must verify `self.hp/max_hp` after a plating event.
2. Nanites for a poke-and-heal bot, but behind plating and not useful outside
   zone or after 390 s.
3. Armor is a weapon-only defensive layer.
4. Gun rate/damage/velocity for direct duels; gun weapon upgrades are always
   offerable while the gun is held.
5. Laser damage/charge or lightning range/chain only after a real pickup and
   if the match plan uses that weapon.

**Endgame calculation**

- 1400 HP / 260 HP/s = 5.38 s after the zone closes.
- 3 plating stacks give 2129 HP = 8.19 s.
- 3 plating + 10 cubes gives 2981 HP = 11.46 s.
- The bot should therefore protect max HP and capture uninterrupted drops before
  phase 4 rather than chase small damage upgrades.

## 5. Weapon choices

**Evidence/config**

- `protocol.md §7 Weapons`:
  gun 45 damage, 252 m/s, 12 mag, 2.4 s reload;
  laser 315 full charge, 280 m, 0.75 s charge, 1.65 s cooldown;
  mortar 200 direct / 160 splash, 7 m;
  lightning 60 × three targets in 45 m / 30° cone, 0.25 s, 3 energy.
- Weapon triangle: lightning beats laser, mortar beats lightning, laser beats
  mortar, gun neutral.
- `notes/research/house-bots.md`: mech 10 was gun + laser, reacted in ~0.6 s,
  led targets ~0.023 rad, boosted/jet-hopped/juked, and got a laser within 5 s.
- `notes/research/stream.md`: at ~150 m, four full-charge lasers did 1260 damage;
  gun-only fighting at that range lost. LOS was decisive.

**Measured switch**

- The 56-match calibrated-squad `b_peek` laser defense was 1.96 ± 0.26 vs
  s_base2 2.00 ± 0.25, paired -0.20 ± 0.20. It had worse early-death rate
  (51.8% vs 48.2%) and fewer laser hits (1.04 vs 1.20/match), so current
  evidence does **not** support enabling it.
- AIM_PREDICT is supported by a unit result: moving-target hit rate rose
  0.20 to 0.40, but it has not yet been measured in the calibrated 56-match
  paired batch. It is the next low-risk combat test.
- Lightning ambush and a close-range laser peek remain unmeasured in the
  calibrated squad. Lightning is especially valuable against laser users because
  its short effect disables charging for 2 s; laser is valuable against
  mortars, and mortar handles lightning at range.

## 6. Turning environment assists into wins

1. **Control the first drone/NPC fight only if it creates cubes without
   exposing us to a hunter.** An uncontested drone can yield 2 cubes; with
   350 HP and 25 damage/s, it is safest to kite above 45 m and break LOS.
2. **Contest supply drops only when unobserved.** `protocol.md §7` gives 3
   cubes + full HP + full energy after 4 s alone, with drops at 70/140/210 s.
   A drop is best as a phase transition heal, not a fight objective. If another
   mech enters, leave because the capture clock freezes.
3. **Convert hunter mistakes into a direct kill.** House bots shoot back and
   expose their shooter with gun/laser sounds/beams
   (`protocol.md §2`, `§7/§8`). Break LOS to reset regen, face the
   attacker to avoid rear ×1.5 damage, and re-engage a low-HP or charging
   target only with cover.
4. **Use zone timing to force contested enemies to move.** Once the next circle
   is known, an inner/lower-exposure hold point with the zone behind the rear
   angle can turn enemy route pressure into rear-loss avoidance.
5. **Preserve HP to 415 s.** This is the clearest environment conversion:
   drones/crates/drops add cubes and HP, zone forces position, and every player
   is then fighting the same 260 HP/s collapse. Maximum HP at 415 s decides
   the HP tiebreak.

## 7. Ordered open questions / next evidence

1. Run calibrated 56-seed AIM_PREDICT against s_base2; target is at least
   +0.7 kills/match or a clearly lower early-death rate. Keep no other switch
   enabled.
2. Increase squad pressure (`DEFEND_RANGE 60→80` or earlier hunter schedule),
   but only after the bot A/B baseline is stable, because the latest calibration
   remains approximate and 56-seed noise is ±~0.25.
3. Record direct bot kills separately from NPC/zone/other-squad deaths in every
   full JSON/trace, including `kill.target` and `killed_by`.
4. Verify plating HP-heal semantics from a real/sim upgrade event.
5. Test lightning-first only after weapon-pickup and close-range cover logic
   exists; test with laser peek and aim prediction off first, otherwise effects
   will confound.
