# mechfight bot kit: breakdown

A summary of everything in this repo: what it's for, the game rules, the wrapper, the example bot, and how to submit. The source of truth is `protocol.md` and `hello.config`; numbers here are defaults and can change between matches.

## 1. Objective

Write a bot that pilots one mech in a **16-mech free-for-all battle royale** on a map of the Ohio State campus (Ohio Stadium to the Oval). This is the Mech Royale track at joinbuilders.org/buildathon.

- The bot is a program that reads JSON lines on stdin and writes JSON lines on stdout.
- It ships as a Docker image, submitted as a public GitHub repo with the `Dockerfile` at the top level.
- Each submission plays **48 practice matches** against built-in bots.

### Scoring

- Placement is the order mechs die in: last alive is 1st, first to die is 16th. Mechs that die on the same tick share a place.
- If the clock runs out (8:00), survivors are ranked by HP.
- Each match gives **`16 − place`** points (15 for a win, 0 for dying first). Your score is the mean over your matches.
- **Surviving matters more than kills.** Kills only help indirectly, through the cubes they drop.

## 2. Repo contents

| Path | Role |
|---|---|
| `README.md` | Quickstart: run the check, build the image, submit |
| `protocol.md` | Full rules and message format (the spec) |
| `mechfight.schema.json` | JSON Schema (draft-07) for every message |
| `python/mechfight.py` | Wrapper: stdin/stdout loop, typed messages, debug drawing (standard library only) |
| `python/example_bot.py` | Minimal example bot |
| `python/Dockerfile` | Submission image (`python:3.13-slim`) |
| `check/check.py` + `check/stream.jsonl.gz` | Conformance check that replays 300 recorded observations |
| `arena/v2/world.json`, `arena/v2/terrain.i16` | The map, mounted at `/arena` in a match |
| `main.py`, `pyproject.toml` | `uv init` placeholders that the bot doesn't use |

Notes:
- The README mentions a `ts/` TypeScript wrapper that isn't in this repo. Only Python is available here.
- The submission needs the `Dockerfile` at the repo root, but here it's in `python/`. Move those files up, or use a separate repo, before submitting.

## 3. Match lifecycle and timing

```
server → bot   hello                       once
bot → server   ready                       within 20 s (covers container start)
loop, 10 times per match-second while alive:
  server → bot obs  {tick: N, ...}
  bot → server action {tick: N, ...}       within 50 ms
server → bot   end {place, kills}          then stdin closes; exit
```

- **Lockstep:** the server sends all 16 observations, waits for every answer or 50 ms, applies the actions, then simulates 2 ticks (0.1 s). Answering fast never hurts you.
- **Echo the tick:** answers with the wrong tick, including late answers to earlier observations, are dropped.
- **No answer = coast, then idle:** without a valid answer your mech keeps the last `move`, `boost` and `aim`, and drops one-shot fields (`fire`, `jump`, `reload`, `pick`, `take`, `drop`). After 1.0 s of missed answers it idles.
- **Crash = idle** for the rest of the match.
- **Fall behind gracefully:** if observations queue up, answer only the newest. The wrapper does this for you.
- After your mech dies you get no more observations, only `end`.

### Runtime limits

- One JSON object per line, UTF-8, at most 64 KiB per line.
- stdout is for protocol messages only. Logs go to stderr (shown only when the conformance check fails at submission).
- Sandbox: no network, 1 CPU, 512 MB of memory, read-only disk except `/tmp` (64 MB), user uid 65534 (not root). Install packages system-wide in the Dockerfile.

## 4. Coordinates and units

- Meters, seconds, radians. **x = east, y = north, z = up**, relative to the ground at the map origin.
- **Yaw** is measured counter-clockwise from +x: 0 = east, π/2 = north, ±π = west. **Pitch** is positive upward.
- Direction vector: `[cos(pitch)·cos(yaw), cos(pitch)·sin(yaw), sin(pitch)]`.
- A mech is a vertical cylinder, radius 2.5 m and height 9 m. `pos` is the feet.
  - center of mass: `z + 4.5`
  - eyes: `z + 8`
  - gun muzzle: `z + 7`
  - mortar tube: `z + 9.5`
