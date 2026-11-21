# Recorded stream: `check/stream.jsonl.gz`

Evidence: scratch script `stream.py` (stdlib, gzip + json), run as `python -I stream.py check/stream.jsonl.gz`, plus a timeline one-liner. Numbers are its output.

## Shape

- 302 lines: 1 `hello`, **300 `obs`**, 1 `end` = `{"place": 13, "kills": 0}`. We are slot 3 (`self.id` 3).
- Time range **tick 0 → 736, t 0.0 → 36.8 s**, all in zone phase 1's hold.
- Steps: 295 × 2 ticks (0.1 s), but **one 128-tick gap** (tick 590 → 718, t 29.5 → 35.9: 6.4 s missing) and three short ones (4, 8, 6 ticks) at the end. The bot must not assume t advances by 0.1 per obs: use `t`/`tick` deltas for velocity, timers and regen estimates.
- `alive`: 16 for 180 obs, then 15, 14, 13 (three `death` sounds; first death ≈ t 17).
- Obs line size 1,387 – 2,008 bytes.
- Our mech: spawned at (320.2, −280.3, −2.0) in the south-east open area, full HP/energy, gun only (slot 1 `null`), never took a pickup, 0 cubes, no offer, no drop, `in_zone` true throughout, airborne in 61 of 300 obs. At t 36.8 it has **9.5 HP** with an empty magazine mid-reload; it dies right after (place 13).

## What is typically visible (per obs)

| list | min | median | mean | max | distinct ids over the stream |
|---|---|---|---|---|---|
| mechs (kind mech) | 0 | 1 | 0.56 | 1 | 1 (id 10, always `["gun", "laser"]`) |
| NPCs | 0 | 0 | 0 | 0 | 0 |
| projectiles | 0 | 0 | 0.10 | 2 | 11 (all `gun`) |
| crates | 0 | 0 | 0.15 | 3 | 3 |
| cubes | 0 | 0 | 0.01 | 1 | 1 |
| pickups | 0 | 0 | 0.69 | 4 | 9 (4 laser, 4 lightning, 1 mortar) |
| sounds | 0 | 0 | 0.27 | 2 | — |
| beams | 0 | 0 | 0.02 | 1 | — (5 laser beams, all by id 10) |
| events | 0 | 0 | 0.08 | 2 | — |
| drops | 0 | 0 | 0 | 0 | — (first drop is called at 70 s) |

So the world is sparse: one enemy at a time, usually nothing else. Per-tick work is dominated by our own model, not by obs size.

## Events and sounds seen

- Events: `damaged` × 13 (gun 9, laser 4), `hit` × 10 (all gun, all on mech 10). No `kill`, `pickup`, `upgrade`, `took`, `effect`, `drop`.
- `damaged.rear` never appears (we were never hit from behind); **`rear` is omitted, not `false`, when not a rear hit**. The first `hit` has `rear: true` and `amount` 67.5 = 45 × 1.5 (§7 rear armor confirmed).
- Sounds: gun 62, laser 6, explosion 5, death 3, crate 2, laser_charge 2, mortar 1, boost 1. Distance: far 58, mid 22, near 2.

## The fight that killed us (lesson for the Strategist)

Mech 10 (gun + laser) engaged from **~150 m** at t 5.7 (later ~100 m, and 55 m at the end). Laser hits for **315 each** (full charge, no range falloff) at t 7.9, 10.6, 19.3 and 35.9; gun hits for 45 in between. Our gun hit back 10 times (472.5 damage; the enemy's lowest HP was 1028.75, and regen gave it back 218 HP between t 25 and 35.9). Laser hits alone took 1260 of our 1400 HP. Gun vs laser at 150 m in the open is a losing trade; the bot should break line of sight when it sees `weapons` containing `laser` or a `charging: true` / `laser_charge` sound.

Regen confirmed: HP went 545 → 556.25 at t 18.8, i.e. 0.25 s × 45 HP/s, exactly 5 s after our last *dealt* damage at t 13.5. **Dealing damage resets the regen timer too** (§7 says "without dealing or taking damage").

## Fields vs protocol.md

Every key seen is documented in §6 (key sets per object type listed by the script). Nothing undocumented at the obs level. Details protocol.md leaves implicit:

- `self.stats` has 34 keys, exactly the `config.mech` keys (`radius`, `height`, `eye_height`, …, `hearing`), shown as `"..."` in §6.
- `self.weapons[i].stats` has the `config.weapons.gun` keys.
- Optional event fields are omitted when unset (`rear`, `effect`), not sent as `false`/`null`.
- Other mechs carry `cubes`, `charging`, `weapons`, `hp`, `max_hp` in every entry seen.
- `hello.map.dir` is `"../arena"` in the recording (see `config.md`).
