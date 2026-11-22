# Maximum-hard-but-probably-valid squad model

Date: 2026-11-22  
Status: design proposal only. No `sim/bots/squad.py` edit and no match batch
has been authorized or run.

## Objective and evidence

This model is not a claim that every tuned value is recorded. It is the hardest
single-squad model that can still be defended from the protocol and from the
evidence already collected:

- Track: 15 house bots act as one squad, share vision, never fight each other,
  and hunt the player. The exact proportions are 4 easy, 4 medium, 4 hard,
  3 expert.
- Protocol: shots, zone, NPC, upgrades and world data come from `hello.config`;
  user rule: squad slots take no zone damage.
- Recorded FFA evidence: one observed bot reacted from a hit in about 0.6 s,
  led ~0.023 rad, opened later with full-charge lasers, boosted at 19.4 m/s,
  jet-hopped, juked every 0.3–0.6 s and kept attacking for at least 31 s.
  It was FFA and not known to be a house bot, so this is supporting evidence,
  not squad calibration.
- Existing calibration: current post-fix squad.py has zero pre-415 squad zone
  deaths and exceptions in the 40-seed anchors, but whether 60 m defender
  pressure is too high or low is unsettled: post-fix anchors give sub1
  1.82 ± 0.27, s_base2 1.55 ± 0.26 and example 1.12 ± 0.22; an authoritative
  seed-21 rerun gives sub1 1.98 ± 0.29 and s_base2 2.20 ± 0.29.
  DEFEND_RANGE therefore needs a controlled 60/80/100 sensitivity sweep.

## Maximum-hard AOE grouping hypothesis

Status: design only; no model edit or match launch authorized.

The strongest defensible cooperative behavior is to make the squad converge
and deliberately overlap mortar/lightning/laser effects around the player,
instead of relying only on isolated gun trades. When a candidate, NPC, or
valid AOE target is inside the same effect, the squad may use splash or chain
opportunity for support damage. This is a behavior model, not a damage
multiplier.

### Evidence for the hypothesis

- `protocol.md` and `hello.config` provide 16-mech FFA, two weapon slots,
  LOS/cover, shared enemy observations, mortar, laser, lightning, NPC, and
  zone rules. No hidden-squad feature or wall-penetrating telemetry exists.
- `notes/research/house-bots.md`: one observed bot reacted in about 0.6 s,
  led at about 0.023 rad, boosted at 19.4 m/s, jet-hopped, juked every
  0.3–0.6 s, and kept chase/re-entry for at least 31 s. It supports hard-tier
  aim and movement; it does not prove house-bot coordination.
- Engine evidence: `sim/engine.py` implements mortar direct/splash/concussion,
  full-charge linear laser damage/cookoff, and lightning 30° cone plus two
  chain jumps. The live config supplies all ranges and cooldowns.
- Map evidence: `arena/v2/world.json` plus terrain have 77% open ground,
  22.8% building/stadium footprint, 1,560 trees, and 244 of 250 roofs
  reachable to 49.5 m. Long crossfire and building LOS breaks are both valid;
  four-sector crossfire can be represented geometrically.
- Existing anchors: post-fix 40-seed sub1 1.82 ±0.27, s_base2 1.55 ±0.26,
  example 1.12 ±0.22, with zero squad zone deaths before 415 s.

### Shared and timing constants

| Constant | Exact value | Basis |
|---|---:|---|
| Shared target age | 30 s | Maximum-hard proposal; normal mech track remains `vision.memory_s` |
| Mortar interception | 2 s prediction | Test constant; projection stops after 2 s |
| V1 inner ring | 25 m | Below `vision.near_range` 45 m; keeps a lightning opportunity |
| V1 outer ring | 45 m | `vision.near_range` and lightning `range` in live config |
| V1 sectors | 72° nominal, 5 active positions | One point around a ring |
| V1 tangential offset | 8–12 m every 1 s | Map-spacing tactic, not a damage rule |
| V2 sectors | 0°, 90°, 180°, 270° | Four angular crossfire sectors |
| V2 stagger | 0.00, 0.35, 0.70, 1.05 s | Tactic constants |
| V2 exposure | 1.5 s | Short LOS exposure |
| Hunter zigs | 0.3–0.6 s reversal | Recorded FFA movement evidence |
| Reaction floor | 31 s retaliation | Recorded minimum observed continuity |
| Stale target | reject after 30 s | Never infer current position beyond the shared age |

