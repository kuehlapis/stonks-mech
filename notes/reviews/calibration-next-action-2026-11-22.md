# Critic finding: next action after the zone-death trace

## Verdict

Do not rerun bot switch A/Bs, edit shipped bot behavior, or tune
`DEFEND_RANGE` / hunter timing yet. The highest-value next action is to
finish the squad-model trace and prove that the v2 squad is zone-safe.

## Evidence

- `notes/progress.md`: the later session target is mean 10, and its first
  calibration step says to rerun sub1, s_base2, and example on 40 seeds.
- `notes/tests/2026-11-22-calibration.md`: the c1 v2 run for sub1 is
  **2.23 ± 0.31**, and the raw rows show **407 squad zone deaths** before
  415 s. The unchanged example run is also invalid with 357 squad zone
  deaths. Neither result is usable for bot selection.
- `notes/agents/tester.md` log: the calibration task explicitly remains
  blocked until the v2 zone regression is traced and fixed.
- `notes/tests/squad-v2-trace.jsonl` already contains a one-match v2 trace;
  `notes/tests/squad-zone-slot4-trace.jsonl` contains a separate slot trace.
  These are diagnostic evidence, not permission to change the bot.
- The drone-routing smoke is not a substitute: it was only 4 matches,
  improved drone deaths modestly (about 3.1 -> 2.75 per match), and raised
  sub1 to 2.25. The 40-seed routing run was stopped and no result exists.
- The older 1042 bot-zone trace in
  `notes/reviews/aar-2026-11-21-2.md` is about shipped-bot zone discipline,
  not the currently blocking `squad.py` calibration regression.

## Bounded execution plan

1. Trace one known pre-415 v2 squad zone death at a stable seed/slot,
   recording position, zone/next-zone distances, stuck state, wall state,
   and whether boost/jet/slide goals repeat.
2. Confirm the root cause and whether it is general or slot-specific.
3. If general, make only a simulator-model fix in `sim/bots/squad.py`;
   do not touch `python/`.
4. Run a small smoke (about 4 matches) and require 0 pre-415 squad zone
   deaths.
5. Then rerun sub1, s_base2, and example on 40 seeds in separate output files.
   A run is valid only if squad zone deaths before 415 s are 0.
6. Only after sub1 calibrates near 1.6 ± 0.2 should bot switch A/B work
   resume.

## Stop conditions

No bot behavior change and no unrelated implementation work in this step.
Return to the zone trace if the smoke is not zone-safe. Ignore track score
until the model and raw death causes are valid.

## Execution result

A trace of seed 2100000 / slot 15 from the pre-fix model was replayed
with `sim/bots/squad.py`; it did not reproduce a zone death, but the
bounded 4-match smoke exposed a separate zone-navigation defect. In one
match a squad bot could reach the next-circle centre exactly, so
`zone_exit` then divided by the distance from that point to the centre.
This raised a `ZeroDivisionError` in `squad.py:245` and was counted as a
simulator bot error.

Simulator-only fix: at `zone_exit`, only divide by centre distance when
the distance is non-zero. No file under `python/` was changed.

Evidence:

- Pre-fix 4-match smoke:
  `notes/tests/zone-smoke-4.json`
  - squad: 60 mechs, 0 pre-415 zone deaths in the row counts, but
    **1 simulator error** and a `ZeroDivisionError` trace.
- Post-fix 4-match smoke:
  `notes/tests/zone-smoke-4-fixed.json`
  - squad: 60 mechs, **0 pre-415 zone deaths**,
    **0 simulator errors**, **0 late answers**,
    median squad death 114.0 s.
  - sub1: 4 mechs, median death 31.5 s, 0.25 kills/match.
- Fixed smoke output: 4/4 matches completed in 118 s.
- `python -m unittest discover sim/tests`: 50/50 passed.

Status: the bounded smoke passes its stop condition. This result does
not calibrate pressure or validate track targets. Remaining work is still
the 40-seed sub1 / example / s_base2 calibration on the corrected model.
