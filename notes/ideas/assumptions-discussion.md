# Assumptions discussion

## Tester (2026-11-22)

What the sim actually does for A9–A16, whether it is calibrated, and the cheapest check.

| # | What the sim does (file:line) | Calibrated? | Cheapest calibration |
|---|---|---|---|
| A9 | `DEFEND_RANGE = 60.0` (sim/bots/squad.py:30): non-hunters shoot visible enemies within 60 m; `RETALIATE_S = 10.0` (squad.py:33): a member hit by a non-squad mech counts as a hunter for 10 s at any range and posts an 80 m bearing guess to the shared map. | Guess. The "example bot 1.01 vs track 1.15" check predates retaliation and zone-smart, so it no longer calibrates the current model. | Run `python/example_bot.py` ×1 vs squad.py ×15 on 40 seeds and check that it lands within about 1 SE of 1.15. |
| A10 | Aim error is AR(1): `aim_err = 0.8*aim_err + 0.2*gauss(0, 2.2*noise)` with noise from `TIER` (squad.py:23–28). Steady-state sd ≈ 0.73×noise: easy 0.044, medium 0.022, hard 0.011, expert 0.006 rad. Lead factor 0 / 0.6 / 0.9 / 1.0. | Guess; the numbers in A10 match the code. | Same 40-seed run as A9. If the example bot lands far from 1.15, scale all noise by one factor until it fits. |
| A11 | Squad bots walk; `boost` only when out of zone or when stuck and airborne (squad.py:230). No roof or jet logic. squad_chase.py adds boosting on chases > 40 m at energy > 30. | Guess. | Can't be calibrated in the sim. Needs a recorded track match. |
| A12 | squad.py reads no `sounds`. squad_chase.py turns sound bearings into last-known positions (near 40 / mid 110 / far 200 m). | Guess, two variants. | Run s_base vs squad and vs squad_chase on the same 40 seeds. If the ranking of our versions changes, A12 matters. |
| A13 | Medium and up take lasers within 60 m (squad.py:143). Every tier picks upgrades by the fixed `PREF` order (squad.py:106). Easy bots don't farm or take lasers. | Guess. | None cheap. Needs track replays. |
| A14 | sim/engine.py implements protocol.md. Known gaps (tester journal): no 50° slope, no slide-out; NPC behaviour, laser charge scaling and the lightning cone are assumptions. Mechs also get wedged on walls (traced 2026-11-22: a squad bot sat at (3,-140) for 90 s, jumping, until the zone killed it). | Unverified. Sim 2.07 vs track 1.6 for our submitted bot; example bot 1.01 vs 1.15. | **Paired 40 seeds:** example bot and s_base, each ×1 vs squad.py ×15, same seeds (`--seed 1 --matches 40 --rotate --jobs 2`, about 1 h each at jobs 2). Pass if example ≈ 1.15 and s_base ≈ 1.6 (the track score of our submitted bot) within 1 SE. The ratio is the cheaper signal: track 1.6/1.15 = 1.39. |
| A15 | 4–8 match A/Bs. | **Weak.** From today's 4-match runs, our per-match SE was 0.71–1.7, so the sd is 1.4–3.4 points per match. At n = 8 that gives SE ≈ 0.5–1.2, and the SE of a difference between two versions ≈ 0.7–1.7. An 8-match gap under ~1.5–2 points is noise. Paired seeds help, but we have no measured pairing correlation. | Report the paired-difference SE on every A/B. Treat n ≥ 40 as the floor for any gap < 1 point. |
| A16 | `late` counted when `act()` > `tick_budget_ms` (sim/inproc.py:114, 161). Today under load: our `ms_max` 58–105 ms, late 6–38 per 4 matches. With little load, earlier runs: 22–41 ms. | Unverified on an idle machine. | Time our bot alone on the replayed stream (`check/check.py`) with no other sims running, once, and report p99 and max. |

