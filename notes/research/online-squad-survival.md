# One mech against 15 coordinated hunters: outside tactics translated (rev 2)

Researcher (online), 2026-11-22, revised after moderator feedback (thin sources, R2 unsettled, overlaps with built switches, R1 not costed). Rule facts cite `protocol.md` lines. Not repeated: `online-movement.md` §2–5, `mechanics.md` gap 1. Effects are reasoned, not measured.

## What the stronger sources say

- **Pursuit-evasion theory.** Bhadauria, Klein, Isler, Suri (arXiv 1110.4838, abstract fetched): with full information about the evader, **three pursuers always suffice** to capture it in any polygonal environment, "independent of the number of vertices or holes". With incomplete information, merely *detecting* the evader needs Ω(√h + log n) pursuers (h holes = obstacles). Translation: against 15 hunters with shared vision, outrunning or out-turning them while seen is a lost game; obstacles only help while we are **undetected**. Our play must be "be unseen" or "be seen by at most a few at once", never "run in the open".
- **Horde AI design** (attack tokens, Kung-Fu circle: Envato Tuts+ "Battle circle AI"; StraySpark "Attack token system"; Unity AI Cookbook "fighting circle", after *Kingdoms of Amalur*). Games make hordes beatable by **limiting how many attack at once**. Hunter bots on the track have no such limit, so we have to impose it with geometry: if only k can see us, only k shoot.
- **LLM battle-royale experiment** (Devfolio "AI Battle Royale"): given distance and safe-zone status, agents converged on kiting at their best range and staying near the zone center. Expect hunters to sit at the center late, which favours holding a covered spot near it rather than the exact center.
- Consumer BR and self-defence guides from rev 1 (sources below) are kept only as supporting colour, never as the sole support for a rule.

## R2 (body shield): settled from protocol, narrowed to lightning only

- Gun bullets, shells and lasers: `protocol.md:317` says they hit buildings, bridges and terrain. It never says whether a mech in the path stops a bullet or beam, so a general body shield is **not supported. Dropped.**
- Lightning (`protocol.md:306`): it hits the **nearest** target (mech, NPC or crate) within 45 m and 30° of the aim, then **chains** to up to 2 more targets within 14 m (×0.7 per jump). Two facts follow, both protocol-backed:
  - (a) **Spread from our own pack-mates is not our problem, but bunching is theirs.** When we hold lightning, prefer a target with other hunters within 14 m: up to 60 + 42 + 29 = 131 damage per 0.25 s shot spread over 3 mechs.
  - (b) **A nearer mech or crate inside an enemy's lightning cone takes the arc instead of us.** This is too situational to build. Noted, not a rule.
- **R2' (kept, small):** `combat`/`brain` target pick with lightning: score = time-to-kill minus a bonus per other hunter within `chain_range` of the target. **A/B:** `b_chain`, switch `brain.CHAIN_PICK = False` (default off). Expected: a small effect, +0.1 to +0.3 place, only in matches where we hold lightning.

## R1: funnel, so at most one or two hunters can see the spot

- **Does:** when ≥ `FUNNEL_MIN` (3) hunters are tracked (visible or remembered under 5 s), pick a hold spot that the fewest hunters can see, with a wall behind it. Hold there and fight whoever shows up.
- **Why:** with no attack-token limit, the number of shooters equals the number with line of sight. Pursuit-evasion says we can't escape full information, so we cut the number of shooters instead. Rear armour (`protocol.md:295`, ×1.5 from behind) makes a covered back worth more.
- **How to score a spot, reusing existing code** (`survival.find_cover`, `survival.py:192`):
  1. Candidates: the same `nav.wall_cells(pos, WALL_SEARCH=60)` list `find_cover` already builds, same height filter (`COVER_DZ`) and in-zone filter. Drop the shadow-side test (it assumes one main threat). Sort by straight distance and keep the **nearest `FUNNEL_K` = 8**.
  2. Exposure: for each candidate, the count of the **`FUNNEL_N` = 5 nearest** tracked hunters with `world.los(eye_h, cell + height/2)`. One height, not two. Worst case 8 × 5 = **40 los calls**, equal to the existing `LOS_CAP = 40`, and checked against `LOS_CAP` exactly as `find_cover` does.
  3. Back wall: the wall cell's normal (`nx, ny` from `wall_cells`) must point away from the hunters' centroid (dot product > 0). This is free arithmetic, with no los calls.
  4. Score = exposure × 100 + distance m. Take the minimum, and stay on it only if exposure ≤ 2. Otherwise fall back to the current `find_cover`.
- **Cost:** `World.los` over 200 m measured 0.04 ms (`notes/agents/tester.md:47`); the interface cap is 0.3 ms (`notes/interfaces.md:41`). 40 calls cost 1.6 ms typical and 12 ms at the cap. The result is cached for `CACHE_S` = 1 s with the same "threats moved < `MOVE_M` 10 m" invalidation, so the search runs at most once a second. It is skipped when `brain._slow()` (`SLOW_MS` = 30) already fired this tick.
- **Why it won't repeat the 50–62 ms hold-point search:** that search (`HOLD_SEARCH`, `decisions.md:9`) did a grid path search of up to `HOLD_NODES` = 4000 nodes over 300 m. The funnel does no path search: it uses straight distance over at most 8 cells already inside a 60 m radius. Its cost is bounded by the 40 los calls.
- **A/B:** `s_funnel`. Switches: `survival.FUNNEL = False` (default off), `FUNNEL_MIN = 3`, `FUNNEL_K = 8`, `FUNNEL_N = 5`. `brain` calls `S.funnel(obs, threats)` in step 8 before `find_cover` when the switch is on. Tester: also report p99 of `act()` and the mean count of hunters with line of sight while our HP falls.
- **Expected:** +0.5 to +1.5 places in squad sims. Risk: a corner the hunters can't see is also a corner we can't see out of, so it's weak against mortars lobbed over the wall (`protocol.md:304`).

