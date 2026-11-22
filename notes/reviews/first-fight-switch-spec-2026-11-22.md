# Review: first-fight switches specification

Critic, 2026-11-22. Scope: turn round-2 first-fight findings into exactly two
off-default experimental switches. No bot code was changed.

## Switch A — conservative gun-only opening

**Purpose.** Stop treating weapon inventory `['gun']` as proof that the enemy is
an easy tier, and require a real time-to-kill edge before voluntarily revealing
our position with gunfire.

**Location.** `python/brain.py`: constants at lines 25–26, `_ttk_ratio` at
lines 575–596, and the voluntary `"open"` branch at lines 355–366.

**Smallest design.** Add one boolean, default `False`, for example
`CONSERVATIVE_OPEN = False`.  When it is true only:

- calculate gun-only enemy DPS with multiplier **1.0**, rather than the current
  `WEAK_GUN = 0.6`, in `_ttk_ratio` (and match the same multiplier in
  `_group_target`, lines 608–614, so two decision paths do not disagree);
- use an open threshold of **0.8**, rather than `OPEN_EDGE = 1.2`, in the
  `"open"` branch.

Do not alter the existing default constants or the `finish`, return-fire, or
cornered branches. This makes the experiment solely about initiating a fight;
it must still fight when already engaged.

**Why.** Every mech initially has only a gun, while the observed house bot
picked up a laser by 4.9 s. The current branch can open at 180 m when our
estimated kill time is up to 1.2 times theirs, after reducing its gun DPS by
40%; the gun sound is audible to the squad. This is an inventory/tier inference,
not a measured strength signal.

## Switch B — laser-aware range policy

**Purpose.** Avoid choosing the generic 130 m gun-fight distance against an
enemy laser that we do not hold ourselves.

**Location.** `python/brain.py`: constant block near lines 13–80;
`_fight` lines 728–737; `_range_pref` lines 739–753. `LASER_DUCK` remains a
separate existing switch and is not changed by this experiment.

**Smallest design.** Add one boolean, default `False`, for example
`LASER_RANGE_POLICY = False`. When it is true, in `_range_pref` after the two
lightning clauses and before the generic `FIGHT_RANGE` clause:

- if `laser in theirs` and `laser not in mine`, return the same bounded close
  command that targets **50 m** (equivalent to using a local fight target of
  50 m); otherwise leave the existing path unchanged.

Keep the policy to movement range only. Do not add a cover search, a new
mode, or a fire restriction in this switch: `_fight` already handles an
engaged target and its existing `LASER_DUCK` path can be paired later in a
separate test. The close command is intentionally bounded by the existing
`[-0.6, 0.8]` movement scale.

**Why.** The generic policy kites to `FIGHT_RANGE = 130` regardless of weapon
matchup. At 60–150 m `_dps` assumes a 35% gun hit probability and an 85% laser
hit probability; recorded house-bot lasers landed about 4/5 at 100–150 m.
At close range, strafing and cover have a plausible chance to reduce the laser
advantage without changing fire initiation.

## Measurement and guardrails

Build each flag separately and off by default. After simulator calibration,
run each versus the calibrated baseline on paired seeds (at least 56 matches);
report score, kills/match, deaths before 120 s, laser hits received, and
paired-difference SE. Do not stack them unless each clears the predeclared
effect bar (at least +0.7 kills/match or a meaningful survival improvement).
Run the Python unit suite and conformance/timing check before any commit.

## Explicitly deferred

`_ttk_ratio` is still one-on-one and averages laser alpha damage over its full
cycle. A remembered-enemy danger gate and alpha-risk term are valid follow-up
ideas, but they are not part of either switch: adding them would confound the
two requested A/Bs.
