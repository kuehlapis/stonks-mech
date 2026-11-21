# Config from the recorded hello

Source: `notes/research/hello.json`, the one `hello` line of `check/stream.jsonl.gz` (302 lines: 1 hello, 300 obs, 1 end), saved raw.
Extracted with `python -I -c "import gzip,json; ..."` (first line whose `type` is `hello`). Table built by a scratch script that flattens `config` and compares each value with the number protocol.md states (section in brackets).

## Verdict

- **No value differs from protocol.md.** 162 flat values checked: 130 match the number protocol.md gives, 0 differ, 32 have no number in protocol.md (listed as "new number" below; they are the physics and timing constants a builder still needs).
- `cubes.upgrade_thresholds` is `[1, 3, 6, 10, 15, 21, 28, 36, 45]`: protocol §10 shows `1, 3, 6, 10, 15, 21, …`; the list **ends at 45**.
- `zone.phases` (not in the table; see `zone.md`) matches §9: radii 380, 240, 140, 70, 25, 0 and dps 20, 35, 60, 100, 160, 260; the last shrink ends at 415 s = 6:55.
- `config.upgrades`: 22 entries, see `upgrades.md`.
- Non-config hello fields: `protocol` `mechfight/1`, `slot` 3, `seed` 315233926, `map.dir` **`"../arena"`** (the check's kit-relative path, not `/arena`; `check.py --map-dir /arena` rewrites it, §1), `map.files` `["v2/world.json", "v2/terrain.i16"]`. Bots must open `os.path.join(hello.map.dir, file)`, never a hard-coded path.
- `obs.self.stats` carries every `config.mech` key (34 keys, same values at t=0), and `self.weapons[i].stats` carries the `config.weapons.<kind>` keys. So the bot can read live (post-upgrade) numbers from the obs; `hello.config` gives the base values.

## Numbers a builder needs that protocol.md does not give

| Key | Value | What it means for the bot |
|---|---|---|
| `mech.jump_speed` | 11 m/s | ballistic jump apex 11²/(2·22) = 2.75 m |
| `mech.jet_accel`, `max_rise_speed` | 34 m/s², 10 m/s | jet climbs at most 10 m/s |
| `mech.jet_drain` | 15/s | 100 energy = 6.67 s of jet = ≤ 66.7 m climb at 10 m/s (+2.75 m jump); protocol's "about 60 m" is the safe figure |
| `mech.boost_drain` | 17/s | 100 energy = 5.88 s of ground boost = 114.7 m at 19.5 m/s |
| `mech.energy_regen`, `energy_regen_delay` | 18/s after 0.6 s | 0→100 in 6.16 s |
| `mech.pitch_rate`, `min_pitch`, `max_pitch` | 3 rad/s, −0.7, 1.3 | aim limits; mortar max-range pitch 45° = 0.785 is allowed |
| `weapons.mortar.cooldown` | 2.6 s | |
| `weapons.mortar.ttl` | 7 s | shell lifetime; a 45° shell at 72 m/s flies 2·72·sin45/22 = 4.6 s, so ttl does not cut max range |
| `weapons.laser.pierce` | 0 | `laser_pierce` upgrade adds 1 |
| `projectile.gun_radius`, `npc_radius` | 0.3 m | bullet collision radius |
| `crates.radius`, `crates.height` | 1.4 m, 2.4 m | aim point for crates: pos.z + 1.2 |
| `npc.speed`, `npc.spread_deg` | 5 m/s, 2.5° | NPCs are slow; easy to outrun or kite |
| `match.spawn_min_separation` | 130 m | no enemy spawns within 130 m |
| `match.spawn_zone_fraction` | 0.8 | presumably spawns lie within 0.8 × 560 = 448 m of the zone center (assumption, not stated) |
| `match.arena_margin` | 30 m | presumably spawn/loot margin from the map edge (assumption) |
| `drops.repair` | 1 | capture restores 100% HP (§7 "full HP") |
| `drops.spread` | 0.7 | presumably drops land within 0.7 × the next circle's radius of its center (assumption) |

## Full table

| key | hello value | protocol.md | status |
|---|---|---|---|
| `match.tick_hz` | 20 | 20 (§6 obs) | same |
| `match.decide_every` | 2 | 2 (§2) | same |
| `match.duration_s` | 480 | 480 (§9 8:00) | same |
| `match.mechs` | 16 | 16 (§1) | same |
| `match.spawn_min_separation` | 130 | not stated | new number |
| `match.spawn_zone_fraction` | 0.8 | not stated | new number |
| `match.arena_margin` | 30 | not stated | new number |
| `bot.tick_budget_ms` | 50 | 50 (§2) | same |
| `bot.hello_budget_ms` | 20000 | 20000 (§2) | same |
| `bot.coast_s` | 1 | 1 (§2) | same |
| `bot.offer_timeout_s` | 5 | 5 (§10) | same |
| `bot.max_line_bytes` | 65536 | 65536 (§3) | same |
| `mech.radius` | 2.5 | 2.5 (§5) | same |
| `mech.height` | 9 | 9 (§5) | same |
| `mech.eye_height` | 8 | 8 (§5) | same |
| `mech.muzzle_height` | 7 | 7 (§5) | same |
| `mech.hp` | 1400 | 1400 (§7) | same |
| `mech.walk_speed` | 11.7 | 11.7 (§6 obs example) | same |
| `mech.boost_speed` | 19.5 | 19.5 (§6 obs example) | same |
| `mech.ground_accel` | 58.5 | 58.5 (§7) | same |
| `mech.air_accel` | 12 | 12 (§7) | same |
| `mech.gravity` | 22 | 22 (§7) | same |
| `mech.jump_speed` | 11 | not stated | new number |
| `mech.jet_accel` | 34 | not stated | new number |
| `mech.max_rise_speed` | 10 | not stated | new number |
| `mech.step_up` | 1.2 | 1.2 (§7) | same |
| `mech.max_slope_deg` | 50 | 50 (§7) | same |
| `mech.energy` | 100 | 100 (§7) | same |
| `mech.energy_regen` | 18 | not stated | new number |
| `mech.energy_regen_delay` | 0.6 | not stated | new number |
| `mech.boost_drain` | 17 | not stated | new number |
| `mech.jet_drain` | 15 | not stated | new number |
| `mech.turn_rate` | 4 | 4 (§6 obs example) | same |
| `mech.pitch_rate` | 3 | not stated | new number |
| `mech.min_pitch` | -0.7 | not stated | new number |
| `mech.max_pitch` | 1.3 | not stated | new number |
| `mech.regen_delay` | 5 | 5 (§7) | same |
| `mech.regen_per_s` | 45 | 45 (§7) | same |
| `mech.charge_move_mult` | 0.5 | 0.5 (§7 laser "half speed") | same |
| `mech.self_damage_mult` | 0.5 | 0.5 (§7 mortar) | same |
| `mech.armor` | 0 | not stated | new number |
| `mech.rear_mult` | 1.5 | 1.5 (§7) | same |
| `mech.front_arc_deg` | 180 | 180 (§7) | same |
| `mech.near_range_bonus` | 0 | not stated | new number |
| `mech.vision_bonus` | 0 | not stated | new number |
| `mech.hearing` | 1 | not stated | new number |
| `vision.range` | 200 | 200 (§8) | same |
| `vision.fov_deg` | 120 | 120 (§8) | same |
| `vision.near_range` | 45 | 45 (§8) | same |
| `vision.canopy_blocks` | true | not stated | new number |
| `vision.show_enemy_hp` | true | not stated | new number |
| `vision.memory_s` | 5 | 5 (§8) | same |
| `sound.bearing_noise_deg` | 7 | 7 (§8) | same |
| `sound.near` | 60 | 60 (§8) | same |
| `sound.mid` | 160 | 160 (§8) | same |
| `sound.step_speed` | 5 | 5 (§8) | same |
| `sound.step_every` | 0.6 | 0.6 (§8) | same |
| `sound.range.step` | 40 | 40 (§8) | same |
| `sound.range.boost` | 90 | 90 (§8) | same |
| `sound.range.reload` | 60 | 60 (§8) | same |
| `sound.range.gun` | 320 | 320 (§8) | same |
| `sound.range.mortar` | 420 | 420 (§8) | same |
| `sound.range.explosion` | 420 | 420 (§8) | same |
| `sound.range.laser_charge` | 140 | 140 (§8) | same |
| `sound.range.laser` | 380 | 380 (§8) | same |
| `sound.range.lightning` | 160 | 160 (§8) | same |
| `sound.range.jet` | 90 | 90 (§8) | same |
| `sound.range.death` | 600 | 600 (§8) | same |
| `sound.range.crate` | 220 | 220 (§8) | same |
| `sound.range.npc_gun` | 200 | 200 (§8) | same |
| `sound.range.drop` | 600 | 600 (§8) | same |
| `weapons.gun.damage` | 45 | 45 (§7) | same |
| `weapons.gun.cooldown` | 0.24 | 0.24 (§7) | same |
| `weapons.gun.speed` | 252 | 252 (§7) | same |
| `weapons.gun.range` | 230 | 230 (§6 obs example) | same |
| `weapons.gun.spread_deg` | 0.6 | 0.6 (§6 obs example) | same |
| `weapons.gun.mag` | 12 | 12 (§7) | same |
| `weapons.gun.reload` | 2.4 | 2.4 (§7) | same |
| `weapons.mortar.damage` | 200 | 200 (§7) | same |
| `weapons.mortar.splash` | 160 | 160 (§7) | same |
| `weapons.mortar.splash_radius` | 7 | 7 (§7) | same |
| `weapons.mortar.splash_edge` | 0.3 | 0.3 (§7 "to 30%") | same |
| `weapons.mortar.cooldown` | 2.6 | not stated | new number |
| `weapons.mortar.speed` | 72 | 72 (§7) | same |
| `weapons.mortar.gravity` | 22 | 22 (§7) | same |
| `weapons.mortar.ttl` | 7 | not stated | new number |
| `weapons.mortar.knock` | 16 | 16 (§7) | same |
| `weapons.mortar.knock_up` | 9 | 9 (§7) | same |
| `weapons.mortar.drain` | 45 | 45 (§7) | same |
| `weapons.laser.damage` | 315 | 315 (§7) | same |
| `weapons.laser.charge` | 0.75 | 0.75 (§7) | same |
| `weapons.laser.min_charge` | 0.15 | 0.15 (§7) | same |
| `weapons.laser.min_frac` | 0.35 | 0.35 (§7) | same |
| `weapons.laser.hold_s` | 2 | 2 (§7) | same |
| `weapons.laser.cooldown` | 1.65 | 1.65 (§7) | same |
| `weapons.laser.range` | 280 | 280 (§7) | same |
| `weapons.laser.pierce` | 0 | not stated | new number |
| `weapons.laser.charge_turn_mult` | 1 | 1 (§7) | same |
| `weapons.laser.cookoff` | 0.6 | 0.6 (§7) | same |
| `weapons.lightning.damage` | 60 | 60 (§7) | same |
| `weapons.lightning.cooldown` | 0.25 | 0.25 (§7) | same |
| `weapons.lightning.range` | 45 | 45 (§7) | same |
| `weapons.lightning.cone_deg` | 30 | 30 (§7) | same |
| `weapons.lightning.chain` | 2 | 2 (§7) | same |
| `weapons.lightning.chain_range` | 14 | 14 (§7) | same |
| `weapons.lightning.chain_falloff` | 0.7 | 0.7 (§7) | same |
| `weapons.lightning.energy` | 3 | 3 (§7) | same |
| `weapons.lightning.short_s` | 2 | 2 (§7) | same |
| `projectile.gun_radius` | 0.3 | not stated | new number |
| `projectile.npc_radius` | 0.3 | not stated | new number |
| `cubes.pickup_radius` | 3.5 | 3.5 (§10) | same |
| `cubes.hp_per_cube` | 0.04 | 0.04 (§10) | same |
| `cubes.damage_per_cube` | 0.04 | 0.04 (§10) | same |
| `cubes.stat_cap` | 10 | 10 (§10) | same |
| `cubes.death_drop_extra` | 2 | 2 (§10) | same |
| `cubes.size_per_cube` | 0.05 | 0.05 (§10) | same |
| `cubes.upgrade_thresholds` | [1, 3, 6, 10, 15, 21, 28, 36, 45] | [1, 3, 6, 10, 15, 21] (§10 (list ends "…")) | matches, and extends the list: 28, 36, 45 (last) |
| `crates.count` | 36 | 36 (§7) | same |
| `crates.roof_fraction` | 0.25 | 0.25 (§7 "about a quarter") | same |
| `crates.hp` | 300 | 300 (§7) | same |
| `crates.radius` | 1.4 | not stated | new number |
| `crates.height` | 2.4 | not stated | new number |
| `crates.cubes` | 1 | 1 (§7) | same |
| `loot.pickup_radius` | 4 | 4 (§6/§7) | same |
| `loot.equip_s` | 1 | 1 (§7) | same |
| `loot.floor_count` | 40 | 40 (§7) | same |
| `loot.floor_roof_fraction` | 0.25 | 0.25 (§7) | same |
| `loot.crate_weapon_chance` | 0.5 | 0.5 (§7) | same |
| `loot.death_drop` | 1 | not stated | new number |
| `loot.weights` | {"gun": 0, "mortar": 1, "laser": 1, "lightning": 1} | {"gun": 0, "mortar": 1, "laser": 1, "lightning": 1} (§7) | same |
| `npc.count` | 12 | 12 (§7) | same |
| `npc.hp` | 350 | 350 (§7) | same |
| `npc.radius` | 1.8 | 1.8 (§5) | same |
| `npc.height` | 3.5 | 3.5 (§5) | same |
| `npc.speed` | 5 | not stated | new number |
| `npc.leash` | 30 | 30 (§7) | same |
| `npc.chase_leash` | 60 | 60 (§7) | same |
| `npc.aggro_range` | 45 | 45 (§7) | same |
| `npc.deaggro_range` | 90 | 90 (§7) | same |
| `npc.spawn_clear` | 0 | not stated | new number |
| `npc.damage` | 25 | 25 (§7) | same |
| `npc.cooldown` | 1 | 1 (§7) | same |
| `npc.projectile_speed` | 90 | 90 (§7) | same |
| `npc.spread_deg` | 2.5 | not stated | new number |
| `npc.cubes` | 2 | 2 (§7) | same |
| `drops.times` | [70, 140, 210] | [70, 140, 210] (§7) | same |
| `drops.fall_s` | 25 | 25 (§7) | same |
| `drops.radius` | 8 | 8 (§7) | same |
| `drops.capture_s` | 4 | 4 (§7) | same |
| `drops.cubes` | 3 | 3 (§7) | same |
| `drops.repair` | 1 | 1 (§7 "full HP") | same |
| `drops.spread` | 0.7 | not stated | new number |
| `debug.max_lines` | 64 | 64 (§6) | same |
| `debug.max_points` | 64 | 64 (§6) | same |
| `debug.max_text` | 16 | 16 (§6) | same |
| `debug.max_text_chars` | 80 | 80 (§6) | same |
| `debug.max_bytes` | 8192 | 8192 (§6) | same |
| `debug.max_match_bytes` | 8000000 | 8000000 (§6 "8 MB") | same |
| `debug.hold_s` | 0.5 | 0.5 (§6) | same |
| `replay.frame_every` | 2 | not stated | new number |
| `zone.start_center` | [41.3, -72.8] | [41.3, -72.8] (§9) | same |
| `zone.start_radius` | 560 | 560 (§9) | same |
