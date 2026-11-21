# Opponent behaviour seen in `check/stream.jsonl.gz`

Researcher (offline), 2026-11-22. Scripts (stdlib, scratchpad, not committed): `hb.py` (per-obs timeline of self, visible mechs, events, beams, projectiles, sounds) and `hb2.py` (aim residual vs ideal lead, gun-sound bearings vs bearing to mech 10). Run as `python -I -X utf8 hb.py check/stream.jsonl.gz`.

## What this recording is, and its limits

- **Mode: free-for-all, not the squad practice.** `hello.config.match` = `{mechs: 16, duration_s: 480, ...}`; no key anywhere in the config contains `squad`, `team`, `mode` or `house`. Three other mechs die at t 17-25 (`death` sounds, `alive` 16 -> 13) while only mech 10 is in contact with us, and "far" gun fire comes from bearings 1.7-2.9 (not mech 10's 0.4-0.97) without ever hitting us. So mechs were fighting each other. **We cannot tell whether mech 10 or anyone else is a house bot**; the identity of the opponents is not in the stream.
- Only 36.8 s (300 obs, a 6.4 s gap at 29.5-35.9), all in zone phase 1 hold. Nothing about zone behaviour, upgrades, drops, late game, hunters or squads.
- One opponent ever visible (id 10, gun + laser). All numbers below are **n = 1 bot, one fight** — evidence of what a bot on this engine does, not a calibration of the house tiers.
- Projectiles carry no owner; shooters are attributed by sound bearing (noise 7 deg) and `damaged.by`.

## 1. Reaction time to being hit (A5)

- Before our first hit, mech 10 was aiming 0.1-0.8 rad off us and facing away (our first hit, t 5.7, was `rear: true`, 67.5). It did **not** react to our two gun shots at t 5.2 and 5.5 (140 m, well inside gun hearing 320 m); it was outside its 120 deg FOV of us.
- t 5.7 hit -> aim swings toward us from the next obs (2.21 -> 2.61 -> 3.01 -> -2.87 rad, about 4 rad/s = `turn_rate`) -> **on target (within 0.06 rad) at t 6.3: 0.6 s** after the hit.
- Laser charge starts t 7.1 (1.4 s after hit), first laser damage on us t 7.9 (**2.2 s**), first gun damage t 9.3. Gun projectiles toward us visible from t 8.0.
- After that it stayed on us for the whole stream (re-engaged at t 18.0 and 35.9 when LOS returned) and killed us. A5 (shoots back at whoever shoots it) holds for this bot, with ~0.6 s turn + ~1.5 s to first shot.

## 2. Turning toward unseen gunfire (A12)

- Only the case above: our shots at t 5.2/5.5 while unseen did not turn it within 0.5 s; the hit did, immediately. Weak evidence (n = 1, and it may have been busy with another target) that **sound alone did not trigger a turn; damage did**.
- When LOS broke (t 13.2-18.0, 26.0-35.9) it came back into view **closer** each time (150 -> 100 -> 55 m), i.e. it kept chasing us after contact. Whether it used sound or memory to do so cannot be separated.

## 3. Aim quality and lead (A10)

- Aim residual (its yaw minus true bearing to us) vs ideal gun lead (our tangential speed x d / 252 m/s), 67 obs with our tangential speed > 3 m/s: mean |residual| 0.026 rad, mean |residual - lead| 0.023 rad, mean bias 0.007 rad. Clear runs track the lead: t 8.5-8.9 (we strafed -14..-19 m/s, lead -0.054..-0.076, residual -0.018..-0.067); t 20.3-20.9 (lead 0.018-0.035, residual 0.021-0.035). **It leads moving targets.** Residual noise ~0.02 rad sits inside the A10 guess for hard/expert (0.006-0.03).
- Gun hit rate: 10 "mid" gun sounds from its bearing at ~150 m (t 8.0-12.0) -> 5 gun `damaged` events: **~50% at 150 m**. At 100 m: 1 shot, 1 hit (t 19.5/19.8). At 55-60 m: 3 gun hits in 0.9 s (t 36.1-36.8). Shots came every 0.3-0.5 s, not at the 0.24 s cooldown (paced fire).
- Laser: 4 hits of 315 from 5 beams; full 0.8 s charges (t 7.1->7.9, 9.8->10.6, 18.5->19.3) at 100-150 m. The one miss (t 24.4) was a 0.2 s charge fired while jetting, beam passed 22 m from us. Laser 1260 of our 1390 damage.
- For comparison our own gun: 10 hits.

## 4. Movement, cover, loot, zone (A11, A13)

- **Boost: yes.** Speed 19.4 m/s at t 18.0-18.2 (`boost_speed` 19.5) while closing on us.
- **Jet: yes, but not onto a roof here.** t 23.1-24.7 vz +8.9 (= `max_rise_speed` ~10), z 2 -> 21, then fell (vz -16 at t 26.0): a jet hop in the open, during which it fired the missed laser.
- **Strafing/juking: yes.** Its velocity reverses direction every ~0.3-0.6 s during every exchange (e.g. t 7.5-8.0 vx -9.7 -> +7.7), 6-18 m/s.
- **Cover:** LOS broke twice; cannot attribute to either side.
- **Loot: yes.** Mechs spawn with a gun only (our own self at t 0); mech 10 already had a laser at t 4.9, so it picked one up within 5 s.
- **Regen:** its HP 1029 -> 1247 between t 25.0 and 35.9 while out of contact (HP regen used, consistent with backing off).
- **Zone:** no data (in_zone all stream, no zone deaths visible, phase 1 hold only).

## 5. Cooperation

- None visible: FFA, others die to each other early, no shared-target pattern. **The stream says nothing about squad behaviour (A2, A7, A8, A9).**

## Takeaways for the sim (A9-A13)

1. Bots that are shot turn at `turn_rate` and fire back within ~1.5 s; laser carriers open with a full charge.
2. Aim noise ~0.02 rad with full lead is a fair "hard" setting; gun ~50% at 150 m.
3. Bots boost, jet-hop and juke in fights, and loot a laser in the first seconds. The A11 "walk only, never jet" guess is too passive for at least one engine bot.
4. Sound-only reaction: weak evidence of none (A12 stays a guess).
