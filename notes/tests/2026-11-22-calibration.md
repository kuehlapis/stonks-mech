# Squad model calibration, 2026-11-22 (Tester). UNFINISHED: session ended.

Targets (moderator): on 40 seeds (`--seed 21 --rotate`), sub1 (f803b02, `sim/versions/sub1/bot.py`) = 1.6 ± 0.2, s_base2 (c529ecc) = 1.6 ± 0.2, example bot = 1.15 ± 0.2. 0 squad zone deaths before 415 s, or the run is invalid.

Command: `python sim/inproc.py --bot <L>=<path> --count 1 --bot squad=<model> --count 15 --matches 40 --jobs 4 --seed 21 --rotate --out <json>`

## Runs

| # | Squad model | Knobs | Our bot | Score ± SE | Kills | death_t_median | Squad zone deaths < 415 s | Valid? |
|---|---|---|---|---|---|---|---|---|
| c0 | `sim/bots/squad_v1.py` (zone-smart + retaliation, before calibration) | RETALIATE_S 10, DEFEND_RANGE 60, strafe 0.6–1.6 s, no chase boost, no wall slide | sub1 | **1.23 ± 0.21** (target 1.6) | 0.65 | 59.8 s | 320 of 419 zone deaths | **No** (zone deaths) |
| c0 | squad_v1 | same | example | not finished (stopped at session end) | | | | |

Not run: s_base2, and every run on the new squad.py (v2).

## Where the 1.6 floor comes from

Score = 16 − place = the number of mechs that die before us (protocol §4). In run c0, sub1 dies at a median of 60 s. The 1.23 it scores is almost exactly what died before it:
- 0.63 squad bots per match killed by our gun and 0.05 by laser (our kills: 0.65/match)
- 0.55 squad bots per match killed by NPCs

Zone deaths of squad bots come later than ours, so they don't count toward our score. So the floor is about **our kills + NPC kills of squad bots before we die**. It barely depends on fight quality as long as we die in the first ~1–2 min. Two different bots both scoring 1.6 on the track fits this. To land 1.6, the levers are how long we survive (hunter schedule, DEFEND_RANGE, aim) and how often NPCs kill squad bots early, not zone behaviour.

## squad.py v2 (written, importable, NOT yet measured)

Old model kept as `sim/bots/squad_v1.py`. Changes, from `notes/research/house-bots.md`:
- `RETALIATE_S = 30.0`: the observed bot kept retaliating for ≥ 31 s.
- `STRAFE_S = (0.3, 0.6)`: the observed bot reversed direction every 0.3–0.6 s.
- `CHASE_BOOST_M = 40`: hunters boost toward a goal farther than 40 m when energy > 30 and not stuck (the observed bot closed at 19.4 m/s).
- Wall slide: when stuck, a bot moves sideways and switches side every 4 s. This fixes the wedge traced earlier today.
- Zone fallback: a bot that is out of the zone, or still outside the next circle within 10 s of shrink_start, boosts toward the next centre.
- `squad_chase.py` now only adds sound hunting on top of squad.py.

## Next (unfinished)

1. Run v2 vs sub1, example and s_base2 (40 seeds each). First check that squad zone deaths before 415 s are 0. If not, trace one (`--trace SLOT`) and fix.
2. If sub1 is still below 1.6, our bot dies too early. Lower the pressure: DEFEND_RANGE 60 → 45, or start the extra hunters later (+1 at 150 s → 180 s). If it's above 1.6, do the reverse. Use aim noise only to separate example from sub1.
