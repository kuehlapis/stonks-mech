# FPS Elite Tactics — Mechfight Hypotheses (2026-11-22)

## Scope

TenZ/Shroud are used only as broad inspiration for elite FPS habits: controlled
pressure, precise aim, rapid cover use, information-led timing, and selective
fights. This document does not reproduce exact plays, VOD routes, quoted
commentary, or copyrighted sequences. No bot code or matches are proposed or
launched here.

The rule table comes from the repository's protocol and current evidence:
Mechfight is 10 decisions/s; walls and terrain block shots; mechs track enemies
for 5 s after sight; rear hits multiply damage by 1.5; guns lead; full laser
damage is 315 at 0.75 s charge; lightning is a 45 m cone weapon and shortens
laser hold by 2 s; NPC drones are 350 HP, shoot at 25 damage, and give 2 cubes;
supply drops require 4 s alone and three drops are called at 70/140/210 s
(`protocol.md` §§6–10). Repository measurements show 48.2% early deaths and
the last 56-match baseline at 2.00 ± 0.25 in one reported queue
(`notes/ideas/iteration-brainstorm-2026-11-22.md`).

## Evidence hypotheses

### H1 — Controlled peek/retreat reduces exposed hit time

**Hypothesis:** Reveal the mech for one short shot, break LOS immediately, and
re-enter from a different adjacent line rather than holding the same angle.
This should reduce rear and sustained incoming damage while preserving a first
shot.

**Protocol evidence:** shots resolve along actual torso aim, a gun mag leaves
12 shots, laser charging halves movement and creates a visible/near-sound
telegraph, and cover is defined by LOS.

**Module mapping:**
- `perception.py`: remember threatened/charging attackers and damage bearing.
- `nav.py`: steer to a reachable LOS-break point, not merely a farther point.
- `survival.py`: rank and cache the nearest cover point.
- `combat.py`: aim/lead and apply a strict 0.25–1.0 s first-shot window.
- `brain.py`: one peek, one trade, then `evade`/`flee`.

**Primary metric:** early deaths and rear-damage share. **Never-camp guard:** no
more than 3 s in one cover-adjacent firing lane before relocating.

### H2 — Crosshair pre-position lowers torso-slew loss

**Hypothesis:** Keep the torso on a likely approach corridor, sound bearing,
or last-known route instead of sweeping broadly after seeing the target.
Pre-aim should improve first-shot quality and reduce wasted reveal motion.

**Protocol evidence:** turns slew at config turn rate; every shot uses actual
torso aim; sound and beams provide bearings/paths; remembered mechs remain
trackable for 5 s.

**Module mapping:** `perception.py` supplies last-known position, beam origin,
sound bearing and threat age; `combat.py` blends direct/lead aim; `brain.py`
chooses when to scan or hold.

**Primary metric:** gun hit rate on moving targets at 50–150 m. **Anti-risk:**
pre-aim is bounded to one corridor and expires in 3 s.

### H3 — First-shot discipline avoids a weak opening

**Hypothesis:** Fire only with weapon/cover/range advantage and a valid firing
gate; if the opening is not favorable, break LOS or move first. This translates
elite restraint, not a claim that every fight must be won.

**Protocol evidence:** weapon triangle and reload/charge states are exposed;
gun spread and target movement make low-accuracy fire noisy; laser charge has
audible and visible telegraphs.

**Module mapping:** `combat.py` owns LOS, range, cooldown, lead and reload
gates; `perception.py` identifies weapon/charge/target count; `brain.py` owns
fight/evade hysteresis.

**Primary metric:** opening-hit share and damage taken in the first 1.5 s.

### H4 — Off-angle, short ambush holds use surprise without camping

**Hypothesis:** Let a hunter commit to the last-known route, then expose for
one lightning/laser/gun trade from an adjacent new angle and leave. This is
dynamic off-angle positioning, not map-corner camping.

**Protocol evidence:** movement is independent of torso, memory is 5 s,
lightning has a 45 m 30° cone, and LOS can be broken behind a wall or corner.

**Module mapping:** `perception.py` tracks arrival; `nav.py` chooses the adjacent
cover route; `survival.py` prohibits exposed holds; `combat.py` releases one
short trade; `brain.py` imposes a short timer and mandatory reposition.

**Primary metric:** damage dealt/received in re-entry plus hunters arriving
within 5 s.

### H5 — Sound/beam timing creates unpredictable re-engagement

**Hypothesis:** Use fresh sound, beam, and damage bearings to distinguish
real threats and re-enter on a bearing not aligned with the source. Timing
varies among cover points instead of a fixed peek cadence.

**Protocol evidence:** sound is age/bearing/distances, beams show shooter
paths, and damaged events include bearing and rear state.

**Module mapping:** `perception.py` is the only time/age/beam authority;
`survival.py` converts threat bearing to a face/cover choice; `nav.py` moves
through LOS; `combat.py` pre-aims only while brief and valid; `brain.py`
chooses one re-entry angle/window.

**Primary metric:** extra-hunter arrivals within 5 s and damage received per
confirmed re-entry.

### H6 — Zone/loot/drone support turns pressure into elimination

**Hypothesis:** The bot moves to the next zone early, takes uncontested drone
or supply support, and fights only isolated threats. Zone/drone effects are
force multipliers, not direct credit for kills.

**Protocol evidence:** zone and supply data are always known; supply capture
requires 4 s alone; drones shoot within 45 m/30 m home and give 2 cubes;
outside-zone regen stops and zone damage applies.

**Module mapping:** `survival.py` handles zone deadlines and center/corner
position; `economy.py` gates drops/cubes/drone farming; `perception.py`
requires no seen/remembered hunter nearby; `nav.py` escapes/rotates; `brain.py`
prioritizes zone safety unless the isolated trade passes.

