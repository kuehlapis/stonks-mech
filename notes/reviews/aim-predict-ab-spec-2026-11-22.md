# Review: AIM_PREDICT isolated A/B specification

Critic, 2026-11-22. This is a review-only handover; no bot file was edited
and no simulator batch was started.

## Verdict

The existing `sim/versions/c_aim/` snapshot is **not valid** for this A/B.
It is not an isolated copy of `sim/versions/s_base2/`: normalized diffs show
extra changes in `brain.py` and `economy.py`, and it lacks the current
s_base2 `RUN_HIT_S` fixes. It must not be used for a measurement.

The exact candidate is `s_base2` with only:

```python
AIM_PREDICT = True
```

in `python/combat.py` / the candidate's `combat.py`. Keep these defaults
unchanged in the candidate:

- `HIT_GATE = 0.25`
- `PREDICT_WINDOW_S = 1.0`
- `AIM_TOL_FRAC = 0.6`
- `MIN_TOL = 0.004`
- `LOW_AMMO_FRAC = 0.5`

Do not alter mortar aim, reload, laser charge release, `FIRE_POLICY`,
`RUN_MODE`, `RUN_HIT_S`, `LADDER`, `CUBE_CAP`, economy, navigation, perception,
survival, or brain. The existing candidate directory must be replaced or
rebuilt as a copy of `sim/versions/s_base2/`; only `AIM_PREDICT` may differ.
Because this spec requires isolation, that rebuild is the Builder's first
bounded step and must be reviewed by a normalized file diff before a run.

## Exact paired design

Baseline:

```sh
python sim/inproc.py --bot s_base2=sim/versions/s_base2/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 56 --jobs 4 --seed 11 --rotate --out notes/tests/cal-aim-off-2026-11-22.json
```

Candidate, after isolation is verified:

```sh
python sim/inproc.py --bot c_aim=sim/versions/c_aim/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 56 --jobs 4 --seed 11 --rotate --out notes/tests/cal-aim-on-2026-11-22.json
```

Use the same seed range and `--rotate` in both runs. Do not place baseline and
candidate as separate mechs in the same match. Do not stack any laser-defense
A/B switch or another combat switch. Run only `c_aim` while the requested
laser-defense A/B remains running and do not start a competing batch.

## Predeclared metrics

Report, per bot, with paired candidate-minus-baseline differences:

1. Mean placement score and paired SE.
2. Kills/match and paired-difference SE.
3. Median and <120 s death share.
4. Gun hit rate on moving targets 50–150 m.
5. Laser shots/hits, candidate and baseline (the switch is expected to
   improve release-time laser aim as well as gun lead).
6. Rear-damage share.
7. Candidate outside-zone tick share.
8. Act exceptions, late answers, candidate/squad pre-415 zone deaths.
9. Mean/p99/max decision time.

## Promotion gates

Promote `AIM_PREDICT=True` only if all validity guards pass and one primary
score gate passes.

Validity guards:

- Unit check: `python -m unittest discover python/tests` passes.
- Candidate and squad: **0 act exceptions**, **0 late answers**.
- Candidate pre-415 zone deaths: no increase over baseline.
- Candidate outside-zone ticks: **<= 2%** and no more than **+1 percentage
  point** versus baseline.
- Rear-damage share: **<= 20%**.
- Per-tick: mean <= 15 ms, p99 <= 35 ms, max < 45 ms.
- Isolation: normalized diff proves only `AIM_PREDICT` differs from s_base2.

Primary gate (ship if either):

1. Paired mean score improves by **>= 1.0**, with kills/match improving by
   **>= 0.7**, or
2. Kills/match improves by **>= 0.7** and early-death share improves by
   **>= 10 percentage points**, with no mean-score or rear-damage regression.

Do not promote on a unit-test hit-rate result alone. The unit test is a
hardware-independent guard because it may show a larger effect than 56 squad
matches. Use the paired SE and the raw JSON as the source of truth.

Any valid improvement smaller than the bar is inconclusive; leave the switch
off and record the result. A proxy result that raises kills but lowers paired
score is a reject, not a stackable winner.
