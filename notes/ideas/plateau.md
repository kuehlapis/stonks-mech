# Breaking the squad plateau (score ~1.9 sim, 1.6 track)

Strategist, 2026-11-22. Inputs: `protocol.md` §5, §7, §9; `sim/bots/squad.py`; Critic `notes/reviews/squad-sim-2026-11-22.md`; `python/brain.py` flags.

## Why we die early, and why the score does not move

1. **Place = squad bots dead before us + our kills.** Squad bots never kill each other. In the sim they die almost only to the zone, late: median squad death ~395 s, 19/30 to the zone (`squad.py:143`: they head in only once outside), 7 to NPCs (Critic run, seed 7). We die at ~148 s. So any death before ~350 s scores 0–2, whether it happens at 60 s or 300 s. **Every tuning so far was judged by a metric that cannot see it.** Surviving past ~400 s is worth about +10.
2. **We are always the target.** "Weakest first" only ranks the hunters among themselves; the target is always us. Shared vision (any sighting, kept 30 s in the sim) means one bot seeing us sends every hunter to our last known position.
3. **Each kill adds a hunter** (`_hunters`: `1 + dead + time bonus`; all at 300 s). Fighting buys +1 place but makes the next minute harder. Our current brain is tuned aggressive (`FIGHT_EDGE 1.2`, `OPEN_EDGE 1.2`), adopted because it lifted score 1.40 → 1.74; under the floor effect that gain is ~1 kill, not survival.
4. **Hunters walk; we can boost.** Squad bots boost only when outside the zone or stuck (`squad.py:208`). Walk 11.7 m/s vs our boost 19.5 m/s. A hunter at 100 m never closes if we run on boost pulses. Non-hunters stay inside the next circle and fire only within 60 m (`DEFEND_RANGE`).
5. **The final burn is a free win in the sim.** Radius 0 at 415 s, 260 HP/s; most HP lasts longest. A full-HP mech that is inside the circle while squad bots wander outside it outlives them.

**Measured (current bot, 14 matches vs 15 squad, `--seed 1 --rotate --jobs 2`):** score 2.0 (SE 0.48), median death 100 s, 57% dead before 120 s, causes gun 12 / laser 2, kills 1.07, 0% time outside the zone. Squad: 147/210 deaths to the zone, 35 to NPCs; matches end ~414 s. So we die to hunters' guns early, never to the zone.

**Primary proxy for everything below: `death_t_median`, % alive at 300 s, % alive at 400 s,** on paired seeds (≥ 56 matches), with score as the target. Score alone cannot rank these.