- Shots start 3.0 m out along the aim, or less if a wall is closer.
- NPC drones: radius 1.8 m, height 3.5 m.

## 5. Messages

### `hello` (server → bot)

- `slot`: your mech id for this match (0–15).
- `seed`: your own RNG seed (fixed per slot, unrelated to the match seed).
- `map`: `{dir: "/arena", files: [...]}`.
- `config`: the **complete rule set**. Read numbers from it instead of hard-coding them. It contains `match`, `bot`, `mech`, `vision`, `sound`, `weapons`, `projectile`, `cubes`, `crates`, `loot`, `npc`, `drops`, `zone`, `replay`, `debug` and `upgrades`.

### `ready` (bot → server)

`{"type": "ready", "name": "my-bot"}`. The name is cut to 32 characters.

### `obs` (server → bot)

| Field | Meaning |
|---|---|
| `tick`, `t` | Sim tick (20 per second) and match time in seconds. Echo `tick`. |
| `alive` | Mechs still alive. Your place if you died now. |
| `self` | `pos`, `vel`, actual `aim`, `hp`/`max_hp`, `energy`/`max_energy`, `grounded`, `cubes`, `upgrades`, `in_zone`, `weapons[2]` (null = empty slot; each has `cooldown`, plus `ammo`/`reload` for the gun, `charge` for the laser, and `stats` after upgrades), `stats` (mech numbers after upgrades) |
| `mechs` | Visible mechs and NPC drones: `id`, `kind`, `pos`, `vel`, `aim`, `hp`, `max_hp`, `cubes`, `weapons`, `charging` |
| `projectiles` | Visible enemy bullets, shells and NPC bullets with `pos` and `vel`. Your own are left out. |
| `crates`, `cubes`, `pickups` | Visible crates (with HP), power cubes, and weapons on the ground |
| `sounds` | What you heard since your last observation: `kind`, `bearing`, `dist`, `age` |
| `beams` | Laser beams and lightning arcs by others that you saw: `by`, `kind`, `path`, `age` |
| `events` | Things that happened to you (table below) |
| `drops` | Supply drops called and not yet taken: `pos`, `radius`, `lands_in`, `capture_s`, `progress`, `holder`. Always known. |
| `zone` | `center`, `radius`, `next_center`, `next_radius`, `shrink_start`, `shrink_end`, `dps`. Always known. |
| `offer` | A pending upgrade choice, or null |

Id ranges: mechs 0–15, NPCs 100+, crates 1000+, cubes 5000+, weapon pickups 8000+, supply drops 20000+.

#### Events

| `type` | Fields | Meaning |
|---|---|---|
| `damaged` | `amount`, `weapon`, `bearing`, `by`, `rear?` | You took damage. `bearing` is the world-frame yaw toward the source (null for the zone). |
| `hit` | `target`, `amount`, `weapon`, `effect?`, `rear?` | You damaged a mech, NPC or crate |
| `effect` | `effect`, `by` | `cookoff`, `short` or `concuss` landed on you |
| `drop` | `id`, `cubes` | You captured a supply drop |
| `kill` | `target` | You killed a mech |
| `pickup` | `cubes` | You picked up a cube |
| `upgrade` | `id` | An upgrade was applied |
| `took` | `id`, `kind`, `slot` | Your `take` succeeded |
| `dropped` | `id`, `kind`, `slot` | A weapon left your slot and lies on the ground |
| `take_failed` | `id`, `reason` | `gone`, `range`, `have`, `full` or `busy` |

### action (bot → server)