**Primary metric:** time alive and direct vs assisted elimination count.

## Ranked six one-lever packages

Every package has exactly one lever. The candidate changes that lever only;
it does not bundle aim, economy, ambush and zone switches.

| Rank | Package / one lever | Why this rank | Primary metric | Module |
|---:|---|---|---|---|
| 1 | `COVER_PEEK_1S` — allow at most 1.0 s exposed, then require an LOS break and a non-identical return angle | Directly addresses 48.2% early deaths and rear/sustained damage without changing target or loot policy | early-death share; rear-damage share | `brain.py`, `survival.py`, `nav.py`, `combat.py` |
| 2 | `PREAIM_CORRIDOR_3S` — expire one corridor pre-aim after 3 s and restrict it to one sound/beam/last-known bearing | Improves first-shot quality with low switching risk | gun hit rate 50–150 m | `perception.py`, `combat.py`, `brain.py` |
| 3 | `FAVOR_VALID_FIRST_SHOT` — require cover, LOS/range, cooldown and low-risk target before any voluntary opening | Avoids the baseline's observable gun/laser dueling weakness | damage dealt/taken in first 1.5 s; opening-hit share | `combat.py`, `perception.py`, `brain.py` |
| 4 | `SHORT_AMBUSH_REENTRY` — wait behind new cover until a remembered threat arrives within 25 m, then one ≤2 s trade and mandatory relocate | Uses surprise without persistent hold or a fixed cadence | re-entry damage ratio; extra hunters within 5 s | `perception.py`, `nav.py`, `combat.py`, `survival.py`, `brain.py` |
| 5 | `INFO_TIMED_REPOSITION` — re-enter only after a fresh sound/beam/damage event and choose a different angle; no fixed peek rhythm | Makes timing variable and reduces predictable repeat peeks | damage received per re-entry; repeat-angle share | `perception.py`, `brain.py`, `nav.py` |
| 6 | `ZONE_DRONE_SUPPORT_GATE` — late loot/drone/drop action only while zone-safe and no hunter seen/remembered within the named radius; never use support as a camping reason | Potential late survival and resource gain, but lowest priority until early losses are controlled | alive at 300/375/415 s; assisted/direct removal separation | `survival.py`, `economy.py`, `perception.py`, `nav.py`, `brain.py` |

## 16-match screener gate

For every rank, run one isolated candidate against the current frozen baseline
with paired, rotated seed pairs and the same runner/ opponent pool. The
candidate changes no module except the package's one lever.

**Valid run:** 16 matches per arm, 0 act exceptions, 0 unbounded/late answers,
zero pre-415 squad zone deaths, and no guardrail failure.

**Promote to 56 matches** only if:

1. paired mean score is at least baseline +1.0; or
2. score is not below baseline by more than 0.5 and the package primary metric
   improves by at least 10 percentage points; and
3. early-death share does not worsen by 5 percentage points; mechanism metrics
   do not regress; no persistent camp appears.

**Reject immediately** if the valid-run mean is more than 0.5 below baseline,
early deaths rise by 5 percentage points or more, or the package's primary
metric regresses.

An inconclusive run remains off. Do not tune a second parameter from the same
16-match trace.

## 56-match confirmation gate

One promoted lever only. Run 56 paired, rotated matches against the frozen
baseline plus a separate adaptation pool. Ship only if:

- paired mean is at least baseline +0.4;
- early-death share is no more than 2 percentage points worse;
- the primary metric improves materially and its improvement is not explained
  entirely by a proxy/opponent artifact;
- 0 crash/guardrail regressions;
- no increased pre-415 zone death or repeated camping remains; and
- direct, NPC-assisted, zone-assisted and drone-assisted removals are reported
  separately.

A failed 56-match confirmation rejects the lever and it must not be stacked or
re-run unchanged.

## Anti-overfit rules

1. **One lever at a time.** A package must show a single named input and one
   primary metric. Never stack packages within a run.
2. **Freeze the baseline.** Save normalized source snapshots and verify that the
   only diff is the package's switch/constant.
3. **Paired and rotated seeds.** The same seeds are paired with arm order
   rotated; report paired mean and uncertainty, not just the arm mean.
4. **Do not chase one map or trace.** Use an opponent pool containing passive
   looters, aggressive hunters, campers, drone-aware, laser/lightning/gun
   styles, and past bot copies. A 10-point improvement in one exact seed is not
   promotion evidence.
5. **Predefine horizons and metrics.** Declare the 16/56 gate before running.
   Do not change the metric after losses or post-hoc select a favorable slice.
   Report deaths in `<120`, `120–300`, `300–415`, and `>415 s` buckets.
6. **No camp/cadence fitting.** Reject a strategy if it stays at one corner,
   repeats one peek rhythm, or holds exposed territory for a fixed timer.
   Hold points must move with the zone and threat state.
7. **Separate mechanisms.** Do not attribute zone, drone or NPC deaths to direct
   bot aim. Count direct kills, NPC-assisted removals, zone-assisted removals,
   and placement outcomes independently.
8. **Reset search state.** Reject remembering an adversary's exact future
   route, tuning constants to a replay, or optimizing for a known opponent id.
   Legitimate state is only sound/beam/damage/vision information in protocol
   observations.
9. **Track guardrails.** Proxy gain does not ship if mean score drops by more
   than 0.5, early deaths rise, or act time/late-answer/memory/build limits
   regress.
10. **Never hide.** No package is allowed to win by passive holding. Cover is
    used to set up a short trade or break LOS, then the bot rotates.
