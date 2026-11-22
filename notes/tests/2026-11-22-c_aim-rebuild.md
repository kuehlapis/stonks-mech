# c_aim rebuild — 2026-11-22

Rebuilt `sim/versions/c_aim/` as a copy of `sim/versions/s_base2/` and set
`AIM_PREDICT=True` in the candidate `combat.py`.

Isolation:
- Normalized diff across candidate files: no differences after normalizing the
  single `AIM_PREDICT` assignment.
- Raw `combat.py` diff: only `AIM_PREDICT=False` → `AIM_PREDICT=True`.
- `b_peek` and all other requested switches remain off.
- No simulator match batch was run.

Validation:
- `python -m unittest python.tests.test_combat`: 18 tests passed.
- `python -m unittest discover python/tests`: 93 tests passed on rerun.
- The first run had one transient survival timing failure
  (`worst_cover=34.14 ms`, limit 10 ms); rerun passed
  `survival timing: find_cover max 3.11 ms`.