| Field | Default | Meaning |
|---|---|---|
| `tick` | required | Echo of the observation tick |
| `move` | `[0,0]` | Desired horizontal direction in the world frame. Length clamped to 1; less than 1 walks slower. |
| `boost` | false | On the ground: run at `boost_speed`, draining energy. In the air: jet upward. |
| `jump` | false | Jump if grounded |
| `aim` | last aim | Desired `[yaw, pitch]`. The torso turns toward it at `turn_rate`. |
| `fire` | `[false,false]` | Hold the trigger of slot 0 / slot 1 until the next decision |
| `reload` | false | Start a gun reload early |
| `pick` | none | Index 0–2 into the current offer's choices |
| `take` | none | Pickup id within 4 m horizontally and 4 m vertically |
| `drop` | none | Slot 0 or 1. With `take`, the slot to replace. Alone, empties the slot. |
| `debug` | none | Debug drawing (never affects the match) |

Each action lasts for the 2 ticks until the next decision. Unknown fields are ignored.

### Debug drawing

- `lines[]` (`a`, `b`), `points[]` (`at`, `size` 1–12), `text[]` (`text`, optional `at`), `label`, and an optional `color` on any item.
- A drawing stays until your next action that carries `debug`, or 0.5 s. Send `{}` to clear it.
- Caps: 64 lines, 64 points, 16 texts, 80 characters per text, 8192 bytes per decision, 8 MB per match. The server cuts anything over the caps without telling you.
- Debug drawings stay out of the public replay, and nothing on the track shows them to you.

## 6. Rules of the world

### Movement

- Mechs accelerate toward the commanded velocity: 58.5 m/s² on the ground, 12 in the air.
- **Walls:** you slide along them and never end up inside one.
- **Ledges** up to 1.2 m are walked up. Anything taller is a wall unless you jump and jet until your feet clear it.
- **Slopes** steeper than 50° can't be walked up.
- **Bridges and overhangs** higher than 9 m can be walked under, and their underside stops a jet.
- **Roof edges:** coming down past a roof you still overhang, you land on the edge. Keep moving toward the roof to step on, or you slide off.
- 100 energy climbs about 60 m, which reaches almost every campus roof but not the 70 m towers.
- Energy regenerates at `energy_regen`/s after `energy_regen_delay` s without spending.
- Gravity is 22 m/s². The map edge is a wall. Overlapping mechs are pushed apart.
- Legs and torso are independent: move one way, aim another.

### Health

- 1400 HP to start.
- After 5 s without dealing or taking damage you regenerate 45 HP/s, except outside the zone.
- Zone damage counts as taking damage. Armor reduces weapon damage, not zone damage.

### Rear armor

Hits from outside the 180° front arc around your aim yaw deal **×1.5 damage**. The direction is where the shot came from. Face your attacker. The `damaged.rear` flag tells you when you were hit from behind.

### Weapons

Every shot leaves along your *actual* torso aim. There is no lock-on. You start with only the gun in slot 0.

| Weapon | How it works |
|---|---|
| `gun` | Bullet at 252 m/s, 45 damage, one shot per 0.24 s, 12-round magazine, 2.4 s reload, small Gaussian spread, 230 m range, no drop. Lead moving targets. |
| `mortar` | Shell at 72 m/s along your aim, falling at 22 m/s² (max range about 235 m at 45°). 200 on a direct hit plus 160 splash falling to 30% at 7 m, blocked by walls. Your own splash hurts you at 50%. **Concussion:** throws mechs away (16 m/s, plus 9 up) and drains 45 energy, scaled by falloff, including you. |
| `laser` | Hold to charge up to 0.75 s, release to fire a hitscan beam (280 m). Damage scales from 35% at no charge to 315 at full. A full charge held 2 s more fires on its own. 1.65 s cooldown. Half speed while charging. Others see `charging: true` and hear it. **Cook-off:** +60% against a mech holding a mortar. |
| `lightning` | Instant. Hits the nearest target within 45 m and a 30° cone of your aim, with line of sight, for 60, then chains to 2 more within 14 m (×0.7 per jump). Costs 3 energy, fires every 0.25 s. Fires (and costs energy) even with no target. **Short:** a hit mech holding a laser loses its charge and can't charge for 2 s. |

