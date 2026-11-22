# Post-fix sub1 calibration, 2026-11-22

## Smoke: seeds 2100025-2100032

Command:

```sh
python sim/inproc.py --bot sub1=sim/versions/sub1/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 8 --jobs 8 --seed 2100025 --rotate --out notes/tests/cal-postfix-smoke-sub1.json
```

Raw results:
- sub1: score **1.25 ± 0.45**, kills 0.88, median death 54.85 s
- squad: score 8.58 ± 0.40, deaths by NPC/gun/laser 27/7/7
- pre-415 squad zone deaths: **0**
- squad errors: **0**
- sub1 errors: **0**
- squad outside-zone ticks: **27.88%** (258,457 / 927,046)
- sub1 outside-zone ticks: **0%**
- late answers: 2 squad, 7 sub1

The smoke was clean for zone death and runtime exceptions. It was not a calibration
target sample; its noise interval is wide.

## Full 40-seed rerun

The first 40-seed run found 4 squad act() exceptions, all at a zero-distance
division path. A guard was added to `sim/bots/squad.py` for goal clamping, and
the 50-test simulator suite passed. The full run was rerun clean:

```sh
python -m unittest discover sim/tests
python sim/inproc.py --bot sub1=sim/versions/sub1/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 40 --jobs 8 --seed 2100025 --rotate --out notes/tests/cal-postfix-sub1-40.json
```

Raw results:
- sub1: score **1.82 ± 0.27**, kills 0.88, median death 73.3 s
- early death: 70.0%
- squad: score 9.02 ± 0.18
- squad causes: NPC 103, gun 33, laser 9
- pre-415 squad zone deaths: **0**
- squad errors: **0**
- sub1 errors: **0**
- squad outside-zone ticks: **27.93%** (1,332,596 / 4,697,483)
- sub1 outside-zone ticks: **0%**
- late answers: 4 squad, 46 sub1

## Verdict

The calibration is valid for zone/death safety: 40 seeds produced no pre-415
squad zone deaths and no bot exceptions. Sub1 scored 1.82 ± 0.27, essentially at
the 1.6 ± 0.2 target boundary and above the handoff pressure threshold of
1.6 + 0.2 = 1.80.

## Exact next action

Raise squad pressure: set `DEFEND_RANGE` from 60 to 80, or move the +1 hunter
trigger earlier than 150 s, then rerun sub1/example/s_base2 on 40 seeds.
