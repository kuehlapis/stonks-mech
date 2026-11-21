# Online research: game AI methods for a 50 ms Python budget

Researcher (online), iteration 1, 2026-11-21. Budget from `objective.md`: `act()` mean ≤ 15 ms, p99 ≤ 35 ms, standard library only, 1 CPU; startup ≤ 5 s target (20 s hard limit). Several primary sources (Game AI Pro PDFs, Killzone slides, Gamasutra) wouldn't render through my fetch tool; where I rely on search snippets I say so.

## 1. Decision structure: small FSM on top, utility scoring inside

- F.E.A.R. used an FSM with only **three states** (Goto, Animate, UseSmartObject) and an A* planner (GOAP) to choose actions. The point: keep the state machine tiny and move choice into a scorer/planner. (Orkin, GDC 2006, https://pages.cs.wisc.edu/~dyer/cs540/handouts/gdc2006_orkin_jeff_fear.pdf and https://gdcvault.com/play/1013394/Three-States-and-a-Plan, snippets)
- Utility AI (Dave Mark, "infinite axis"): normalize each consideration to 0–1 through a response curve and combine them to score each action. Adding considerations is cheap because they're normalized. (https://www.gameai.com/manuals/index.php/Response_Curve and search summaries; I couldn't read the Game AI Pro chapter text.) Common practice: multiply considerations so any 0 vetoes, and add an inertia bonus to the current action to stop dithering (general knowledge; same anti-thrash rule as Robocode, see `online-bot-competitions.md` §3, §7).
- Quake III bots used fuzzy-logic weights for item/goal desire; a 2009 thesis found other methods beat it (https://www.ai.rug.nl/~mwiering/thesis_j_g_gerrits.pdf, snippet).

**For mechfight (Brain):** a handful of goals scored each decision by utility, no planner:
`ZONE` (urgency = clamp((travel_time × 1.5 + 5 − time_to_shrink)/10)), `FIGHT` (go/no-go from `online-battle-royale.md` §1 × target score), `DISENGAGE` (our HP fraction low × incoming dps), `HEAL` (hidden, no damage for 5 s: `mech.regen_delay`), `LOOT` (cube or pickup value / travel seconds), `DROP` (uncontested supply drop), `HIDE` (default). Multiply considerations; add +0.15 to the current goal. GOAP and behavior trees are more machinery than seven goals need. A BT is fine if the team prefers it, but utility handles "how much" questions (HP, distance, time) more naturally.

## 2. Position choice: evaluate a few candidate points, don't build a full influence map

- Killzone (Guerrilla, GDC Europe 2005): "dynamic tactical position evaluation functions" score candidate positions by a **weighted sum** of cover from the primary threat, cover from secondary threats, proximity and preferred fighting range, then pick the best; the same scoring drives tactical pathfinding. Replaced hand-placed hint nodes. (https://www.guerrilla-games.com/media/News/Files/gdce05_killzone_ai.pdf, snippets; slides are image-only.)
- Influence maps (Dave Mark, Game AI Pro 2 ch. 30): layered grids of threat/proximity used to judge "how threatened am I", find safe retreat spots, and find enemy clusters for area weapons; the map gives information only; decay higher for local tactical maps. (https://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter30_Modular_Tactical_Influence_Maps.pdf, snippets)

**For mechfight (Survival/Navigation):** the map is 1070 × 724 m. A 4 m threat grid is 48k cells, too many to refresh in Python every 0.1 s. Use the Killzone/Robocode minimum-risk approach instead: 12–24 candidate points per decision, scored by (a) count of tracked enemies with LOS to the point, from World's LOS, (b) distance to preferred range for our weapon, (c) inside the next circle with margin, (d) a static precomputed "cover value" per 8 m cell (fraction of 16 directions blocked within 30 m), built at startup. Precompute is 134 × 91 cells × 16 rays. Check its cost against the 5 s `ready` target; if it's too slow, compute lazily per cell and cache.

Use a tiny influence map only for **sound**: a 16-sector bearing histogram with 5 s decay of `sounds[]` by kind. That's enough to choose a "quiet side" and an "oldest-scanned" look direction.

## 3. Aiming: closed-form intercept, ballistic arc, hitscan timing

- Constant-velocity intercept: solve the quadratic for time of impact, aim at `target + v × t`; if no positive root, no solution; with a moving shooter whose bullets don't inherit shooter velocity, ignore shooter motion. Target acceleration turns it into a quartic, solved numerically. (gamedeveloper.com "Predictive aim mathematics" and "Shooting a moving target", gamedev.net "Shooting At Stuff", snippets; gamedeveloper returned 403.)
- Ballistic angle to hit (x, y) with speed v, gravity g: `θ = atan((v² ± √(v⁴ − g(g x² + 2 y v²))) / (g x))`; the two signs are the low and high arcs; negative discriminant = out of reach; max flat range `v²/g`. (https://en.wikipedia.org/wiki/Projectile_motion, fetched)

**For mechfight (Combat):**
- **Gun:** `r = target_center − origin`, `v = target.vel`, `s = weapons.gun.speed` (252, or more after `gun_velocity`). Solve `(v·v − s²) t² + 2 (r·v) t + r·r = 0`, smallest positive t. Origin is the muzzle (`pos.z + self.stats.muzzle_height`) plus 3.0 m along the aim, so do one fixed-point iteration. Ground mechs: hold the target's z at its current ground height, or at terrain height at the intercept point (World). Clamp the intercept to walls (a target walking into a wall stops). Assumption to verify: bullets don't inherit shooter velocity (protocol says shots leave along the aim at `speed`).
- **Mortar:** `v = 72`, `g = 22`, tube at `pos.z + 9.5 × scale`. Use the **low arc** against movers (shorter flight: ≈ 1.4 s at 100 m) and the high arc only to clear a wall (the pitch cap `max_pitch` 1.3 rad ≈ 74° limits it). Iterate the target prediction 2–3 times on flight time. Against a mover, aim at the *ground* under the predicted feet: splash 160 falling to 30% at 7 m and blocked by walls, so a near miss still pays. Never fire if the predicted impact is within 7 m of our own predicted position (self damage ×0.5 plus concussion that drains our energy).
- **Laser:** hitscan, so no lead, but charging takes 0.75 s at half move speed and is visible (`charging: true`) and audible at 140 m. Start charging only when the target has been in LOS ≥ 0.3 s and is expected to stay there (not near a corner). Release when actual aim is on target and charge ≥ 0.75 s, or earlier (≥ 0.15 s `min_charge`) if LOS is about to break. Prefer it against mortar holders (+60% `cookoff` = 504 at full charge).
- **Lightning:** no aim lead; needs the target inside a 30° cone within 45 m with LOS. Fire every 0.25 s only when that holds, because it costs 3 energy even with no target.

## 4. Projectile dodging

- Robocode material (`online-bot-competitions.md` §5): random direction changes every 5–20 ticks, stop-and-go, wave surfing.
- The mechfight-specific edge [rule]: enemy bullets and shells are **visible** in `obs.projectiles`, so we can compute exact closest-approach times.

**For mechfight (Survival):** per decision, for each enemy projectile, compute the closest approach of its straight line (bullet) or parabola (shell) to our predicted position under each of 9 move options (8 directions + stop) over the next 0.6 s, using accel 58.5 m/s² toward commanded velocity. Pick the option that maximizes the minimum miss distance, weighted by damage (shell splash radius 7 m dominates). 9 options × ≤ 10 projectiles × 6 steps = 540 cheap vector ops, well under 1 ms. Only override the strategic move when some option is predicted to be hit.

## 5. Pathfinding: precompute at startup, spread the rest over ticks

- Jump Point Search: optimal like A* on **uniform-cost** grids, up to an order of magnitude faster, no preprocessing. The original rules allow corner-cutting. (https://en.wikipedia.org/wiki/Jump_point_search, Harabor & Grastien AAAI 2011 https://ojs.aaai.org/index.php/AAAI/article/view/7994, snippets)
- Flow fields (Supreme Commander 2, Game AI Pro ch. 23): one Dijkstra "integration field" from the goal gives every cell a direction, so any number of agents and any start point share one search. (http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter23_Crowd_Pathfinding_and_Steering_Using_Flow_Field_Tiles.pdf; the PDF wouldn't render, so this is general knowledge of the chapter's well-known method.)

**For mechfight (Navigation):** our goals change slowly (the zone target changes once per phase), and we need a path from wherever we end up after a fight. So build a **flow field to the next circle** rather than A* per query. Grid 4 m (268 × 181 = 48k cells), edges blocked where the step-up > 1.2 m (`mech.step_up`) or slope > 50° (`max_slope_deg`), or inside a prism. Python Dijkstra over 48k cells costs maybe 0.3–1 s (estimate, to measure). Run it incrementally: pop ≤ 2000 heap entries per tick within a time check, and finish within ~3 s of a new `next_center` appearing, long before the shrink (hold phases are 15–60 s). Use A* (with JPS only if the grid is uniform-cost) for short local goals like a crate 60 m away. Roofs need a separate "jet" edge type; leave it out of v1.

## 6. Potential fields

- Anti-gravity (Robocode): inverse-square repulsion summed over points; prone to weight-balance problems and local minima; minimum-risk replaced it in top melee bots. (https://robowiki.net/wiki/Anti-Gravity_Movement, https://robowiki.net/wiki/Minimum_Risk_Movement, fetched)

**For mechfight:** use as the map-free fallback only.

## 7. Time budgeting

- reCurse (CodinGame winner) used the long first turn for precompute and a cache. Halite III and Battlecode postmortems: simple and deterministic beats clever and untested. (See `online-bot-competitions.md` §9.)

**For mechfight:** per decision, check `time.perf_counter()` against a 25 ms soft cap. Order the work: (1) action from the cached plan, (2) aim solve, (3) dodge check, (4) candidate scoring, (5) incremental pathfinding with whatever time is left. Skip later steps when over budget. Determinism: seed `random` with `hello.seed` so simulator A/B runs replay.