**Weapon triangle:** laser beats mortar, mortar beats lightning, lightning beats laser. The gun is neutral.

**Cover:** bullets, shells and lasers hit buildings, bridges and terrain exactly. You can shoot under a bridge. **Trees don't stop shots**, so you can fire into trees at a sound.

**Cube scaling:** damage × `(1 + damage_per_cube × min(cubes, stat_cap))`.

### NPC drones

- 12 per match, 350 HP each. They wander within 30 m of home.
- They shoot (25 damage, 90 m/s bullets, 1 s cooldown) at whoever attacks them, or at mechs within 45 m with line of sight.
- They chase until the target is 90 m away or the drone is 60 m from home.
- Each drops 2 cubes. Drones don't take zone damage.
- Cubes go to the closest mech within the pickup radius (ties go to the lower id).

### Crates

36 per match, 300 HP each, about a quarter on rooftops. Destroying one drops 1 cube, and a weapon with 50% probability.

### Weapon loot

- Sources: 40 floor spawns at match start (a quarter on roofs), destroyed crates, and dead mechs (every weapon except the gun).
- Random spawns are mortar, laser and lightning in equal shares, never the gun.
- Taking is explicit: `take: <id>` within 4 m. It fills your empty slot, or the `drop` slot if both are full (the old weapon lands at your feet).
- You can't hold two of the same kind.
- A taken weapon can't fire for `max(equip_s, its cooldown)`: 1 s for the gun, 1.65 s for the laser. A dropped gun keeps its ammo.
- You can't drop or swap a laser while it's charging. You can drop the gun.
- If two mechs take the same pickup on the same tick, the closer one gets it.
- Ground weapons never despawn, but the zone closes over them.

### Supply drops

- Three per match, called at 70, 140 and 210 s. Each lands 25 s later on open ground inside the circle the zone is closing to.
- Every mech sees them in `obs.drops` from the moment they're called.
- Stand inside the 8 m ring **alone** for 4 s to gain **3 cubes, full HP and full energy**.
- With two or more mechs in the ring the clock freezes. If the ring empties, or a different mech becomes the only one in it, the clock restarts.

## 7. Vision and sound

### Vision

You see an object if your eye (z + 8) has line of sight to its center or top, and either:
- it's within **45 m** in any direction (buildings block, canopy doesn't), or
- it's within **200 m** and inside your **120° yaw wedge** centered on your aim, with no building blocking. Pitch doesn't matter.

- Light canopy still lets you see; dense tree crowns block. Tree trunks block sight but not shots.
- A mech or NPC you've seen stays tracked at its **real current position for 5 s** after leaving view.
- Crates, cubes, pickups and projectiles are listed only while visible.
- Where you aim is where you look, so scanning costs aim time.

### Sound

Carry ranges (m):

| Sound | Range | Sound | Range |
|---|---|---|---|
| `gun` | 320 | `jet` | 90 |
| `mortar` launch | 420 | `death` | 600 |
| `explosion` | 420 | `crate` | 220 |
| `laser` | 380 | `npc_gun` | 200 |
| `laser_charge` | 140 | `step` | 40 |
| `lightning` | 160 | `boost` | 90 |
| `reload` | 60 | `drop` (supply drop landing) | 600 |

- Moving faster than 5 m/s on the ground makes a `step` every 0.6 s, or `boost` while boosting. Walking slowly or standing still is silent.
- Each heard sound gives a `bearing` (world-frame yaw, ±7° Gaussian noise), `dist` (`near` < 60 m, `mid` < 160 m, `far`), and `age`.
- Each weapon has its own sound kind, so a sound tells you what the shooter holds. It doesn't say who.
- Your own sounds aren't reported.

