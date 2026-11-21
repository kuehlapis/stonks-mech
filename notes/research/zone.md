# Zone

Source: `config.zone` in `notes/research/hello.json`: `start_center` (41.3, −72.8), `start_radius` 560, 6 phases. Speeds from `config.mech`: `walk_speed` 11.7, `boost_speed` 19.5, `energy` 100, `boost_drain` 17/s, `energy_regen` 18/s after `energy_regen_delay` 0.6 s. Rules: protocol §9. Table computed by a scratch script (output pasted below unchanged).

## Phase table

Phase k's damage applies from its hold through its shrink (§9). The circle holds during the hold and moves linearly (center and radius) to the next circle during the shrink.

| # | hold (s) | shrink (s) | radius | dps | hold window (t, s) | shrink window (t, s) | outside-zone life at 1400 HP |
|---|---|---|---|---|---|---|---|
| 1 | 60 | 50 | 560 → 380 | 20 | 0 – 60 | 60 – 110 | 70 s |
| 2 | 45 | 40 | 380 → 240 | 35 | 110 – 155 | 155 – 195 | 40 s |
| 3 | 35 | 35 | 240 → 140 | 60 | 195 – 230 | 230 – 265 | 23 s |
| 4 | 30 | 30 | 140 → 70 | 100 | 265 – 295 | 295 – 325 | 14 s |
| 5 | 25 | 25 | 70 → 25 | 160 | 325 – 350 | 350 – 375 | 8.8 s |
| 6 | 15 | 25 | 25 → 0 | 260 | 375 – 390 | 390 – 415 | 5.4 s |

The last circle reaches **radius 0 at 415 s (6:55)**, matching §9. After that every survivor is outside the zone, takes 260 HP/s (armor does not help, regen is off, §7), and the match is decided by who has the most HP at 415 s (1400 HP → 5.4 s; 2129 with 3 plating → 8.2 s; 2981 with 3 plating + 10 cubes → 11.5 s). The 8:00 timeout is effectively never reached.

## How far a mech gets

Boost is energy-limited: a full tank boosts 5.88 s (114.7 m); refilling 0→100 takes 0.6 + 5.56 = 6.16 s, during which the mech can still walk (walking costs no energy). Best sustained mix (boost a tank, walk while it refills) averages **15.5 m/s**. "Boost" below starts with a full tank and alternates that way.

| # | walk, hold | walk, shrink | boost, hold | boost, shrink | worst-case gap 2·(r₀ − r₁) | max boundary speed (m/s) | time to walk the worst-case gap |
|---|---|---|---|---|---|---|---|
| 1 | 702 m | 585 m | 931 m | 783 m | 360 m | 7.2 | 30.8 s |
| 2 | 526 | 468 | 710 | 636 | 280 | 7.0 | 23.9 s |
| 3 | 410 | 410 | 547 | 547 | 200 | 5.7 | 17.1 s |
| 4 | 351 | 351 | 489 | 489 | 140 | 4.7 | 12.0 s |
| 5 | 292 | 292 | 391 | 391 | 90 | 3.6 | 7.7 s |
| 6 | 176 | 292 | 244 | 391 | 50 | 2.0 | 4.3 s |

- **Worst-case gap:** the next circle lies inside the current one, so `|c₀ − c₁| ≤ r₀ − r₁`, and the farthest point of the current circle is `r₀ + |c₀ − c₁| − r₁ ≤ 2(r₀ − r₁)` from the next circle.
- **Max boundary speed:** a point's distance to the moving edge shrinks at most `(|c₀ − c₁| + (r₀ − r₁)) / shrink_s ≤ 2(r₀ − r₁)/shrink_s`. Walking (11.7 m/s) beats it in every phase, but only by 1.6× in phases 1–2: around buildings (path length / straight line ≈ 1.3, an estimate, not measured) the margin in phase 1 drops to 11.7 / 1.3 = 9.0 vs 7.2 m/s.
- Every worst-case gap is walkable within its hold, even at a 1.3 path factor (40, 31, 22, 16, 10, 5.6 s vs holds 60, 45, 35, 30, 25, 15 s).
- Recorded match: phase-1 next circle center (−42.12, 7.11), offset 115 m from the start center (max allowed 180). `zone` was identical in all 300 observations (t 0 – 36.8, all phase 1), so the stream does not show when phase 2's next circle is announced. Assumption to verify: it appears at the hold start (t = 110).

## Latest safe departure rule

**Key fact:** the next circle is inside every intermediate circle of the shrink (for s in [0,1]: `|c(s) − c₁| + r₁ = (1−s)|c₀ − c₁| + r₁ ≤ (1−s)(r₀ − r₁) + r₁ = r(s)`). So **a mech inside the next circle at `shrink_start` stays inside through the whole shrink.**

Rule (conservative, uses walking only so energy stays free for fights):

```
need   = max(0, |pos − next_center| − next_radius + margin)    # straight-line metres to cover
t_go   = shrink_start − need × path_factor / walk_speed − slack
depart when t ≥ t_go (or now, if t_go has passed)
```

with `margin` ≈ 15–20 m (stay off the edge; fights push you around), `path_factor` 1.3 until the nav module can give a real path length, `slack` 3–5 s. In phase 1 a mech at the far edge must leave by about t = 60 − 40 = 20 s; in phase 6 by 375 + 15 − 5.6 ≈ 384 s, though the circle at that point is only 25 m wide.

Fallback check every tick during a shrink (catches being knocked out or late): compute the circle at `t + lookahead` by linear interpolation between (`center`, `radius`) and (`next_center`, `next_radius`) over [`shrink_start`, `shrink_end`], and move toward `next_center` if `|pos − c(t+L)| > r(t+L) − margin`, with `L` ≈ 3 s.

For the last phase (radius 0) the rule cannot keep a mech inside: plan to be at the final center with maximum HP at 415 s (full regen needs 5 s without damage, then 45 HP/s, and regen stops once outside).
