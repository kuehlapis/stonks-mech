# Movement and survival when hunted: outside sources translated

Researcher (online), 2026-11-22. Adds to `notes/ideas/movesets.md`; does not repeat its boost-strafe, hop, backpedal or basic duck ideas.
Numbers from `notes/research/config.md` (`hello.config`).

## 1. Tie strafe reversals to bullet flight time, not a fixed 0.25–0.7 s

Source: RoboWiki *Random Movement* (https://robowiki.net/wiki/Random_Movement): good bots set the reversal chance from distance and enemy bullet speed, pick a destination reachable within the enemy shot's flight time, and change velocity every 5–20 ticks, not every tick. Purely uniform random motion is nearly linear about 1/4 of the time and so easy to hit.

Rule: `flight = dist / gun_speed` (252 m/s). Reverse after a random `U(0.6, 1.4) × flight`, clamped to ≥ 0.25 s (accel limit). Never keep one direction longer than `2 × flight`. At 130 m that is 0.31–0.73 s (today's range by chance); at 50 m it would want 0.12–0.28 s, so the clamp wins and close in we rely on hops; at 230 m 0.55–1.3 s, longer than today, which gives more sideways distance per shot.
Expected effect: fewer gun hits taken at long range; small (+0.1–0.3 place). A/B: `m_flight` vs `s_base`, same seeds, measure gun damage taken per second in sight.

## 2. Minimise the count of shooters with line of sight (minimum-risk movement)

Source: RoboWiki *Melee Strategy* (https://robowiki.net/wiki/Melee_Strategy): score candidate points with a risk function (inverse-square distance to threats, weighted by how likely each one targets you), re-evaluate often, and don't sit still long. In mechfight the 15 bots share vision and hunt us, so "likely to target us" is everyone; what we control is **how many have line of sight at once**.

Rule (survival.py, every 0.5 s, spread over ticks): sample 8 points at 15 m around us; risk = Σ over known enemies with LOS to the point of `1/d²` (×2 if it holds a laser at < 140 m, ×2 for lightning at < 50 m) + zone penalty. Move to the lowest. Uses `world.los` already in the World module.
Expected effect: the biggest gain here, since being shot by 3+ at once is what kills us; guess +0.5–1.0 place. A/B: `s_minrisk` vs `s_base`; proxy = mean number of enemies in sight per tick and time alive.

## 3. Jiggle peek against hitscan lasers

Source: CS2 peeking guides (https://dignitas.gg/articles/cs2-how-to-improve-your-peeks, https://metabot.gg/en/cs2/guides/cs2-peeking-guide-wide-jiggle-shoulder): a jiggle peek shows you for a fraction of a second to bait a shot or gather info; the shoulder peek is the jiggle aimed at snipers (one-shot hitscan) so they waste the shot. Wide peek only when you already know where the enemy is.

Translation: a laser is hitscan with a visible charge (0.75 s full, 0.15 s minimum, 1.65 s cooldown). Behind cover against a charging laser: step out for ≤ 0.3 s and back. If it fires (beam event or `charging` goes false), we have 1.65 s; wide-peek and spend it shooting, then back in before 1.5 s. If it holds the charge, it is at half speed and we stay hidden at no cost. This extends `movesets.md`'s "peek after the beam" with the bait step that makes the beam come.
Expected effect: turns laser duels in our favour; +0.2–0.5 place if lasers are common in the squad. A/B: `s_jiggle` vs `s_duck30`; proxy = laser damage taken vs dealt.

## 4. Peek from a new spot each time

Source: same peek guides (re-peeking the same angle is punished because the holder pre-aims it). Rule: after ducking, re-expose from the other side of the cover or by a hop over it (2.75 m apex), alternating. Cheap add-on to 3. A/B inside `s_jiggle` with and without.

## 5. Hunted by many: fight only at the edge of the pack, and always toward cover

Source: Melee Strategy (avoid the middle, let enemies get in each other's way, finish weak targets, don't switch targets often).
Rule: when ≥ 2 enemies are in sight, choose targets only among the nearest and never advance past the line from the pack's centroid; retreat direction = away from the centroid, biased to the nearest LOS-blocking prism. Keep one target until it leaves sight or dies.
Expected effect: fewer pincer deaths; included in the 2 sweep. A/B: target-switch count and deaths with ≥ 3 enemies in sight.

## Priority

1. Minimum-risk LOS count (2), largest expected gain. 2. Jiggle peek vs laser (3+4). 3. Flight-time reversals (1), cheap.

## Sources

- https://robowiki.net/wiki/Random_Movement
- https://robowiki.net/wiki/Melee_Strategy
- https://dignitas.gg/articles/cs2-how-to-improve-your-peeks
- https://metabot.gg/en/cs2/guides/cs2-peeking-guide-wide-jiggle-shoulder

Effects are reasoned estimates, not measured.
