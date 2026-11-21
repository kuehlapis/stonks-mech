# Online research: bot-programming competitions

Researcher (online), iteration 1, 2026-11-21. Robocode is the closest analogue (real-time tanks, no lock-on, bullets with travel time, melee mode with many bots). Robocode melee scoring also pays for survival: each surviving bot gets 50 points every time another bot dies (https://robocode-dev.github.io/tank-royale/articles/scoring, snippet), so melee wisdom carries over to `16 − place`.

## Robocode: targeting

### 1. Linear and circular targeting beat simple movers; statistical guns beat everyone else

- Linear targeting assumes constant heading and speed; the exact form solves a quadratic for intercept time; predicted points are clamped so the target "stops at the wall". Works when the target moves straight at steady speed, or at short range with a fast bullet. (https://robowiki.net/wiki/Linear_Targeting, fetched)
- Circular targeting steps the target forward with constant speed *and* turn rate until bullet flight time matches; clamps at walls. (https://robowiki.net/wiki/Circular_Targeting, fetched)
- GuessFactor (GF) targeting: normalize where the target ended up between "max forward" (+1) and "max backward" (−1) over the bullet's flight, keep segmented hit statistics (by distance, velocity, wall proximity), fire at the most-visited factor. "One of the most popular and successful methods of targeting in all of Robocode"; David Alves: nearly any method works "as long as it isn't simple linear or circular targeting" against good movers. (https://robowiki.net/wiki/GuessFactor_Targeting_(traditional), fetched)
- Play-It-Forward: replay a logged movement sequence of the target from its current state to find where it will be. (https://robowiki.net/wiki/Play-It_Forward, fetched)

**For mechfight:** start with exact linear lead for the gun (`weapons.gun.speed` 252 m/s, origin 3.0 m out along the aim from muzzle height `self.stats.muzzle_height`, target center = `pos.z + 4.5 × (1 + 0.05 × cubes)`). Flight time at 100 m is 0.40 s; a walking target (11.7 m/s) moves 4.6 m, nearly 2× the mech radius, so no lead means mostly misses. Clamp predicted points at walls using World (a target walking into a wall stops). Only consider a GF-style gun (per-enemy-id histograms of lateral factor) if the local hit-rate proxy (`objective.md`: ≥ 40% at 50–150 m) stalls below target. Built-in bots probably move simply, so linear may be enough. That's an assumption; the stream in `check/stream.jsonl.gz` can test it by checking how straight enemy `vel` stays over 0.4–0.8 s.

### 2. Fire only when the shot can hit

- Melee Strategy: don't waste shots; use enough power to finish a nearby bot before others take it; target whoever you're most likely to hit. (https://robowiki.net/wiki/Melee_Strategy, fetched)

**For mechfight:** fire the gun only when the angle between our *actual* aim (`self.aim`, the torso lags at `turn_rate` 4 rad/s) and the intercept direction is below `atan(target_radius / distance) + spread`. That's 0.95° at 150 m for an uncubed mech (`spread_deg` 0.6). Ammo and reload matter (12 rounds, 2.4 s reload), and gunfire is audible at 320 m. Reload early (`reload: true`) when no target is visible and `ammo < 6`.

## Robocode: movement

### 3. Minimum-risk movement is the standard melee method

- Two parts: a candidate-point generator and a risk function; move to the lowest-risk point. Candidates: points at regular angles around you at random distances (HawkOnFire), or field subdivision (FloodHT). Risk terms: enemy energy and distance; "whether they would become the closest bot to an enemy, which makes them more likely to be targeted"; repel the battlefield center; time spent in the same area; moving straight toward or away from an enemy is riskier than perpendicular. Called "extremely effective", and "less likely to converge at some happy local minimum" than anti-gravity. (https://robowiki.net/wiki/Minimum_Risk_Movement, fetched)
- Top melee bots (Coriantumr, Shiz, HawkOnFire) use minimum-risk movement. (https://robowiki.net/wiki/Melee_Strategy, fetched)

**For mechfight:** this is the right skeleton for the Survival/Navigation "where to stand" decision. Each decision, evaluate ~16 candidate points (8 bearings × 2 radii, 15 m and 35 m) that are walkable and reachable (World), and pick the lowest risk:
`risk = Σ_enemies w_e × threat_e / max(d,10)² × (2 if we'd be that enemy's nearest mech) × (1 + LOS_e)`
`+ zone_term (∞ if outside next circle when the shrink would catch us) + 0.3 × same_area_term − cover_bonus`,
where `threat_e` scales with enemy HP × cube damage multiplier and is higher for weapons that beat ours. Keep the current target unless the new best is ≥ 15% lower risk (anti-dither). Cost: 16 × ≤ 5 tracked enemies = 80 LOS checks per decision. Spread them over ticks if a check costs more than ~0.1 ms in Python.

### 4. Anti-gravity: simpler, but local minima and weight tuning

- Sum inverse-square repulsion from each point (enemies, walls, center); move along the result. Hard to balance weights as bot counts change. (https://robowiki.net/wiki/Anti-Gravity_Movement, fetched)

**For mechfight:** use as a cheap fallback when the world model failed to load (CLAUDE.md "never crash" rule): repel from tracked enemies by `1/d²`, attract toward `next_center` when outside `0.8 × next_radius`.

### 5. Dodging: random direction changes beat predictive guns; stop-and-go beats linear guns

- Random movement: reverse orbit direction at random intervals of roughly 5–20 ticks (not every tick, because acceleration is limited); pick destinations perpendicular to the enemy; pure randomness still drifts straight toward the enemy about a quarter of the time, so filter destinations. (https://robowiki.net/wiki/Random_Movement, fetched)
- Stop-and-go: if the enemy fires while you're still, start moving; if moving, stop. Beats head-on, linear and circular guns; loses to guns that average velocity. (https://robowiki.net/wiki/Stop_And_Go, fetched)
- Wave surfing: model every enemy shot as an expanding wave, learn which firing angles the enemy uses, move to the safest reachable spot on the nearest wave. Since 2010 the top 40 Robocode duelists all surf. (https://robowiki.net/wiki/Wave_Surfing, fetched)

**For mechfight:** better than Robocode, we *see* enemy bullets and shells in `obs.projectiles` with `pos` and `vel`, and hear `gun` sounds (Perception) [rule]. Rules:
- **Strafe** perpendicular to the shooter's bearing when engaged, and reverse at random every 0.4–1.5 s (4–15 decisions). Ground accel 58.5 m/s² reaches 11.7 m/s in 0.2 s.
- **Dodge visible bullets:** for each projectile whose closest approach to our predicted center is < `radius + 0.3 + 0.5` m within the next 0.5 s, pick the move direction (of 8) that maximizes the miss distance. Gun bullets fired from ≳ 110 m are dodgeable on sight. From 100 m a bullet takes 0.40 s. Minus up to 0.1 s before we see it, a standing mech moves ≈ 2.3 m sideways (accel 58.5 m/s², then 11.7 m/s), just short of the 2.8 m needed (radius 2.5 + bullet 0.3). Closer than that, only pre-emptive strafing helps.
- **Stop-and-go against gunfire** we can't see (heard only): when a `gun` sound arrives from a bearing, flip between moving and stopping.
- Full wave surfing needs to learn per-enemy aim; probably overkill. Simple linear leading by built-ins is beaten by direction changes alone (assumption to verify in the sim).

### 6. Melee radar = our vision wedge

- Spinning radar is simplest; "Oldest Scanned" turns toward the enemy not seen for longest; "Gun Heat Lock" locks on the target only when about to fire, else sweeps. (https://robowiki.net/wiki/Melee_Radar, fetched)

**For mechfight:** aim is also our eyes (120° `vision.fov_deg`, 200 m), and tracked mechs drop after 5 s (`vision.memory_s`). Use oldest-scanned: when not about to fire, turn the aim toward the bearing (from sound or last track) whose info is oldest. Turning 360° takes 1.57 s at 4 rad/s. Lock on the target only for the 0.2–0.5 s before a shot (gun heat lock ≈ `weapons[i].cooldown < 0.2`). Constraint from rear armor: keep a known threat within ±90° of aim (front arc 180°). That still lets the wedge cover threat −150° to +150°.

### 7. Target choice

- Default nearest; also weigh lowest-energy target and whoever shoots you; avoid thrashing (switch only when clearly better, e.g. 10%); "count how many other bots are closer to an enemy than you; if zero or one, it's probably aiming at you". (https://robowiki.net/wiki/Melee_Strategy, fetched)

**For mechfight:** target score = `hit_prob(d, lateral speed) × (1 + 1.5 × [hp_e < 300]) × (2 if it damaged us in the last 3 s) × triangle_bonus`. Keep the current target unless a new one scores ≥ 1.2×. Finishing a low-HP mech also drops all its cubes + 2 (`cubes.death_drop_extra`).

### 8. Corners and survival in melee

- Corner movers often last longest because corners usually have fewer nearby bots; middle is fine early if others are outside, but with 4–5 bots left you won't last long in the middle. Survival pays (≈ 100 points per bot outlasted in classic scoring). (https://robowiki.net/wiki/Melee_Strategy, fetched)

**For mechfight:** same idea as the BR "edge" (see `online-battle-royale.md` §3). Our "corner" is a pocket of cover at the inner edge of the next circle, away from where enemies are.

## Halite, CodinGame, Battlecode, StarCraft AI: what separated top bots

### 9. A local match runner against old versions was the #1 tool

- Halite III (#66, #1 JS bot): wrote a local runner against older versions, played each pairing twice with sides swapped, made the bot deterministic so games replay identically; simple heuristics beat a "theoretically optimal" one in testing; ML tuning of magic numbers failed for lack of data. (https://stonet2000.github.io/postmortem/, fetched)
- reCurse, CodinGame Fall Challenge 2023 winner: a multi-threaded local referee "100% worth it"; kept every best model in a local leaderboard; a steady local Elo gain **hid an overfit** to self-play, so keep opponents varied. (https://gist.github.com/reCurs3/7d4eb5b952790e3009337f61c3341074, fetched)
- reCurse, Winter Challenge 2024 winner: "local testing above all", using PsyLeague to rate versions; used the 1000 ms first turn for heavy precompute. (https://gist.github.com/reCurs3/fea106bea9c55389706e959b97f956c0, fetched)
- reCurse, Summer Challenge 2024 (2nd): adding noise was worse in local tests but better against real opponents. (https://gist.github.com/reCurs3/40793036b9800472eb219136a33f6997, fetched)
- Battlecode 2019 (XSquare, many-time top finisher): "our biggest mistake ... we barely scrimmed after seeding ... and we didn't see the meta shift". (https://battlecode.org/assets/files/postmortem-2019-oak.pdf, text extracted)
- Halite: many tuned versions of nearly identical bots ended with similar ratings, so tuning time was better spent elsewhere (search snippet, shummie post-mortem https://shummie.gitbooks.io/halite-postmortem/content/history.html).

**For mechfight:** the Tester's simulator is the highest-leverage tool. It must (a) run our bot against copies of the example bot *and* against other behavior styles (campers, rushers, zone-walkers), because overfitting to the example bot is the trap reCurse and XSquare describe; (b) be seeded and deterministic for A/B pairs; (c) report mean place over ≥ 100 matches with a confidence interval. With 48 real matches the noise is ±0.7, so don't chase local gains under ~0.5 place. Use the 20 s `hello` budget (`bot.hello_budget_ms`) for map precompute, like reCurse used his long first turn, but keep `ready` ≤ 5 s per `objective.md`.

### 10. Robustness wins tournaments

- StarCraft AI (AIIDE/CIG): in 2010 crashes in the BWTA terrain library hit so many bots that organizers named no winner; in 2015 two bots withdrew after crashing in most games; 2019 rules made exceeding the compute limit a loss; PurpleWave (2017) made "robustness of the overall behavior" its main goal: avoid blocking, indecision, predictability. (Churchill's reports https://www.cs.mun.ca/~dchurchill/starcraftaicomp/report2013.shtml, report2015.shtml; search snippets, the site refused connection.)
- An "old-fashioned" rule-based bot won a 2018 StarCraft AI tournament (https://www.technologyreview.com/the-download/612438/an-old-fashioned-ai-has-won-a-starcraft-shootout/, snippet).

**For mechfight:** our map-analysis code is exactly the BWTA risk. Wrap World loading so failure falls back to map-free play. Cap per-tick work with a time check (`time.perf_counter()`), and treat "stuck against a wall for > 2 s" (indecision/blocking) as a bug the simulator counts.

### 11. Simulation plus search where the game is cheap to simulate

- Coders Strike Back (CodinGame): the common top method was a game-physics clone plus a genetic algorithm over move sequences; predicting the opponent for ~30 ms first mattered ("simulating without predicting the opponent moves doesn't work so great"). (https://www.codingame.com/blog/evolutionary-trajectory-optimization/, https://medium.com/@jstnlef/postmortem-of-coders-strike-back-f4d642d270ca, snippets)

**For mechfight:** full-match search is out of reach in Python at 50 ms. A *local* forward simulation is in reach: our own movement for 0.5–1 s (accel 58.5, walls via World) against visible projectiles, to choose a dodge (≈ 8 candidates × 5 steps). That is "precise prediction" in Robocode terms.

### 12. Rules plus learning beats pure learning on big FPS maps

- Arena Breakout (Tencent): navmesh pathing and rule-based shooting combined with RL; win rate about 30% above pure RL at equal training; RL shooting alone was erratic. (https://arxiv.org/html/2410.04936v1, fetched)

**For mechfight:** no learning is needed or feasible here (standard library, 1 CPU, no training infrastructure). Rule-based aim and pathing are what industry and competition winners use for this layer.

## Not covered

- I did not find a Halite II/III winner's own write-up or a microRTS/AI Arena write-up worth citing. The AIIDE reports and the Killzone slides could not be read (connection refused / image-only PDF).
