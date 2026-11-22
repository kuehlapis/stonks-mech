# Pre-415 squad zone-death trace, 2026-11-22

## Scope

Bounded analysis of `notes/tests/cal-immune-sub1.json` (40 seeds, sub1 ×1 + squad ×15),
plus one-slot replay of seed 2100025, slot 13. This investigates the remaining
pre-415 squad exits after zone immunity and the wall-exit priority fix. It does not
change shipped bot behavior.

## Commands

```sh
python -c "import json,statistics,collections; d=json.load(open('notes/tests/cal-immune-sub1.json')); ..."
python sim/inproc.py --bot sub1=sim/versions/sub1/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 1 --jobs 1 --seed 2100025 --start 0 --rotate --trace 13 --trace-out notes/tests/squad-immune-seed2100025-slot13.jsonl --out notes/tests/squad-immune-seed2100025-slot13.json
```

The analysis command counted raw match rows for labels beginning `squad`.

## Findings

- 40 matches, 600 squad rows: **0 squad zone deaths**.
- Squad death causes across the complete 40-seed run:
  - NPC: 123
  - gun: 34
  - laser: 13
- 158 squad rows die before 415 s in the raw deadline-filtered check; 118 are
  NPC, 34 gun, and 6 laser below 415 s. There is no zone cause.
- 449 of 600 squad rows have at least one outside-zone tick.
- Median `ticks_out` is 1,448 ticks;
  max is 7,882 ticks. This is a high outside-time proxy, not a death cause.
- The replay trace for seed 2100025, slot 13 ran 480 s, with no zone-death row:
  15 squad NPC deaths in that one match and sub1 died by gun at 35.95 s.
- The replay slot was not observed outside the current zone ring in the trace
  window, so it does not prove the `ticks_out` worst row in the 40-seed artifact
  is wall-wedge-specific; that row and the 40-seed seed/slot mapping need a
  tighter replay before changing simulator routing.

## Replay classification, highest original `ticks_out` rows

| Original case | Replay result | Classification | Evidence |
|---|---|---:|---|
| seed 2100025 / slot 13, 7,882 ticks | Replay in current code: dies to sub1 gun at 38.8 s, 0 ticks out | Other / short combat death | Original and replay differ; replay does not represent an exit |
| seed 2100012 / slot 11, 7,848 ticks | Current replay: 3,353 ticks out, survives | Next-ring geometry / active exit | Current-ring outside 85.2 s at 325–410.2 s; next-ring outside 214.9 s at 265–479.9 s. |
| seed 2100021 / slot 5, 7,843 ticks | Replay in current code: dies by laser at 47.2 s, 0 ticks out | Other / short combat death | No current or next-ring outside segment |
| seed 2100033 / slot 6, 7,823 ticks | Replay in current code: survives, 4,441 ticks out | Wall wedge | Pre-fix position remained `(-23.2, -211.5)` from about 171–479 s while sideways move/jump/boost commands alternated; low-progress range was 308.3 s. |
| seed 2100010 / slot 8, 7,732 ticks | Current replay: survives | Next-ring geometry | Next-ring outside 104.9 s at 375–479.9 s; current-ring outside only 0.1–0.2 s blips. |

The 2100025 and 2100021 replay outcomes do not match their original 40-seed
rows. They are therefore marked **other**, not evidence of a geometry bug.
Differences are consistent with running the later squad model rather than the
artifact's earlier code snapshot.

## Evidence-supported simulator fix

The only supported fix was in `sim/bots/squad.py`: when `zone_exit` is true,
zone movement has priority and the stuck side-slide is suppressed. This prevents
wall-slide logic from overriding a direct pull toward the next-circle centre.
No shipped `python/` bot file was changed.

## Bounded smoke

Replay seed 2100033 / slot 6 before and after the fix:

| Run | Slot 6 `ticks_out` | Low-progress wedge | Position outcome |
|---|---:|---:|---|
| Pre-fix | 4,441 | 308.3 s | Wedged at `(-23.2, -211.5)` |
| Post-fix | 3,355 | No 308 s interval; maximum matched intervals were 0.1 s | Wedge removed |

Post-fix delta: **-1,086 ticks_out** (`-24.5%`) for the traced slot.

Simulator unit verification: `python -m unittest discover sim/tests` ran 50 tests;
all 50 passed.

## Verdict

The wall-exit/zone-immunity fix removed zone-caused squad deaths as intended:
the latest 40-seed artifact has 0 zone deaths. The remaining investigation target
is **outside-zone tick accumulation and pre-415 NPC/gun/laser deaths**, not a
pre-415 zone death count.

## Exact next action

Run an 8-seed bounded smoke against the post-fix squad model (seeds 2100025–
2100032, `--matches 8 --jobs 8 --rotate`) and compare aggregate squad
`ticks_out` plus pre-415 zone/combat causes against `cal-immune-sub1.json`.
If it does not regress squad survival or the next model benchmark, rerun the
40-seed calibration for sub1/example/s_base2. Do not change shipped bot code.
