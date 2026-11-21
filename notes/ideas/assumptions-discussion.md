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