**Track caveat.** If the real house bots handle the zone well (don't die to it), the late payoff shrinks: then only the burn ranks us against them, and that is decided by HP at 415 s. Each proposal says how it holds.

## P1 (top): Run, don't fight: the evasion doctrine

**What the bot does.** Never start a fight. On any sighting of a squad bot (seen, `damaged`, sound bearing): turn the legs away, keep the torso on the threat (no ×1.5 rear hits), boost in pulses toward the point inside the next circle that is farthest from all known squad positions, and break line of sight behind buildings (never trees). Fire back only when cornered (`CLOSE_EDGE` case: within 60 m with energy < 20) or when a single easy/medium bot is under 35% HP and alone (free +1). Keep ≥ 40 energy as an escape reserve; walk under 5 m/s once out of sight > 5 s so our steps are silent.

**Why it raises placement.** Time alive is the lever (fact 1). Hunters at walk speed cannot close on a boosting mech (fact 4), and not killing keeps the hunter count at 1–3 until 300 s (fact 3). Regen (45 HP/s after 5 s quiet) refills us between contacts.

**Expected.** Median death 148 s → 250–330 s; % alive at 300 s from ~5% to 30–50%. Score moves only with P2 (alive past ~390 s). Alone: +0.5 to +1.5 (fewer kills offset by a few late zone deaths). With P2: see P2.

**If track bots zone well:** still the right base. Fewer kills cost ~1 point; being alive at the burn is the only way to place well against a squad of 15.

**A/B.** `--bot cur=python/bot.py` vs `--bot run=sim/versions/p_run/bot.py`, 15 squad, 56 matches, `--seed 1 --rotate`, same seeds. Pass: median death_t +60 s or more, and % alive at 300 s ×2. Then re-check on `sim/bots/hunter.py`/`rusher.py` pools so we don't lose FFA play.

**Build.** `python/brain.py`, ~60–100 lines: a `RUN_MODE` flag (default off). Most parts exist: `FIGHT_EDGE`/`OPEN_EDGE` raised to ~3 (no voluntary fights), the evade-to-cover path (`EVADE_*`), `DANGER_RANGE` holding out of sight. New: the "farthest from known squad inside next circle" goal (score 12–16 candidate points on the next circle at radius 0.6·r by min distance to remembered enemies, filtered by `world.walkable`), and boost pulses while any hunter is within 150 m and energy > 40. Survival (`python/survival.py`) may own the goal point; one function, ~30 lines.

## P2: Own the final circle: burn endgame + late heal

**What the bot does.** Turn on and extend `BURN_ENDGAME`: from ~45 s before radius 0, stop all voluntary fights, stand well inside the final `next_center` (radius − 15 m), at full HP. Take the 210 s supply drop (called 210 s, lands 235 s) if no squad bot is within 80 m of it: full HP + energy + 3 cubes. Put every cube into `plating` (max HP) after 300 s; never let HP be below max at 400 s if regen can fix it (break contact for 5 s at ~395 s).

**Why it raises placement.** In the sim, squad bots walk to `next_center` only once outside, so in the last two phases (160 and 260 HP/s) they die in the gap. A mech inside the circle with full HP outlives all of them: alive at 400 s ≈ place 1–5. On the track, if they do reach the center, the burn ranks by HP: plating gives us more HP than the easy/medium tiers (easy bots don't loot, `squad.py` tier table), so we still beat some.

**Expected.** Conditional on being alive at 380 s: score ≈ 11–14 in the sim, 4–8 on the track if bots zone well. Unconditional: score ≈ 1.9 + 10 × (% alive at 390 s gained). With P1 reaching 30% alive at 390 s: **~5–6 sim**. This is the only path I see to > 6.

**A/B.** Flag on vs off on top of P1, same seeds. Metrics: place given alive at 380 s; deaths by cause after 380 s (zone vs mech). Pass: place given alive-at-380 ≤ 4 in sim.

**Build.** `python/brain.py` (flag exists: `BURN_ENDGAME`, `BURN_LEAD`; set lead 45 s, add "regen before 400 s") and `python/economy.py` (late plating order, ~5 lines). `DROP_ON` already chases drops; add the "no squad within 80 m" gate (~5 lines). Total ~30 lines.

## P3: Edge-of-zone ghost (positioning against shared vision)

**What the bot does.** The squad crowds the next circle (non-hunters pick random goals inside `next_radius − 15`). Sit in the band just inside the *current* zone edge, on the side away from `next_center`, as long as the shrink lets us (zone timer known, §9), moving inward only with the edge. That keeps the 14 non-hunters far away (they never come out, and fire only within 60 m), so only the hunters find us, and they come from one side (inward), which puts cover and escape room behind us.

**Why it raises placement.** Most early contact in the sim comes from walking through the crowd (Critic finding 3). Fewer bots in view = less shared vision = fewer hunter vectors. Zone damage stays 0 if we track the edge with a margin (`radius − 12` m, existing Z2 rule).

**Expected.** Median death +30–80 s on top of P1; cheap. Weak point: in the last two phases the circle is too small to hide in; P2 takes over there.

**If track bots zone well:** unchanged early benefit; edge risk grows if real bots patrol outward. Fall back to P1 alone.

**A/B.** P1+P3 vs P1, same seeds. Metric: mean count of squad bots within 120 m per second alive (trace), death_t median.

**Build.** `python/survival.py` hold-point function: edge-band target replacing the "next circle" hold point when RUN_MODE is on and t < final phase start. ~25 lines. Existing Z2 edge-hold logic is the base.

## P4 (optional, only after P1–P3): Hunt only the lone early hunter

**What.** Before 150 s, exactly one hunter (the weakest, an easy bot: no lead, no strafe, gun only, `squad.py` TIER) hunts us. If it is alone (no other squad bot within 150 m) fight it from 130 m with laser/strafe: +1 place, 2 cubes + its cubes. Do **not** fight the replacement hunter (it is easy #2, then medium).

**Why.** +1 point for ~10 s of fight against the weakest bot; each kill adds one hunter, so cap at 1–2 kills.

**Expected.** +0.5 to +1 score; −10 to −20 s median death. Run only if P1 shows hunters reach us rarely.

**Build.** `python/brain.py`: a kill-cap counter on the fight gate (~10 lines).

## Ranking by expected death time

| Proposal | Median death (now ~148 s) | % alive 300 s | % alive 400 s | Score effect | Holds if track bots zone well? |
|---|---|---|---|---|---|
| P1 run doctrine | 250–330 s | 30–50% | 10–25% | +0.5–1.5 alone | yes (base for any late plan) |
| P2 burn endgame | same as base | same | +5–10 pts on top | ×10 per alive-at-390 point; ~5–6 with P1 | partly: HP ranking still beats easy tiers |
| P3 edge ghost | +30–80 s on P1 | +10 pts | +5 pts | +0.3–1 | yes early; weaker late |
| P4 lone-hunter kill | −10–20 s | −5 pts | ~0 | +0.5–1 | yes |

All numbers are reasoned guesses until the A/Bs run. Order: P1 → P2 (stack) → P3 → P4.

## Risks

- The sim's squad zones badly; the track's may not. P2's payoff is then much smaller; P1 still the precondition.
- Hard/expert aim is near-perfect in the sim (Critic finding 4), so running in the open loses HP fast; P1 depends on breaking LOS, not on dodging.
- Real hunters may boost; then fact 4 fails and P1 must lean on cover and jets to roofs (60 m climb per 100 energy).
- Our own earlier test said "aggression helps"; it was measured on score under the floor effect. Re-measure with death_t before trusting either.
