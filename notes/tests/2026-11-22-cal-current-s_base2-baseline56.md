# Current calibrated-squad baseline: s_base2 ×1 vs squad ×15

Date: 2026-11-22  
Mode: 56 paired matches, seed 11, `--rotate`, 4 workers  
Raw: `notes/tests/cal-current-s_base2-baseline56.json`

Command:

```sh
python sim/inproc.py --bot s_base2=sim/versions/s_base2/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 56 --jobs 4 --seed 11 --rotate --out notes/tests/cal-current-s_base2-baseline56.json
```

## Summary

| Slot | Score ± SE | Kills/match | Median death | Early death (<120 s) | Death causes | Rear damage | Outside-zone ticks | Late answers | Act errors |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| `s_base2` | **2.00 ± 0.25** | 0.98 | 133.5 s (runner upper median); 131.15 s standard median | 48.2% (27/56) | gun 42; laser 12; NPC 1; zone 1 | 10.1% | 0.34% | 0 | 0 |
| `squad` | **9.03 ± 0.15** | 0.08 | 107.0 s | 14.3% (120/840) | NPC 146; gun 41; laser 20; lightning 5 | 52.2% | 27.75% | 0 | 0 |

Additional validity counts:
- Squad zone deaths before 415 s: **0**.
- The `s_base2` zone death occurred at 269.9 s. It is a candidate-bot zone
  death in the pre-415 interval and does not change the squad validity check.
- `s_base2` mean decision time 0.44 ms; runner maximum 33.36 ms.
- Squad mean decision time 0.06 ms; runner maximum 37.65 ms.

## Status

Baseline recorded before any switch test. No `python/` behavior or simulator
switch was changed.
