# Researcher: journal

Owns: `notes/research/`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration (2026-11-22) brief: measure opponent behaviour in the recorded stream for assumptions A5, A7-A13 -> `notes/research/house-bots.md` + section in `notes/ideas/assumptions-discussion.md`. Status: **done**.

Previous: 
Iteration 1 brief (moderator): collect the facts the builders and the Strategist need, with evidence: `hello.json` + `config.md`, `map.md`, `upgrades.md`, `zone.md`, `stream.md` in `notes/research/`. Status: **done** (all six files written, 2026-11-21).

## Plan

1. Extract the `hello` line from `check/stream.jsonl.gz` raw into `hello.json`; diff every `config` value against the numbers protocol.md states. (done)
2. Analyze `world.json` + `terrain.i16`: bounds, terrain, prisms by kind, roof rise distribution, bridges, footprint vs open, trees, open regions and clusters. (done)
3. Tabulate `config.upgrades`, stacked values, survival ranking. (done)
4. Zone phase table, walk/boost distances, worst-case gaps, latest safe departure rule. (done)
5. Summarize the 300 observations: time range, visible counts, events, sounds, undocumented fields. (done)

Done when the five files exist with evidence: met.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Config values only known as defaults | Wrong numbers break aiming and zone timing | Read them from the recorded hello | done: 0 of 162 differ, 32 not in protocol listed in `config.md` |
| Path factor (path length / straight line) is a guess (1.3) | Sets the zone departure time; too low = zone deaths (proxy: 0% zone deaths) | Once `world.py`/`nav.py` exist, sample 200 random point pairs in the zone and measure real path length | open |
| When the next circle of phase ≥ 2 is announced is assumed (hold start) | Departure timing for phases 2–6 | The stream only covers t ≤ 36.8; ask the Tester's simulator or a real match log; until then plan from `shrink_start` only | open |
| Plating: does it heal the added HP? | Decides upgrade order and endgame HP (HP at 415 s decides the win) | Observe `self.hp` around the first `upgrade` event in a real or simulated match | open |
| Barriers: 20 fences have `"blocks": true` in world.json but §11 says the server ignores barriers | A pathfinder that trusts world.json would avoid open ground needlessly; one that ignores a real wall gets stuck | Confirm against a real match (stuck detection near a fence line) | open |
| Spawn/drop placement semantics (`spawn_zone_fraction` 0.8, `arena_margin` 30, `drops.spread` 0.7) are inferred, not specified | Phase-1 travel need and drop contest planning | Collect spawn positions over several matches/sim runs | open |
| Opponent model rests on one FFA bot (mech 10) over 36.8 s | Sim calibration of house bots (A9-A13) | Get a real squad-practice replay or obs log; repeat `house-bots.md` measures on it | open |
| My map raster took 18 s in pure Python | Builders copying it would blow the 5 s ready budget | Flagged in `map.md`; recommend coarse grid / bbox culling | done (flagged) |

## Lessons

- Projectiles carry no owner: attribute shooters by sound bearing vs bearing to the visible mech, and by `damaged.by`.

- `python -I` ignores `PYTHONIOENCODING`, and Windows stdout redirected to a file is cp1252: `§` came out as byte 0xA7. Use `python -I -X utf8` when piping output into notes, and check files decode as UTF-8 before reporting.
- Computing worst cases from the config (2·(r₀−r₁), boundary speed) is more useful to builders than restating the table; the single biggest insight came from following a number to its end (radius 0 at 415 s → HP decides the winner).
- Check every hand-computed number against a second calculation before writing it; I caught one wrong stacked value (gun_rate cooldown) only on review.

## Log (newest first)

- 2026-11-22: wrote `notes/research/house-bots.md`. Recording is FFA (no squad keys, others kill each other). Mech 10: on target 0.6 s after being hit, laser hit 2.2 s; ignored our unseen shots; aim residual 0.023 rad around ideal lead; gun ~5/10 at 150 m, laser 4/5; boosts (19.4 m/s), jet-hops, jukes; looted laser by t 4.9. A11 contradicted, A5/A10/A13 supported, A2/A7/A8 untouched. Next: same measures on a squad-mode log.

- 2026-11-21, iteration 1: wrote `notes/research/hello.json`, `config.md`, `map.md`, `upgrades.md`, `zone.md`, `stream.md`. Evidence: scratch scripts `map.py`, `stream.py`, `config.py` (stdlib) in the session scratchpad; outputs quoted in each file. Key results: config matches protocol (0/162 differ; thresholds list ends at 45; `hello.map.dir` is `../arena`); 244/250 roofs ≤ 49.5 m rise, 6 out of reach (≥ 67.3 m), clean gap; footprint 22.8% of map; start zone covers 93.2% of map; stadium is terrain (all 19,810 cells > 10 m, 5,292/5,357 steep cells); only bridge #4 is a safe underpass; tree crowns are offset (`crownX/crownY`); zone radius 0 at 415 s; walking beats boundary speed in every phase (max 7.2 m/s); recorded mech lost a gun duel to a gun+laser mech at ~150 m (4 × 315 laser hits) and placed 13th; dealing damage resets regen (measured). Next: measure path factor and plating heal once nav/simulator exist.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