## R3: regen break, as a delta on `brain.REGEN_BREAK`

- **Built already** (`brain.py:51`, `:164`, `:249`): after any `damaged`/`hit` event, no *voluntary* fights for `regen_delay` s. **Missing:** it does not take us out of sight or keep us quiet, so with shared vision someone keeps seeing us, shoots again, and resets the 5 s clock. Pursuit-evasion says detection is the only thing obstacles defeat.
- **Delta:** during the regen window, when any hunter is visible, route to `find_cover(obs, all tracked threats)` (or to the R1 funnel spot if `FUNNEL` is on) with `quiet=True` (walk under 5 m/s, no step sound per `mechanics.md`). Don't fire unless `engaged` within `CORNER_DIST`.
- **A/B:** `b_regen_hide`. Switch `brain.REGEN_HIDE = False`; it requires `REGEN_BREAK = True`. Compare against the existing `b_regen` variant (`sim/versions/b_regen/`).
- **Expected:** +0.3 to +0.8 places over `b_regen`. Measure the count of full regen cycles completed per match.

## R4: let the zone wear down the pursuers

- **Does:** stay inside the *next* circle 10–15 s before each shrink, on the side away from the hunters' centroid. Engage only hunters that are outside the live circle; they take zone damage and don't regen (`mechanics.md` Zone row).
- **Support:** protocol fact (no regen outside the zone, zone damage), plus the LLM-BR finding that agents converge on the zone center, so arriving early takes the cover first. BR guides from rev 1 agree.
- **How:** `survival.hold_point` already aims inside the next circle (`HOLD_DEPTH`). The delta is (a) bias the hold target to the side of the circle opposite the hunters' centroid, and (b) in the fight gate, a time-to-kill bonus ×0.8 for hunters outside the live circle.
- **A/B:** `s_zone_lean`. Switches: `survival.ZONE_LEAN = False`, `brain.OUTSIDE_BONUS = 1.0` (set 0.8 in the variant).
- **Expected:** +0.2 to +0.6 places. It is cheap: two lines of arithmetic, no los.

## R5: shoot the weakest hunter

- It is already how the brain picks fights (time-to-kill fight model, `decisions.md:30`). **Dropped as a separate rule.** The only new part is the outside-zone bonus, which is now in R4.

## R6: last circle, as a delta on `brain.BURN_ENDGAME`

- **Built already** (`brain.py:49`, `:184–189`): from `burn_t`, no fights unless cornered; go to `final_center`, and return fire with the gun when engaged. Loot is skipped by construction, because the branch returns before the loot steps. The "no looting late" part of rev 1 is therefore **dropped**.
- **Delta:** the return fire breaks our own regen. Regen needs 5 s with no damage *dealt* or taken (`mechanics.md` HP regen row), so every hit we land while not cornered costs HP at 415 s. Also, holding the exact center in the open is where LLM-style hunters converge.
  - When engaged and not cornered, **don't fire**. Go to `find_cover` (or the funnel spot) inside the final circle instead of the center, `quiet=True`.
  - Only enter the centre ring when the live radius gets below cover range.
- **A/B:** `b_burn_quiet`. Switch `brain.BURN_QUIET = False`; it requires `BURN_ENDGAME = True`. Compare against the existing `b_burn`.
- **Expected:** +0.2 to +0.5 places over `b_burn`. Measure our HP at t = 415 s.

## Priority (build order)

1. `s_funnel` (R1)
2. `b_regen_hide` (R3)
3. `s_zone_lean` (R4)
4. `b_burn_quiet` (R6 delta)
5. `b_chain` (R2', only if lightning is common in sims)

Each variant is off by default and gets its own A/B against the squad pool.

## Sources

Fetched:
- Bhadauria, Klein, Isler, Suri, "Capturing an evader in polygonal environments", arXiv 1110.4838: https://arxiv.org/abs/1110.4838

Search snippets:
- Isler group, IJRR 2012 version: https://www-users.cse.umn.edu/~isler/pub/ijrr2012pe.pdf
- Battle circle AI (Envato Tuts+): https://code.tutsplus.com/battle-circle-ai-let-your-player-feel-like-theyre-fighting-lots-of-enemies--gamedev-13535t
- Attack token system: https://www.strayspark.studio/blog/attack-token-system-ue5-group-combat-that-feels-fair
- Unity AI Cookbook, fighting circle: https://www.oreilly.com/library/view/unity-2018-artificial/9781788626170/d9807718-33bb-41f9-884e-59caf70dc0ac.xhtml
- AI Battle Royale (LLM agents): https://devfolio.co/projects/ai-battle-royale-dc53

Supporting only (rev 1):
- Art of Manliness: https://www.artofmanliness.com/skills/tactical/how-to-fight-multiple-assailants/
- Police1: https://www.police1.com/officer-safety/a-dozen-suggestions-for-prevailing-against-multiple-attackers
- Sportskeeda, PUBG Mobile last zone: https://www.sportskeeda.com/esports/pubg-mobile-tips-and-tricks-to-survive-in-the-last-zone
- Tom's Guide, Fortnite tips: https://www.tomsguide.com/us/pictures-story/1398-fortnite-battle-royale-tips.html