## 8. The zone

- A circle that shrinks in phases: starts at 560 m around (41.3, −72.8), then 380 → 240 → 140 → 70 → 25 → 0 m.
- Damage outside it by phase: **20, 35, 60, 100, 160, 260 HP/s**. No armor, no regen.
- Before `shrink_start` the circle holds still. Between `shrink_start` and `shrink_end`, center and radius move linearly to the next circle.
- The next circle is always entirely inside the current one.
- The last circle closes at about 6:55. Matches end when one mech is left or at 8:00.

## 9. Cubes and upgrades

- Pick up a cube by walking within 3.5 m horizontally and 4 m vertically.
- Each cube: **+4% max HP** (healing the difference) and **+4% damage**, up to 10 cubes.
- Each cube also makes you **5% bigger, with no cap**: radius, height, eye and muzzle all grow. Easier to hit, but you see and shoot from higher.
- Killed mechs drop all their cubes plus two.
- At cube thresholds **1, 3, 6, 10, 15, 21, …** you get an **offer** of 3 upgrades.
  - Answer with `pick: i`. Unanswered after 5 s, choice 0 applies.
  - Offers queue one at a time.
  - Weapon upgrades only appear for weapons you hold, each up to its `max` stacks.
  - Weapon upgrades belong to your mech, not the item: they persist if you drop the weapon and apply again if you pick up the same kind.
  - The full list and effects are in `hello.config.upgrades`. Each effect multiplies (`mul`) or adds to (`add`) one stat.
- Example upgrades: `gun_rate` (+15% gun fire rate), `armor` (−8% damage taken), `sensors` (+15 m proximity, +25 m vision, halves sound bearing error).

## 10. Map files

`hello.map.dir` (`/arena` in Docker). The map is the same every match.

- **`v2/world.json`**
  - `bounds`, `terrain` (grid description), `prisms`, `trees`, `rules`.
  - `prisms[]`: every solid that isn't terrain. `kind` (`building`, `stadium`, `bridge`), `base` and `top` heights, `ring` (footprint polygon as flat `[x0, y0, x1, y1, ...]`), and `holes`. A point is inside if it's inside the ring, outside the holes, and between `base` and `top`. A bridge's `base` is above the ground.
  - `trees`: `fields` names the columns of the flat `data` array (`x`, `y`, `z`, `height`, `crownR`, `crownBase`, `trunkR`, ...). Trees block vision only.
  - `rules`: viewer walking rules and the canopy numbers (`canopyDensity`, `canopyBlockT`). The server uses `config.mech` for walking.
  - Ignored by the server: `blocks`, `stadium`, `cars`, `parking`, `water`, `barriers`, `stats`. None block movement, sight or shots.
- **`v2/terrain.i16`**: little-endian int16 centimeters, 1070 × 724, row-major from (`minX`, `minY`) with a 1 m step. Index `j * nx + i` is the ground height × 100 at `x = minX + i`, `y = minY + j`. Sample it bilinearly.

## 11. Versioning

`hello.protocol` is `"mechfight/1"`. Fields may be **added** within version 1, never removed or changed. Ignore fields you don't know.

## 12. The wrapper (`python/mechfight.py`)

Single file, standard library only, Python 3.9+.

- **Types (most of the file):** TypedDicts generated from the schema. At runtime every message is a plain dict.
- **`Draw` / `mf.draw`:** `line(a, b, color)`, `point(at, color, size)`, `text(text, at, color)`, `label(text)`. Stops adding at the server's caps. Cleared each decision.
- **`log(*args)`:** prints to stderr. stdout is the protocol.
- **`run(BotClass)`:**
  - A background thread reads stdin into a queue. Each loop empties the queue and answers only the newest `obs`.
  - On `hello`: sets the draw caps, builds `BotClass(hello)`, sends `ready` with the class's `name`.
  - On `obs`: calls `bot.act(obs)`, sets `tick`, attaches the debug drawing, and sends.
  - If `act()` raises: logs the traceback (first 5 times, then every 100th) and re-sends the last `move`, `aim` and `boost`, so the mech coasts.
  - If the action isn't JSON-serializable: logs it and sends `{tick, ...last}`.
  - Exits on `end` or when stdin closes.

