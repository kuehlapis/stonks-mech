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

## Zone-smart squad (moderator round 2, 2026-11-22)

User directive: assume squad bots do not die to the zone. Baseline (112 matches): 2.07 ± 0.15, median death 101 s, killed by gun 88 / laser 22. The 1154/1680 sim zone deaths are gone. What's left: **our kills**, **squad deaths to drones** (254/1680 in the sim, ~2.3 per match, timing unknown) and **the final burn**.

### The arithmetic of > 6

score = kills + (drone deaths before ours) + (squad bots with less HP than us at the burn, if we are alive at 415 s).

Without the burn we need **6+ kills per match**; today we get 1.07. With the burn, a 10-cube mech with 3 plating has 1400 × 1.4 × 1.52 ≈ 2980 HP = 11.5 s at 260 HP/s, against 5.4 s for a bare 1400 HP bot. A target mix that clears 6: **4 kills + 0.5 drone deaths + 25% alive at the burn × ~8 bots outlasted ≈ 6.5.**

### Squad structure we can exploit (`squad.py` `_hunters`, track text "one early, more as you thin them out")

- The hunter count is 1 + dead (+1 at 150 s, +2 at 240 s, all of them at 300 s). Hunters are the **weakest** alive. So they arrive in tier order: easy ×4, then medium.
- Easy bots (sim): no lead (`lead_k` 0), aim noise ~0.044 rad, no strafe, gun only, no laser pickup. At 130 m a bullet takes 0.52 s; we walk 11.7 m/s sideways, so an unled shot misses a strafing target (6 m > 2.5 m radius) almost always.
- After k kills there are k+1 hunters: 1, 2, 3, then 4 (easy #4 + 3 medium). **The first four kills come mostly from easy bots, in groups of 1–3.**

### ZS1 (top): the hunter ladder, then run

**What.** Before 240 s, fight hunters that look easy: gun-only (`weapons` in `obs.mechs`), ≤ 3 visible, no other squad bot within 150 m, and no laser beam or `charging` seen from them. Fight at 120–150 m (`FIGHT_RANGE`), strafing at walk speed (save energy) and leading with the gun. Take their dropped cubes (kills drop cubes + 2). Stop the ladder at the first laser holder, when 4 or more are visible, or below 50% HP, and switch to RUN_MODE (built). The rest of the match runs on RUN_MODE + FIRE_POLICY.
**Why.** It turns the squad's "weakest first" escalation into a queue of the worst shooters, one or two at a time. Each kill is +1 point and +3 or more cubes (+4% HP and +4% damage each). Gun-only bots are nearly harmless to a strafing mech at range.
**Expected.** Kills 1.07 → 3–4; median death about the same or later (we leave once mediums with lasers arrive). **Score 4–5.** This is most of the gap.
**Track risk.** Real easy bots may lead or strafe. The gun-only + ≤ 3 visible gate still keeps us out of losing fights; the worst case is today's 2.
**A/B.** `zs_ladder` vs `r_run` (RUN_MODE + FIRE_POLICY), 112 matches on paired seeds, on a **zone-smart squad** (below). Metrics: kills per match, kills before 240 s, median death_t, cause of death. Pass: kills ≥ 2.5 with median death not earlier.
**Build.** `python/brain.py`, about 25 lines: a `LADDER_UNTIL` (240 s) gate in front of FIRE_POLICY/RUN_MODE that allows a full fight when the target and every visible enemy is gun-only, the visible count is ≤ 3 and HP > 0.5. Reuse the existing fight code; RUN_MODE takes over outside the gate.

### ZS2: be the fattest mech at 415 s

**What.** Cubes and upgrades: ladder kill drops, crates within 80 m before 240 s (existing farming), and every supply drop that passes `DROP_SAFE_R` (3 cubes + full HP each). Plating first (already first in `economy.ORDER`), then nanites, then armor. From 370 s `BURN_ENDGAME` + BURN_QUIET (built): hidden, no fire, and full HP by about 405 s (REGEN_HIDE). Stop picking up cubes past 10 (stat cap: they only add size).
**Why.** At the burn, placement is decided by HP. Easy bots likely don't loot and the squad shares ~36 crate cubes + drones among 15, so most have ≤ 4 cubes and 0–1 plating (~1600–1900 HP). We'd have ~2500–3000.
**Size cost.** +5% radius per cube (10 cubes = +50%) makes us easier to hit, mainly in open fights. The ladder fights unled easy shooters (size matters less), and late we hide. Accept it up to 10 cubes, no more.
**Expected.** Conditional on being alive at 415 s: we outlast 8–12 of the squad bots still alive. Unconditional: **+1.5 to +3** on top of ZS1, if 20–30% of matches reach the burn. That share is the open question.
**A/B.** `zs_ladder` vs `zs_ladder` + BURN_ENDGAME/BURN_QUIET/REGEN_HIDE. Metrics: % alive at 370 s and 415 s, `hp415` (the inproc row already has it), our HP rank among the survivors at 415 s.
**Build.** Flags only, plus `economy.py` "skip cubes past stat_cap": about 3 lines.

### ZS3: bait hunters through drones (low)

**What.** When hunted by 2 or more and running, pick the RUN_MODE far point so a drone's home (30 m leash) lies between us and the hunters, and pass it at more than 45 m ourselves. Hunters walking our path come within 45 m with line of sight, and the drone shoots them.
**Why / limit.** Drones do 25 damage per second and squad bots shoot back at a drone that hits them (`squad.py`, every tier). A drone costs a hunter HP and time but rarely kills it alone. The 254 sim drone deaths come mostly from farming bots that start the fight.
**Expected.** +0.2–0.5 (indirect: the hunters' HP drops, so later ladder kills are easier). Don't build before ZS1/ZS2 are measured.
**Build.** `python/brain.py` `_far_point`: add a drone-home bonus term, about 10 lines (homes are learned from sightings; spawns are random per match).

### How the built parts fit

| Phase | Mode |
|---|---|
| 0–240 s | ZS1 ladder: fight only easy-looking hunters; farm crates and cubes within 80 m when no hunter is within 150 m |
| any time the ladder gate fails | RUN_MODE (+ FIRE_POLICY: return fire only while exposed, one-shot kills only) |
| 240–370 s | RUN_MODE; supply drops if safe; regen in hiding |
| 370–415 s | BURN_ENDGAME + BURN_QUIET + REGEN_HIDE: hidden, full HP, no fire |

### Needed before any A/B: a zone-smart squad in the sim

The current sim squad dies to the zone, which would credit hiding falsely. The Tester should add `ZONE_SMART = True` to `sim/bots/squad.py`: head to `next_center` once the shrink starts if outside `next_radius − 10`, about 5 lines. Re-run the baseline (`cur`, `r_run`) on it first. Expected: squad zone deaths near 0, our score near 1.1 (kills + drone deaths), which matches "the zone path is gone".

### Ranking

| # | Proposal | Expected score (zone-smart) | Effort |
|---|---|---|---|
| 1 | ZS1 hunter ladder → run | 4–5 | ~25 lines brain.py |
| 2 | ZS2 fattest at the burn (flags already built) | +1.5–3 on ZS1 | flags + 3 lines |
| 3 | ZS3 drone bait | +0.2–0.5 | ~10 lines |

Together: about 5.5–7.5, guesses. ZS1's kill count is the number to measure first.

## 300–415 s survival (moderator round 3, 2026-11-22)

After the Critic's zone-smart review (`notes/reviews/zone-smart-2026-11-22.md`): ladder capped at 2 kills / 150 s, about 2300–2600 HP, a realistic total of about 3–4. The open question is whether we can be alive at 415 s while all 15 hunt us with shared vision.

### The window in numbers (`notes/research/zone.md`, protocol §9)

| t (s) | Circle | dps outside | What it means |
|---|---|---|---|
| 295–325 | 140 → 70 m | 100 | every squad bot is within 140 m of the next center |
| 325–375 | 70 → 25 m | 160 | the circle is 140 m wide; 15 bots are inside it |
| 375–390 | 25 m (hold) | 260 | 50 m across: nowhere in it is out of sight of everyone |
| 390–415 | 25 → 0 m | 260 | the point it closes on is known from 375 s at the latest |

- **Outside the zone is not an option.** No regen outside (§5). At 100/160/260 HP/s, 2500 HP lasts 25/16/9.6 s. A mech that stays out from 375 s dies by about 385 s, before the squad inside starts burning (415 s). Trading HP for distance only works in phases 1–3 (≤ 60 HP/s), not in this window.
- **The 70 m dorm towers are out of reach for everyone** (rise 72.9 m vs about 60–67 m from one tank of jet, `map.md`). They are also on the west edge (x ≈ −460) and the final circle is random. Dead end.
- **Hiding against shared vision:** one squad bot seeing us is enough, and vision memory keeps our real position for 5 s (§8). In a 70 m circle with 15 bots there are perhaps one or two building footprints. In the 25 m circle there are none that can hide us.
- **Sounds don't say who made them** (§8), but the squad doesn't need sound: they find us by sight. A gun burst (heard at 320 m) is just a bearing for them. In the sim the squad doesn't use sounds at all, so this idea can't be tested there.
- **Mortar-proof spots:** shells arc (72 m/s, gravity), so only overhead cover stops them: bridges and overhangs we can stand under (clearance ≥ 9 m, §7 movement). Under a bridge, gun and laser still reach along its axis. That helps against one weapon, not 15 shooters.

**Honest conclusion: against 15 zone-smart bots with shared vision, % alive at 415 s is about 0–5% whatever we do.** That is worth about +0.3 score (5% × ~6 bots outlasted). The window's real value is kills, not survival time.

### Ranked

| # | Idea | What the bot does | Expected % alive at 415 s | Expected score effect | A/B |
|---|---|---|---|---|---|
| 1 | **Last stand for kills** | From 300 s, or when ≥ 5 hunters are within 150 m: stop running. Take a spot with a wall behind us, enemies on one side and a choke in front (existing `find_cover`, path-distance hold point). Fight from there, focus the lowest-HP visible bot (`hp` is shown), and use lightning (chains 3 targets, 45 m) when the crowd closes. Every kill before we die is +1; dying at 330 s or 400 s scores the same. | 0–3% | **+0.5–1.0** (kills 2 → 2.5–3) | `zs_ladder` vs `zs_ladder + LAST_STAND`, 112 matches, zone-smart squad; metric: kills after 300 s |
| 2 | **Final-roof hold** | At about 360 s, if a reachable roof (rise ≤ 50 m) lies inside the phase-5 next circle (25 m, known from 325 s), jet up with ≥ 90 energy and stand away from its edges. Bots at the foot of the building can't see up past the edge; climbers rise at 10 m/s while visible and can be shot. Only works when the final circle covers a building: guess 20–30% of matches (the campus is dense in the centre, `map.md`). | 3–8% when it applies, 1–2% overall | +0.1–0.3 | trace only: count matches where a roof is in the final circle; then flag on/off |
| 3 | **Edge dance in phase 5–6** | Stay on the side of the shrinking circle away from the squad's centroid, inside by 3 m, strafing. | 0–2% | ≈ 0 | not worth a build |
| 4 | **Sound bait, then relocate** | Fire a gun burst away from where we'll go, then move quietly (< 5 m/s) | ≈ 0 against shared vision | ≈ 0; can't be tested in the sim | skip |

**Builder notes.** #1: `python/brain.py`, about 20 lines. A `LAST_STAND_T` gate that skips RUN_MODE's flee branch, picks the hold point once, and changes target choice to the lowest `hp`. It replaces BURN_ENDGAME's "no fire" while hunters can see us (BURN_QUIET only helps while we are actually hidden). #2: `python/survival.py` plus `world.py` roof heights, about 30 lines; build only if the trace shows roofs in the final circle often.

**Revised total (guesses):** ladder 2 kills + last stand +0.5–1 + drone deaths ~0.3 + burn ~0.3 = **about 3–4, under 6.** Unless the track's squad is weaker than modelled (it may still die to the zone; our track 1.6 doesn't tell), **6.00 needs a far higher kill rate.** That means winning 1v2 or 1v3 against medium and hard bots, which is an aim and fight-quality problem, not a strategy one. **Before more strategy work, the next highest-value check is one track replay (or the track page): do the house bots die to the zone?** If yes, the zone path from P1/P2 is back and worth about +10 per match that survives to about 400 s.