Cheapest single experiment that touches A9, A10 and A14 together: the paired 40-seed example bot vs s_base run against squad.py. It costs about 2 h at `--jobs 2`, and less once the moderator's sims finish.

## Researcher (online), 2026-11-22

The evidence is weak: search snippets plus community copies of files, and one page fetch was refused (Valve wiki, 403). "Bears" means how strongly a finding bears on the assumption: strong, medium, weak.

| Finding | Source | Bears on | How strongly |
|---|---|---|---|
| Shipped difficulty tiers are parameter profiles (Skill, ReactionTime, AttackDelay, aim focus/spread), not separate logic. One Counter-Strike `BotProfile.db` copy has ReactionTime 0.60 s (Easy, Normal), 0.30–0.50 s (Hard) and 0.001 s (Expert); AttackDelay 0.7–0.8 s at the low tiers and 0 at Expert. Other copies differ. | gists trueharuu/fe02f66b, Jezternz/5a99a343, diegorodriguesvieira/f2680e1e; Valve wiki Mp_bot_ai_bt (snippet: "reaction_time = delay before reacting") | A10 | **medium.** A10 models only aim noise. If the house bots also have a reaction delay of about 0.3–0.6 s at easy/medium, our first-shot window is 1–2 gun shots (0.24 s cooldown) before they answer. That favours shooting first at easy/medium bots and not trading with experts. Check: in `check/stream.jsonl.gz`, the time from our first hit on a bot to its first shot back, grouped by bot. |
| Lower tiers aim at the body or legs, the top tier at the head; aim quality runs 0–100 per profile. | CS2 difficulty guides (bo3.gg, totalcsgo) | A10 | weak (mechfight has no hit zones, so only the spread part transfers) |
| Mobile BR bots "know the direction you shoot from and move toward the gun sound" (fan guide). | Sportskeeda, PUBG Mobile bots | **A12** | **medium against A12.** The common design is for bots to react to gunfire sound, so assuming the house bots ignore sounds is optimistic. Our firing then draws hunters, which is consistent with A6 and with r_run doing badly. Variant to check: `squad.py` with hearing on, and re-run `s_base`. |
| BR house bots use per-map navigation and loot by game phase. | PUBG dev statement (GamesRadar) | A13, A11 | weak. It supports "they loot and upgrade" (A13). Nothing on jets or roofs. |
| Fortnite bots move predictably and use cover badly. | Sportskeeda, PC Gamer | A11 | weak. It fits A11 (they walk and don't climb), so roofs and walls are where they are weakest. |
| Horde/squad AI in shipped games caps simultaneous attackers (attack tokens, Kung-Fu circle). | Envato Tuts+, StraySpark | A7 | weak to medium. A7's staggered hunter release ("one early, more as you thin them out") is this pattern. It is plausible that the real squad does the same, which makes the early game the cheapest place to get kills: one hunter at a time. |
| Pursuit-evasion: with full information, 3 pursuers always catch an evader, whatever the obstacles. | arXiv 1110.4838 (fetched) | A8, A17 | medium. With perfect shared vision, running can't work, which matches the A17 refutation. Hiding pays only while we are undetected. |
| Nothing found on whether house or squad bots avoid zone damage. Shipped BR bots presumably follow the circle, but I found no source. | — | A4 | none |

**Open question: how a lone bot reaches 6.00.** No outside source covers "1 vs squad" bot-practice tactics; the searches found only consumer tips. This is inference, not evidence:
- If A7 (staggered release) and a reaction delay (row 1) both hold, a 6.00 bot most likely farms the early lone hunters. It shoots first from about 60–100 m, kills each one before it answers, and then breaks line of sight to regen (`REGEN_BREAK`).
- 6.00 means about 10 squad bots alive at our death, so 5 squad deaths before ours. With A4 (no zone deaths), that is about 5 kills, close to A19.
- The assumption most likely wrong for this to happen is **A9/A5**: the non-hunters may not retaliate or defend as strongly as the sim does. A12 is the next candidate: if they hear us, they may hunt worse than "perfect shared vision" (A8) implies, for example with no memory beyond what they see.
- Cheapest check: the stream file (offline Researcher's area). Measure the reaction delays per bot, and whether bots turn toward our gun sounds.

## Researcher (offline), 2026-11-22

Source: `notes/research/house-bots.md` (the recorded match; FFA, 16 mechs, 36.8 s, one opponent seen: mech 10, gun + laser). **Not known to be a house bot**; no squad mode in the recording.

| # | Bears on it? | Evidence | Suggested status |
|---|---|---|---|
| A2/A7/A8 | No | FFA recording, mechs kill each other (3 deaths t 17-25), no shared vision visible | unchanged (guess) |
| A5 | Yes, supports | Hit from behind at t 5.7 -> on target 0.6 s later, laser hit at 2.2 s, then chased and killed us | supported (n = 1, FFA bot) |
| A9 | Partly | Ignored our 2 unseen shots at 140 m; retaliated immediately when hit and kept retaliating for 31 s (longer than the 10 s window) | consider a longer retaliation memory |
| A10 | Yes, supports | aim residual 0.023 rad around ideal lead, leads strafing targets; gun ~5/10 at 150 m; laser 4/5 | consistent with hard/expert |
| A11 | Contradicts | boost at 19.4 m/s to close, jet hop to z 21, juking every 0.3-0.6 s | squad_chase (boost) is closer to reality; add juke + jet hop |
| A12 | Weak support | no turn to our gunfire for 0.5 s before the hit | stays guess |
| A13 | Supports (loot) | had a laser by t 4.9 (spawn is gun only) | lasers looted early; upgrades: no data |

## Strategist, Round 2: kills (2026-11-22)

Premise (moderator): the squad never dies to the zone, so score ≈ 1 + kills, and > 6 needs about 5 kills per match. Real house bots (`notes/research/house-bots.md`): react about 0.6 s, lead within about 0.023 rad, full-charge laser hits 4 of 5 at 100–150 m (90% of our damage taken), boost and zigzag, retaliate for 31 s or more.

### Kill-speed numbers (protocol §7, against 1400 HP)

| Weapon | Damage rate | TTK at 100% hits | Notes |
|---|---|---|---|
| Gun | 45 / 0.24 s = 188/s burst; mag 12 then 2.4 s reload → ~102/s sustained | ~8 s (≥ 16 s at the 50% we land on zigzaggers) | Projectile; misses boosting targets at range |
| Laser (full) | 315 per 0.75 s charge + 1.65 s cooldown = 131/s | 5 beams: 0.75 + 4 × 2.4 = 10.4 s | Hitscan, can't be dodged once released |
| Lightning | 60 / 0.25 s = 240/s, 3 energy per shot (12/s, below the 18/s regen) | 5.8 s, plus chains to 2 more at 0.7× | 45 m, 30° cone, **shorts lasers for 2 s** |
| Laser + gun | ~230/s | ~6 s | |
| Lightning + laser | ~370/s | ~4 s | |
| Their laser on us | 315 × 0.8 / 2.4 s ≈ 105/s each | 1 hunter: 13 s; 2 hunters: 6.7 s | |

What this says: from range with the gun, we lose every even fight, since their laser lands 4 of 5 and our bullets miss a zigzagging target. To get kills we need either **(a) no exposure during their charge**, or **(b) to take their laser away**.

### Ranked behaviours

**K1 (top): lightning ambush (laser denial).**
Lightning hits shorten the target's laser: no charge for 2 s, and we fire every 0.25 s, so a target inside 45 m of us can **never** fire its laser, which is 90% of the damage they deal. Hunters walk to our last known position (shared vision). So: once seen, break LOS around a corner, wait 10–25 m past it facing the corner, and fire lightning when the hunter turns it. We react before them (they react in about 0.6 s; we already aim at the corner). Run lightning + laser (or gun): about 4–6 s TTK while they fight with the gun only, and chains hit a second bot that is following.
- Needs: lightning picked up early (floor loot, crates, NPC kills; we already pick laser then lightning). Prefer **lightning first** when the squad is the opponent.
- Expected: **+1.5 to +2.5 kills/match**, if we hold lightning by about 90 s in about half the matches. Biggest single lever.
- A/B: existing pickup order plus a new ambush hold (brain, about 30 lines: corner point = a `find_cover` spot within 25 m of the LOS-break, aimed at our previous position). A cheap first check, flags only: lightning-first pickup + `_range_pref` close (`s_close` exists) vs s_base2, 56 matches; metric kills from lightning, and their laser hits on us after a short.

**K2: peek laser (exposure shorter than their charge).**
A laser charges with the trigger held, even without LOS. Charge fully behind cover, step out, release the moment LOS opens (aim pre-set to their last known position), step back. We're exposed for about 0.3–0.5 s. They need react 0.6 s + charge 0.75 s ≈ 1.35 s to beam us back, so **their laser can't answer a peek**; only their gun can, at 50% hits on a sidestepping target. One 315 beam per 2.4 s cycle = 5 cycles per kill, about 12 s, taking only gun chip damage.
- Expected: **+1 to +1.5 kills.** Also the best opening move: the first beam lands before they have reacted.
- A/B: PEEK_AFTER_BEAM + LASER_DUCK 30 exist (b_peek); the new piece is "charge while hidden, release on LOS" (combat + brain, about 30 lines). Metric: our beam hits, their beam hits on us per fight.

**K3: space kills to the regen clock.**
Each kill adds a hunter; the dead bot's cubes (+2) give +4% HP and damage each. After a kill, don't take the next fight until HP is ≥ 90% (45 HP/s after 5 s quiet: 1400 HP takes 31 s from 0, about 15 s from half). Move away from the death spot: the kill reveals us (death sound 600 m).
- Expected: +0.5 kills (fewer second fights at half HP), and later deaths.
- A/B: REGEN_BREAK + REGEN_HIDE (built) on top of s_base2; metric: HP at the start of each fight, kills/match.

**K4: upgrades for kills.**
At ~1 kill per match, cube offers are rare (1st cube, 3rd cube). For a kill bot the first offers should be `laser_damage` / `laser_charge` (faster cycles, more alpha: 4 beams per kill instead of 5 at about +10%), not plating. Each cube also gives +4% damage.
- Expected: +0.2–0.4 kills.
- A/B: an economy ORDER variant (laser_damage, laser_charge, plating...) vs s_base2.

**K5 (avoid): gun duels at range.** Our bullets miss zigzagging boosters; their beams land 4 of 5. Never open a fight with the gun beyond 60 m against a laser holder. FIRE_POLICY's "one-shot kill only" can stay for gun-only engagements.

### Will 5 kills happen?

Stacked guesses: K1 + K2 + K3 + K4 ≈ 0.9 + 1.5–2.5 + 1–1.5 + 0.5 + 0.3 → **about 4–5.5 kills, score 5–6.5**, provided we live past 120 s. The 64% of deaths before 120 s are the first test. Run K2 and K1 first, judged by kills per match and deaths before 120 s, on 56 paired matches each. If neither moves kills by +0.7, the house-bot model is the problem, not the tactic.

## Critic round 2 (2026-11-22)

### (1) Is "score ≈ 1 + kills" the only reading of two 1.60s?

Alternatives, ranked by likelihood × how much they would change the plan:

1. **The track rounds to 1 decimal** (`scores.md`: the first entry is "1.6"). Two bots that differ by up to ±0.05 both show 1.6. On 48 matches the SE is ≈ 0.15–0.2, so a real difference of up to ~0.3 is invisible anyway. "Exactly equal" is not evidence; "no detectable change" is. *Check:* none needed. Treat the track as able to detect changes ≥ 0.4 only.
2. **Both bots ran map-free on the track.** `bot.py:10-15` falls back silently when `World(hello["map"]["dir"])` fails. The fight changes then still matter, but cover, LOS, `_exposed` and navigation all degrade the same way in both bots. Map-free play in a squad is about "die early". *Check (cheapest, decisive):* the same container command as the scorer (`check.py --map-dir /arena` under docker with the sandbox flags), then grep stderr for "world load failed". Also time `ready`: world precompute under `--cpus 1 --memory 512m` could exceed the hello budget or hit memory limits on the track box.
3. **We die before any fight logic matters.** Sim: 64% dead < 120 s, median ~100 s. If the track squad's first contact is 2–3 bots with full-charge lasers (house-bots §1: laser 1260 of 1390 damage, 2.2 s to first beam), both bots lose that first exchange the same way. The 876 lines change later fights we never reach. *Check:* a track submission that logs nothing helps little. Instead use the sim: s_base2 death causes by first-contact group size. If most deaths come in the first engagement, fight tuning can't move the score.
4. **Timing.** Our worst ticks were 74–146 ms (A16). Over 50 ms the mech coasts, and after 1 s it idles. If spikes come in fights (cover search + funnel + combat), both bots lose fights to the same idle. *Check:* idle-machine timing under docker `--cpus 1`, p99 and max on fight ticks only.

Reading "score ≈ 1 + kills" is right *for the sim* (0.91 kills + 0.97 other). For the track it is unproven until (2) is ruled out. **Do (2) first. It is the one alternative that would make every past track result meaningless, and it costs one docker run.**

### (2) Which part of the fight model loses the first engagement (`python/brain.py`)

Against a hunter that turns in ~0.6 s, leads, and opens with a full 315 laser 2.2 s after being hit:

1. **We open fights we expect to lose: `OPEN_EDGE` 1.2 + `WEAK_GUN` 0.6** (`brain.py:25-26`, `_ttk_ratio:575`). We open when our time-to-kill is up to 1.2× theirs. And any gun-only enemy has its damage rate cut to 60%. But every bot starts gun-only (`protocol.md` §7), and the stream's bot had a laser by t 4.9 s. So a hard or expert bot holding only a gun looks like a 0.6× threat, the ratio says "win", and we open with a gun at up to 180 m (`OPEN_RANGE`). That reveals us to the whole squad (gun heard at 320 m), against an aim of ~0.02 rad with lead. **This is the most likely loser.** *Fix to test:* `WEAK_GUN = 1.0`, `OPEN_EDGE = 0.8` (open only on a clear edge). Two constants, A/B on paired seeds.
2. **We kite to 130 m (`FIGHT_RANGE`, `_range_pref:749`), the laser's best range.** A laser is hitscan: no lead, 280 m. At 130 m our gun needs lead and lands ~40–50%, while their beam lands 4 of 5 (house-bots §3). Against a laser holder the right range is "out of LOS" or "< 60 m with strafing", not 130 m. *Fix to test:* if `laser in theirs and laser not in mine`, use `_range_pref` = close to 50 m behind cover, or break LOS.
3. **`_dps` averages the laser over its cycle** (315 / 2.4 s ≈ 131 × hit probability). It ignores the alpha strike (315 at once, 22% of our HP), so the first 3 s of a fight are misjudged. Minor next to 1 and 2.
4. **`_ttk_ratio` is one-on-one.** With shared vision a "lone visible" hunter is rarely alone. That is already covered by `others` being empty only in *our* view. Pair it with `danger` within 150 m (as `_may_fire` does).

### Strategist "Round 2: kills"

Not in the file yet at the time of writing. **Partial: the review of the Strategist Round 2 is still open (session ended).**