Any weapon radius, damage, charge, splash, chain, energy, or cooldown used by
an implementation must come from live `hello.config`. Only these sector,
timing, and ring constants are test-model choices.

### Variant 1: convergent AOE grouping

Rank **1** as the primary experiment.

1. Three to five hunters select the youngest/closest shared target and enter
   a 25–45 m ring around the player.
2. They occupy 72-degree sectors, then retain 8 m center separation where
   terrain permits. They tangentially offset 8–12 m every 1 s.
3. Aim at the player COM: feet plus 50% of live mech height. Mortar lead is
   bounded to 2 s of velocity projection.
4. Fire priority:
   - mortar when a splash/center LOS opportunity exists;
   - lightning in the live 30-degree cone within live 45 m range, candidate
     target first and chain to up to two live targets;
   - full-charge laser only after clear LOS;
   - gun only while another AOE/laser effect is not improving.
5. If LOS breaks for 1 s, the player remains a 30 s shared-memory pursuit
   target; hunters may reach the newest remembered position but may not fire
   through a wall or aim at a stale exact position.
6. Zone escape is absolute: convergence, ring, and V1 offsets stop while
   the zone goal or margin is active.

**Why it may win:** overlapping mortar splash, lightning chaining/control,
and laser/cookoff damage attack cover, position, and reaction at once.

**Failure risks:** wall wedges; own mortar splash; crowding and overlap;
stale-memory omniscience; overstatement of mortar/laser assumptions;
nav/terrain not modeling actual roof edges; a cover player can cancel all
three effects by alternating 1 s LOS breaks.

### Variant 2: one-point crossfire with staggered exposure

Rank **2** as the isolated follow-up.

1. Name one point, the player's live COM, and use four angular sectors:
   0°, 90°, 180°, and 270° around that point.
2. Stagger sector exposure at 0.00, 0.35, 0.70, and 1.05 s. No sector has
   more than one active hunter.
3. Exposed hunters hold LOS for at most 1.5 s, make one AOE/laser release or
   a short gun window, then move 8–12 m to cover.
4. Apply the same mortar, lightning, and laser priority as V1. AOE may be
   used against a cluster of NPC/valid targets; it is not reserved for the
   player only.
5. Non-exposed hunters avoid crossing the player's front 180-degree arc when
   geometry permits. They stop for zone routing and never hold a crossfire
   lane outside the next circle.

**Why it may win:** staggered firing reduces simultaneous exposure and can
force a candidate to choose a side while the next angle arrives.

**Failure risks:** fixed sectors become predictable; 0.35 s gaps are too slow
to beat cover peeks; wall geometry can create one mutual LOS lane instead of
four angles; rear protection/facing can delete the advantage; if only the
first sector damages, V2 degenerates to ordinary pursuit.

### Direct/assisted kill attribution

Keep candidate and squad removals separate.

| Class | Exact rule |
|---|---|
| Candidate direct squad kill | Candidate's `hit`/`kill` event is the final damaging source within 1.0 s of the squad target's removal |
| Candidate assisted squad removal | Candidate dealt >=20% of the target max HP in 5 s and NPC/drone/zone/unknown is the final removal source |
| Squad direct candidate kill | Candidate's final HP-loss event has `by` equal to a squad member and that event is the last damage source |
| Squad assisted candidate removal | One squad member dealt >=20% of candidate max HP in 5 s, while final removal is zone/NPC/drone/unknown |
| Group-assisted candidate removal | 2+ squad members damage in 5 s and one lands the final blow: the final source is direct; other squad sources are assisted |
| NPC/drone/zone removal | Final `weapon` is `npc` or `zone`, or the source id is a drone/NPC; never direct mech kill |
| Unknown | No traceable final source or damage window; never infer attribution |