Gotchas:
- If `__init__` raises, `bot` stays `None` and every answer is just `{tick}`, so the mech idles all match. Keep constructor work (such as loading the map) wrapped in error handling.
- The wrapper doesn't watch the clock. A slow `act()` misses the 50 ms budget and the answer is dropped. Keep your own compute under budget.

## 13. The example bot (`python/example_bot.py`)

Each tick it:
1. Picks upgrade choice 0 if there's an offer.
2. Takes the first non-gun pickup within reach if slot 1 is empty.
3. Walks toward the zone's *next* center, boosting when outside the zone, and jumps every 4 s.
4. Aims straight at the nearest visible mech (muzzle to center of mass) and fires both slots.
5. Draws a line to its target, a point at the goal, and an HP label.

What it lacks:
- No target leading, so the gun misses movers.
- Holding fire on a laser never releases; it only fires when the 2 s hold limit triggers.
- Ignores the weapon triangle, rear armor, cover, NPCs, crates, cubes, supply drops and sounds.
- No energy management or retreating.
- No map awareness, so it walks into walls and slides along them.

## 14. Testing and submitting

### Conformance check (`check/check.py`)

Feeds a recorded `hello` and 300 real observations, and verifies:
- `ready` arrives within the hello budget
- one schema-valid action per observation, echoing its `tick`
- answers within 50 ms (more than 2% late fails; a failing run is retried with a fresh bot up to 3 times, best counts)
- only the newest observation is answered when several are queued
- debug drawings stay inside the caps
- clean exit after `end`

The observations don't react to your actions. Passing means the protocol is right, not that the bot plays well.

```sh
python3 check/check.py -- python3 -u python/example_bot.py
docker build -t my-bot python
python3 check/check.py --map-dir /arena -- docker run --rm -i --network none --cpus 1 --memory 512m --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "$PWD/arena:/arena:ro" my-bot
```

The last command is exactly how the scorer checks your bot before matches. Common failures under those flags: writing anywhere but `/tmp`, and installing packages for root only (`pip install --user`, or into `/root`).

### Submitting

1. Make a public GitHub repo whose top level holds the files of `python/`, so the `Dockerfile` is at the root.
2. At most 20 MB at the submitted commit. Built on linux/amd64 with network on, and the build must finish within 10 minutes.
3. Submit the repo address on the Mech Royale track page. Each submission is built, checked with `check.py`, and played in 48 practice matches. The page shows your score or what to fix.

## 15. Strategic takeaways

These follow from the rules; none are tested yet.

- **Survive first.** Placement is the whole score. Avoid early fights you don't need.
- **Respect the zone.** Damage escalates fast (260 HP/s at the end) and blocks regen. Move toward `next_center` before the shrink starts.
- **Use regen.** 45 HP/s after 5 s of no combat refills you in about 30 s. Break contact to heal.
- **Face threats.** Rear hits do ×1.5. Turn toward `damaged.bearing`.
- **Farm cubes safely.** Crates (1 cube, often a weapon) are free. NPCs give 2 cubes but shoot back. Supply drops give 3 cubes plus a full heal if you can hold the ring alone.
- **Pick weapons by the triangle,** based on what nearby enemies carry (visible in `mechs[].weapons`, or heard from sounds).
- **Lead the gun:** solve for intercept with 252 m/s bullets against target `vel`.
- **Stay quiet when hiding.** Under 5 m/s is silent.
- **Use the map.** Load `world.json` prisms and terrain for pathing, line of sight and cover. Roofs are reachable with about 60 m of jet energy.
- **Read numbers from `hello.config`.** Balance changes between matches.
