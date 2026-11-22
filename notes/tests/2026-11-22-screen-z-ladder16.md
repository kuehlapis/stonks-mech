# 2026-11-22 z_ladder bounded 16-pair screen

Date: 2026-11-22
Mode: 16 paired seeds, seed 11, rotate enabled, jobs 4
Candidate: `z_ladder`
Baseline: `s_base2`
Squad model: `sim/bots/squad.py`
Runner shell: `126`
Raw JSON: `notes/tests/screen-2026-11-22-z_ladder-vs-s_base2-seed11.json`

## Summary

| Arm | N | Score ± SE | Kills/match | Win % | Early death % | Rear damage % | Outside-zone % | Errors | Late answers |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `z_ladder` | 16 | 2.81 ± 0.55 | 1.44 | 0.0 | 50.0 | 5.8 | 1.56 | 0 | 4 |
| `s_base2` | 16 | 2.38 ± 0.46 | 1.19 | 0.0 | 56.2 | 4.5 | 1.91 | 0 | 3 |

Paired score delta: **+0.44 ± 0.45**.
Paired kill delta: **+0.25 ± 0.19**.
Wall time: 1152.59 s.

The score delta is below the objective's 1.0-point evidence threshold and
is not statistically screen-confirmed. No winner is confirmed, so no
56-match batch was allowed.

## Confounded or stale exclusions

- `r_run`: excluded; bundled `RUN_MODE=True` with `FIRE_POLICY=True`.
- `b_rear`: excluded; stale/partial variant relative to `s_base2` and changes
  rear behavior in a different code snapshot.
- `m_boost`: excluded; stale/partial variant relative to `s_base2`.
- `s_close`: excluded; stale/partial variant relative to `s_base2`.
- `s_duck30`: excluded; stale/partial variant relative to `s_base2`.
- `z_ladder`: retained. Against `s_base2`, its source diff is isolated to
  `LADDER=True`; no bot behavior was edited.

One prior 56-match `z_ladder` shell was launched outside this bounded run
and was stopped before stale results could be used or overwrite the raw
screen artifact. No 56-match batch completed.