The same output retains final source, by id, weapon, tier, 5 s damage shares,
and whether the last hit was rear.

### 16/56 match gates

**Validity gate (before every 16 or 56 batch):** zero pre-415 squad zone
deaths, zero act exceptions, conformance/late-answer guardrail pass, direct/
assisted fields complete, no memory age >30 s, no hidden LOS, and no convergence
or crossfire override of the zone margin. Any failure rejects the batch.

**16-match seed-11, paired, rotated screener**

- Promote V1/V2 to 56 if paired placement mean is baseline +1.0 or more, or
  the mean is not below baseline and a primary AOE metric improves >=10
  percentage points with mean loss <=0.5.
- Inconclusive if paired placement difference is <1.0 and no AOE threshold
  is met.
- Reject if mean is >0.5 below baseline, early deaths rise >=5 percentage
  points, or any validity gate fails.
- V1 primary: 2+ hunter convergence within 5 s, mortar/lightning/laser hits,
  and stale-target share.
- V2 primary: crossfire exposure-to-hit ratio, rear-hit share, LOS-break time,
  staggered-fire count, and 5 s group damage.

**56-match seed-11, paired, rotated confirmation**

- Paired placement mean baseline +0.4 or better.
- Win rate not worse by >5 percentage points.
- Early-death share no worse by >2 percentage points.
- Report paired SE and never stack V1 and V2 in one run.
- Preserve the validity gate and separate direct, assisted, NPC/drone, zone,
  and unknown removals.

### Validity against the current map and engine

Valid as a simulator model: current engine has mortar splash/concussion,
laser hitscan/cookoff, and lightning cone/chaining; live config supplies
weapon values; the map has both open and dense LOS sectors.

Not valid for launch until a model implementation, exact trace, and explicit
moderator release exist. Roof routing, exact next-circle timing, mortar
assumptions, and complete wall/ledge behavior are incomplete or assumed.
No code or match is authorized by this document.

## Central design

The squad shares one `seen` table per match. A member reports a visible mech
position, velocity and HP with a sight timestamp. The table is truncated to
**30.0 s**: no member may hunt a target older than 30 s. A target position may
be projected along velocity only for a short, bounded intercept window (at
most 3 s); a stale target is never treated as current position.

Shared vision is not extra wall penetration or omniscience. It only merges
what squad members actually observe. A gun hit event may post a bearing guess
to the registry, but it does not create a position in the absence of LOS.
Damage sources and beams expose the shooter in the protocol; sound-only
reaction remains disabled in the default model because the recording gives weak
and contradictory evidence for it.

## Exact tier model

Keep the existing tier order and aim profile exactly:

| Tier | Squad count | Aim sd (rad) | Lead factor | Reaction (s) | Strafe | Laser/crate/NPC policy |
|---|---:|---:|---:|---:|---|---|
| easy | 4 | 0.060 | 0.0 | 0.8 | off | no laser, no farm |
| medium | 4 | 0.030 | 0.6 | 0.5 | off | laser, crate/NPC farm |
| hard | 4 | 0.015 | 0.9 | 0.3 | on | laser, farm |
| expert | 3 | 0.008 | 1.0 | 0.2 | on | laser, farm |

The implementation's AR(1) aim error may remain; when added in code it is
`0.8 * prior + 0.2 * gauss(0, 2.2 * tier_noise)`. That steady-state error is
approximately 0.73 times the listed noise.

## Pressure schedule

Hunter count is:

1. Start with 1 hunter.
2. Add 1 hunter for every squad mech removed.
3. At `t > 150 s`, add 1 more hunter.
4. At `t > 240 s`, add 2 more hunters.
5. At `t >= 300 s`, all currently alive squad members are hunters.

This is the current guess and exact schedule. It is staggered enough to allow
early isolated fights but remains a maximum-hard late-game model.

The exact defense sensitivity arms are:

