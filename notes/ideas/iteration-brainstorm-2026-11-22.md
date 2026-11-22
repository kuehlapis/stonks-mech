# Ranked strategy queue — 16-match screeners (2026-11-22)

## Evidence and test contract

The calibrated `s_base2` baseline is **2.00 ± 0.25** over 56 matches, with
0.98 direct kills/match, 48.2% of deaths before 120 s, 10.1% rear damage,
and 0.34% outside-zone ticks. The queue is strategy-only: no matches or bot
files are changed by this document. Squad deaths caused by the zone are not
counted as a strategy benefit; report direct, NPC-assisted, and other/NPC
removals separately.

Every screener changes exactly **one lever** from the baseline. Run 16 paired,
rotated matches with the same seed and runner settings as the recorded
baseline. The candidate must have zero act errors and late answers, no new
pre-415 squad zone deaths, and no guardrail failure. Reject a candidate if
its mean score is more than 0.5 below baseline, early deaths increase by
5 percentage points or more, or its primary mechanism metric regresses.
Otherwise it is only *inconclusive*, not promoted.

Promote a screener to 56 matches only when it clears the screener bar:
mean score at least **baseline + 1.0**, or mean score at least baseline with
an improvement of at least **10 percentage points** in the package's primary
metric and no score loss greater than 0.5. Run the promoted package alone
for 56 paired, rotated matches. Ship only if the 56-match paired mean is at
least **baseline + 0.4**, with no guardrail regression and no more than
2 percentage points worse early-death share. A failed 56-match confirmation
rejects the lever and it must not be stacked.

## Ranked queue

### 1. Cover/LOS gate — `COVER_FIRST`

**One lever:** before any voluntary mech attack, require a reachable wall,
corner, roof edge, or terrain LOS break within 35 m; if none exists, move to
cover or the next-zone hold point instead of opening fire. While engaged,
break LOS after 2.0 s without a confirmed hit and relocate 60–100 m.

**Screening package:** `COVER_FIRST` only; keep weapon choice, target choice,
and zone logic unchanged. Primary metric is early deaths (<120 s), with
laser hits and rear-damage share as secondary metrics. This is ranked first
because gun deaths are 42/56 and early deaths are the dominant floor.

**Removal accounting:** direct mech kills only. A safer position is not a
kill; report direct kills separately from NPC-assisted removals.

### 2. Weakest-first ladder — `HUNTER_LADDER`

**One lever:** permit at most two early isolated targets, selecting the
weakest visible gun-only or low-HP hunter; after two confirmed direct kills,
or at 150 s, stop hunting and rotate/regen. Never start a fight against two
or more visible hunters or a charging laser holder in the open.

**Screening package:** `HUNTER_LADDER` only, with the existing cover and aim
behavior unchanged. Primary metric is direct kills by 150 s without an
increase in early deaths; also record group size at first engagement and
deaths by weapon.

**Removal accounting:** direct mech kills are valid. Do not credit cubes,
NPC deaths, or zone deaths as ladder kills.

### 3. Surprise re-engagement — `SURPRISE_REENGAGE`

**One lever:** after breaking LOS from a remembered attacker, wait behind a
cover point until the attacker is within 25 m of its last position, then
make one short re-engagement (one laser release or up to 2.0 s of gunfire)
from a new angle and immediately relocate. Do not repeat the same corner.

**Screening package:** `SURPRISE_REENGAGE` only; no altered weapon pickup or
laser-peek behavior. Primary metric is damage dealt in the first re-entry
versus damage received, plus early deaths and extra hunters arriving within
5 s.

**Removal accounting:** direct damage/kills only. A remembered position is
not proof that the attacker is alone.

### 4. Supply discipline — `SUPPLY_GATE`

**One lever:** capture a landed supply drop only when no enemy has been seen
or remembered within 80 m for 10 s; stand for the normal 4 s capture, then
leave the ring immediately. If the gate fails, skip the drop and continue
zone travel.

**Screening package:** `SUPPLY_GATE` only; no route, upgrade, or combat
change. Primary metric is uncontested captures (target ≥80%), with deaths
within 20 s of capture and HP/energy after capture as safety checks. The
600 m landing sound makes camping the drop unacceptable.

**Removal accounting:** no removal is attributed to the drop. Report any
direct or NPC-assisted deaths separately.

### 5. Drone/ambush pressure — `DRONE_AMBUSH`

**One lever:** attack a drone only when its home/target area has no hunter
seen or remembered within 45 m; keep the drone between the bot and the
approach for at most 5 s, then break LOS and collect cubes only if safe.
Never use a drone as a reason to hold an exposed position.

**Screening package:** `DRONE_AMBUSH` only; do not change drone routing,
weapon priority, or general ambush behavior. Primary metric is NPC-assisted
damage/removals per early death, with drone damage taken, hunters within
45 m, cubes gained, and direct kills recorded.

**Removal accounting:** label direct mech kills, NPC-assisted mech deaths,
and drone/crate deaths as separate counters. Drone damage is support, not a
direct kill claim.

### 6. Final-burn preparation — `FINAL_BURN`

**One lever:** once the bot reaches 300 s, stop discretionary looting and
rotate to a final-circle cover/high-ground point; spend remaining safe time
on HP/energy and face the nearest threat. At the 415 s collapse, hold the
point and fight only to prevent rear damage or finish an already weakened
mech.

**Screening package:** `FINAL_BURN` only; no early-fight or supply changes.
Primary metric is share alive at 300/375/415 s and HP at 415 s, followed by
placement. This is last because the baseline median death is about 131 s;
it cannot help a bot that never reaches the endgame.

**Removal accounting:** direct kills and NPC-assisted deaths remain separate;
the final zone is never credited as an opponent removal.

## Execution order

Screen in the order above and stop after the first rejection only if the
rejection is a guardrail failure; otherwise continue all six. Promote at
most one lever at a time to the 56-match confirmation. Do not stack a second
lever until the first has passed confirmation. A screener with no score
gain but a metric gain is not a winner until its 56-match score clears the
ship bar.

## Mandatory 16/56 post-run rule

This queue is now subordinate to the match-run counterstrategy gate in
`CLAUDE.md`. After any 16-match screen or 56-match confirmation, classify
both wins and deaths before selecting a replan:

- Wins: placement/HP win, direct mech kills, NPC/drone-assisted removals,
  zone-assisted removals, and final-burn survival.
- Deaths: cause, time phase, cover/LOS state, zone pressure, squad/hunter
  count, surprise-window state, and rear/exposed state.

Then name the single strongest counterstrategy supported by those numbers:
prefer a surprise re-entry, cover/LOS break, short ambush, better zone route,
safer drone interaction or routing, or isolated squad-hunting adaptation.
Finally build exactly one corrective package for that counterstrategy. The
package must have one hypothesis, one primary metric, guardrails, a 16-match
or 56-match contract, and an explicit rejection/promotion bar. Do not build
or launch a second package for the same run, do not stack it with another
unconfirmed package, and do not re-run an already rejected idea unchanged.
