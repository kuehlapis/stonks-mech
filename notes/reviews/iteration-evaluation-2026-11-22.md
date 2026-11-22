# Iteration evaluation — 2026-11-22

Critic review. Scope: `objective.md`, `notes/progress.md`,
`notes/decisions.md`, latest calibration reports, `b_peek` evidence,
and the `c_aim` rebuild. No bot behavior was edited and no match batch was
launched.

## Evidence read

The objective is mean placement score, not kills. The 56-match baseline and
calibration evidence are now the operative proxies:

- Completed 56-match baseline: `s_base2` 2.00 ± 0.25, 0.98 kills/match.
- `b_peek`: 1.96 ± 0.26; paired rerun difference -0.20 ± 0.20 points,
  -0.14 ± 0.14 kills/match, and early deaths 48.2% → 51.8%.
- `b_peek` received 58 laser hits, versus 67 in the paired rerun baseline
  (1.04 vs 1.20/match), but this did not offset worse early deaths or
  paired score loss.
- `c_aim` is rebuilt from `s_base2` with only
  `AIM_PREDICT=True`; normalized file diff is clean. Unit combat tests pass
  (18/18) and the full suite passed (93/93), but this is no match evidence.
- Authoritative current-squad 40-seed anchors: sub1 1.98 ± 0.29,
  s_base2 2.20 ± 0.29, example 1.40 ± 0.28. All have 0 pre-415 squad zone
  deaths and 0 act exceptions. Sub1 and s_base2 are both above the
  1.6 ± 0.2 calibration band, while example is not far below
  1.15 ± 0.2.

## Root-cause finding

The highest-impact loop change is **calibration before promotion**, with one
bounded pressure change. The track and current submitted baselines are not
yet reproduced on the authoritative squad model: sub1 and s_base2 each score
roughly 0.4–0.6 above the expected 1.6 band. Running laser or aim switches
against this model would test an overly permissive opponent and could
promote behavior for the wrong reason.

Raise one scalar, not a bundle: `sim/bots/squad.py` `DEFEND_RANGE` from 60 to
80 m. This was selected over moving the extra hunter trigger because it is
one knob, directly changes early pressure, and preserves the existing
schedule. Do not change ship behavior or add drone routing in this iteration.

### Why this outranks b_peek and c_aim

`b_peek` is already a complete rejection: it lacks a score or kill benefit and
raises early-death risk. Re-running it adds no decision value.

`c_aim` has the highest plausible bot-switch value of the currently queued
switches, but only in an isolated, valid simulator. A model-first calibration
change can invalidate or scale its measured effect. Therefore it follows
calibration, not a second competing model change.

## Next iteration gates

### Gate 1 — simulator validity

Run the following on the pressure-adjusted model, 40 seeds each,
`--seed 21 --rotate`, and do not overlap batches:

1. `sim/versions/sub1` — target 1.6 ± 0.2.
2. `sim/versions/s_base2` — target 1.6 ± 0.2.
3. `example_bot` — target 1.15 ± 0.2.

Validity is blocking:

- 0 squad zone deaths before 415 s.
- 0 candidate or squad act exceptions.
- 0 candidate/squad control runtime crash.
- Outside-zone target remains ≤2% for the candidate.
- Late answers remain below the current 2% check threshold.
- 40 raw match outputs retained and paired seed/range recorded.

If sub1 or s_base2 remains outside 1.6 ± 0.2 after DEFEND_RANGE=80, this
does not authorize a bot switch. One additional pressure correction is
allowed only after evidence: move the extra hunter from 150 s to 180 s
(reduce pressure) if both anchors remain too high, or 150→120 s (increase
pressure) only if all anchors remain too low. Do not make both correction
types in the same run.

### Gate 2 — baseline admission

Before an AIM A/B, complete a 56-match `s_base2` baseline on the calibrated
squad at `--seed 11 --rotate`. The baseline must preserve:

- 0 pre-415 squad zone deaths.
- 0 act exceptions.
- Outside-zone ≤2%.
- Rear-damage share ≤20%.
- Recorded score, kills, death-time, hit, weapon, and zone metrics.

Any model that fails validity or changes calibration anchors materially
invalidates prior `b_peek` and baseline comparisons.

### Gate 3 — c_aim promotion

`c_aim` may run only after Gate 2. It requires the exact isolated c_aim
snapshot and the following paired 56-match design:

- One candidate per match, `--seed 11 --rotate`.
- Baseline and candidate use identical squad seed range.
- No `PEEK_AFTER_BEAM`, `RUN_MODE`, `LADDER`, `STRAFE_BOOST_E`, economy,
  brain, survival, or combat changes beyond AIM_PREDICT.
- Report paired candidate-minus-baseline score SE, kills SE, early-death
  change, gun hit rate, laser hits, rear damage, outside-zone ticks,
  errors, late answers, pre-415 deaths, and timing.

Promote only for:

1. paired mean score ≥ +1.0 and kills/match ≥ +0.7, or
2. kills/match ≥ +0.7 plus early-death share ≥ 10 percentage points,
   with no mean-score or rear-damage regression.

All guardrails and validity gates remain blocking. Unit-test improvement
alone is not promotion evidence.

## Rejected and deferred

- Keep `PEEK_AFTER_BEAM=False`; no re-run.
- Do not stack c_aim with b_peek or any other switch.
- Do not launch a competing match batch.
- Defer DRONE_AVOID tuning, K1/K2 lightning or laser tactics, and moveset
  switches until a valid calibrated baseline and the c_aim decision exist.
- A one-lever change should be accepted or rejected before the next lever.