| Arm | `DEFEND_RANGE` | Meaning |
|---|---:|---|
| D60 | 60 m | current calibrated model; lightest non-hunter pressure |
| D80 | 80 m | next intermediate pressure; exactly the smallest requested raise |
| D100 | 100 m | maximum plausible visible-defender range for the first sweep |

Order: run D60 first as a pair against the completed baseline, then D80, then
D100. Do not combine pressure changes with mobility, memory or hunter-schedule
changes. The first arm that breaches the calibration band or validity floor
can be stopped. D100 is a test upper bound, not a presumed winning setting.

A hunter always pursues the youngest shared target in range and otherwise
retaliates for 30 s by the existing `RETALIATE_S`; the evidence-based lower
bound is 31 s, so a future change may use `RETALIATE_S=31.0`, never more than
31.0 unless a new trace supports it.

## Mobility

Required behavior for each eligible hunter:

- Zigzag with exact 0.3–0.6 s reversal intervals.
- Boost toward a target more than 40 m away while energy exceeds 30, using
  config values for `boost_speed` and energy consumption.
- Jump and jet-hop to preserve closing ability or break LOS. Jet duration,
  rise, energy and grounded state use `hello.config`; do not invent fixed
  rise/fall constants outside the config.
- When stuck for more than 0.3 s, slide sideways and flip side every 4 s.
- When stuck for more than 0.5 s while grounded, jump.
- After 3 s stuck, discard and recompute the goal.
- Suppress stuck/side-slide overrides when a zone escape is active.

This is full boost/zigzag/jet at the model level. It does not give every bot
literal rooftop navigation: world/LOS-aware roof routing remains an engine
assumption until its own code and trace evidence exist.

## Vision and close-terrain behavior

Shared vision uses the actual visible-mech list. It may not add LOS seen by
the enemy, so split tree/building LOS remains a valid break.

Target selection for a hunter uses the youngest or closest shared target only
from the 30 s table. Non-hunters:

- defend only visible targets inside `DEFEND_RANGE`;
- use weak laser/crate/NPC preference by tier;
- hold a next-ring goal;
- never start an exposed pursuit outside the zone.

## Zone rules

Zone behavior is a validity rule, not a pressure knob:

- `ZONE_SMART=True`.
- Squad bots stay inside the next circle, with a 15 m center-margin goal.
- A goal outside the next circle is clamped inward.
- While the final radius is 25 m or less, non-hunters stop discretionary fights
  and hold/regen if below max HP.
- At `t > shrink_start - 10 s` and outside the margin, boost toward the centre.
- Exact user rule: squad bots take no zone damage; in-engine zone immunity is
  a match rule and must make the pre-415 squad zone-death count exactly zero.
- Preserve direct centre-directed movement during zone exits; do not allow a
  wall-side slide to override the next-circle pull.
- Zone removal must never be credited as a squad bot kill or assisted
  elimination. It is only a placement event and a final-burn safety metric.

If a wall or exact-centre degeneracy occurs, fail safe: move directly to
`next_center`, boost once if permitted and do not send a zero-length vector.

## NPC and drone rules

NPC behavior remains config-driven. The model is to route around known drone
homes while in-zone and to treat an NPC that hits a squad member as a possible
source only, not as shared mech vision:

- Home location is the first sight position, not a continuously perfect track.
- Drones are avoided within 50 m; goals within 50 m of a known home are
  rejected up to 10 random samples.
- Push direction away from an NPC when inside 50 m, while preserving the zone
  exit priority.
- NPC damage or drone firing is attributed as `npc_assisted`, `drone_assisted`
  or `npc_damage`; it is never added to `direct_kills`.
- A squad bot may farm NPC/crates/cubes only if medium/hard/expert and not
  currently hunting. Farm range remains a tight 50 m goal range.
- The candidate bot may use a drone as cover or lure only in a separate
  measured strategy package, and never at the cost of exposing it outside the
  zone or opening a rear.

## Weapon and upgrade behavior

Maximum-hard behavior should use the existing engine, but it must not invent
weapon stats:

- Easy bots: gun only until they loot an allowed higher-tier weapon.
- Medium and above: prefer laser; hard/expert react faster and lead harder.
- Gun aim: intercept a target with gun projectile speed and lead factor.
- Laser: hold charge until a clear LOS; release at full charge.
- Lightning: fire near 45 m within a 30° cone, if the bot currently holds it,
  and use config cooldown/energy values.
- Upgrade preference remains the existing fixed order:
  plating, gun damage, laser damage, gun rate, armor, laser charge, nanites,
  gun velocity.

## Failure-learning metrics

Every match report must retain or add these fields:

1. Placement, score, win/top3 and HP at 300/375/415 s.
2. Direct mech kills by the candidate, NPC-assisted squad removals,
   drone-assisted squad removals, zone removals and `other` removals.
3. Candidate death cause: gun, laser, lightning, NPC/drone, zone or unknown.
4. Candidate death `killed_by` slot and squad tier.
5. First visible hunter count, first engagement size and first damage range.
6. Each target's memory age at pursuit: 0–30 s, bucketed by 5 s.
7. Stale-target share and stale-target death share.
8. Rear-damage share and rear-hit count.
9. Time outside the current and next zone circles.
10. Pre-415 squad zone deaths: must be zero.
11. Act exceptions and serialized-answer late answers.
12. Per-tick mean/p99/max decision time.
13. Boost distance/time, jet-hop count and vertical gain, strafe reversal count,
   LOS-break duration and re-engagement duration.
14. Laser charges, beams, beam hits, gun shots/hits and lightning shots/hits.
15. NPC/drone events that damage a squad member or candidate, with attribution.

## Per-failure root-cause taxonomy

One death row must classify only one primary root cause, with secondary flags:

| Root cause | Required evidence |
|---|---|
| no-cover death | LOS/cover break was absent for 2 s before first damage |
| pack convergence | 2+ hunters damaged within 5 s |
| laser-alpha | first beam removed ≥20% HP in an unanswered opening |
| gun-lead | no laser; gun hit/shot ratio and 50–150 m lead residual |
| rear exposure | rear-hit share >50% for the death interval |
| stale-memory chase | all pursuing slots used a target older than 30 s |
| nav/stuck | stuck >0.5 s, repeated position, wall wedge or zone override |
| zone routing | outside-zone ticks exceed 2% or margin goal/phase mismatch |
| NPC/drone assist | NPC/drone event was causal and mech damage is secondary |
| final-burn HP | death occurs at 415 s+ and HP/placement decides it |

No root-cause row may be invented from a summary. A trace is required for
nav/stuck, rear, laser-alpha and stale-memory classifications.

## Improvement loop and acceptance gates

1. Run only the 60/80/100 pressure sensitivity matrix after the model is
   implemented. Each arm uses the same 40 seeds, anchor set and opponent order.
2. Reject immediately if there is any pre-415 squad zone death, any act
   exception or a conformance/late-answer guardrail failure.
3. Calibrate against sub1 1.6 ± 0.2, s_base2 1.6 ± 0.2 and example
   1.15 ± 0.2. Values outside ±0.2 are still useful only if they preserve
   validity and explain a consistent rank-order effect.
4. Rank a candidate pressure arm by paired anchor score delta, not its raw
   squad score. The goal is realism and discriminating behavior, not the
   highest possible squad score.
5. After one pressure arm is chosen, add one bot behavior or one switch at a
   time. Keep direct/assisted kills separate. A switch is promoted only after
   a paired confirmation clears score and safety gates.
6. Every failed run produces one AAR replan row naming the failure bucket,
   evidence, expected effect and next smallest experiment.

## Explicit exclusions

This proposal does not:

- enable wall, roof or enemy telemetry that does not exist in observations;
- expand memory beyond 30 s;
- make non-hunters attack outside their defense range;
- count NPC, drone or zone removals as direct kills;
- change shipped `python/` bot behavior;
- launch a match or claim calibration success without evidence.
