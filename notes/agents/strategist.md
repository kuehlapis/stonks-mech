# Strategist: journal

Owns: `notes/ideas/`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration 3 brief (moderator): why we die early vs the squad; 2–4 big strategy changes to reach 6+. Status: **written** `notes/ideas/plateau.md` (P1 run doctrine, P2 burn endgame, P3 edge ghost, P4 lone-hunter kill), ranked by expected death time per the Critic's floor-effect finding.


Iteration 1 brief (moderator): write `notes/ideas/game-plan.md`, the survival-first plan: phase plan, fight-or-flee rule, loot and growth, supply drops, endgame, and staging into M1–M4, with the expected effect on mean score per rule and how to measure each in the local simulator. Status: **revised after the Critic's review** (`notes/reviews/game-plan.md`, 3 high, 6 medium, 5 low findings; all fixed, see the plan's "Changes after review").

Second brief, same iteration (moderator): write `notes/ideas/strategies.md`, alternative whole-match styles to A/B against edge-hold (pacifist hider, camper/ambusher, plus others), each with rules, module needs, counters, expected score, sim test, how it does against a field of copies (other teams' AI bots), and one review metric with a pass line. Status: **written.**

## Plan

1. Read the rules (`protocol.md`), the config (`notes/research/config.md`), and the recorded stream for evidence. Done.
2. Derive the facts the score depends on (death order, final burn, zone safety). Done: `game-plan.md` §0.
3. Write the rules with numbers from config names. Done: §2–§8.
4. Stage them into M1–M4 with expected Δ and measurement. Done: §9–§10.
5. Done: `strategies.md` with 7 styles, the copy-robustness table (§8), comparison (§9) and recommendation (§10).
6. Done: fixed all 14 review findings in `game-plan.md`.
7. Next: answer the Critic's review; replace the guessed hit rates and Δ estimates with sim numbers once the Tester's simulator runs.

Done when the Critic has reviewed `game-plan.md` and the high-impact findings are fixed.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No plan yet | Builders need goals to aim at | Write the phase plan first | done (`notes/ideas/game-plan.md`) |
| M1 shortcuts written as if `world.py` didn't exist, and fight rule ignored weapons (review #1, #2) | Those were the review's high findings; E1 would repeat | Fixed: `find_cover` with `los`, weapon-aware fight-back. In future, check `interfaces.md` for what exists before writing a fallback | done |
| Expected Δ per rule are reasoned guesses (ranges like +1.5 to +3) | Wrong estimates pick the wrong next work; noise is ±0.7 per submission | Ablate each M1 rule in the sim with ≥ 100 paired-seed matches; write measured Δ beside each estimate | open |
| Hit-rate table (§1) is assumed | The fight-or-flee rule depends on it; wrong rates mean fights we lose | Ask the Tester to log gun/laser hit rates by distance band in the sim; update §1 | open |
| Built-in bot behavior known from one match (E1) | The edge-hold idea (Z2) assumes bots converge on `next_center`; hunters would beat it | Watch a sim or track-like replay; add a "hunter" opponent variant to the sim pool | open |
| Edge-hold vs center-hold not compared | Z2 is the core M1 positioning bet | Sim A/B: Z2 against walk-to-`next_center`, paired seeds | open |
| Open zone facts: when `next_*` updates, `in_zone` test, dps after 415 s | Final-burn tactics (EG2) and the 8:00 rule depend on them | Researcher to check; adapt EG2/EG4 | open (asked in §0 and §11) |
| Style ranking (strategies.md) is unmeasured | Picks the A/B order for the builders | Run the 3 recommended A/Bs on pools (a), (b), (d); judge each by its §8 metric | open |
| Field of rival AI bots not modeled | Track opponents will copy obvious ideas; styles that win only against brawlers will fall | Ask the Tester for pool (d), the mirror field (4 edge-holders, 4 hiders, 4 farmers, 3 adaptive) | open |
| Plateau proposals P1–P4 unmeasured | Score can't see survival time (floor effect); only death_t shows progress | A/B P1 then P1+P2 on paired seeds, judge by death_t median and % alive 300/400 s | open |
| Whether plating heals, and whether gun can fire while laser charges | Upgrade order and laser+gun DPS | Researcher or sim test | open |

## Lessons

- The recorded stream holds real evidence (who hit whom, when we died): reading `events` took one command and gave the strongest argument in the plan (E1). Check data before reasoning from rules alone.
- Deriving the final-burn fact (radius 0 at 415 s, everyone burns, so max HP at the collapse decides) changed the upgrade order and the endgame. Compute the timeline from config first; it reframes the "8:00 tiebreak" the brief asked about.
- Ask "what if every opponent does this too?" for each idea. It reversed my ranking of the hider (cheap and strong against brawlers, weak against copies) and promoted the farmer.
- Before writing a fallback, check what already exists (`notes/interfaces.md`): I wrote a map-free retreat while `world.los` was already specified, and it was the review's main finding.
- Edit markdown tables by section, not by the first string match: a scripted cell insert hit a same-named row in an earlier table, and I had to repair it.
- Label rules with distinct prefixes from the start (I first used E1 for both evidence and an endgame rule and had to rename).

## Log (newest first)

- 2026-11-22, iteration 3 (plateau): wrote `notes/ideas/plateau.md`. Evidence: Critic `squad-sim-2026-11-22.md` (squad median death 395 s, 19/30 zone; we die ~148 s, score ≈ kills + late squad deaths), `squad.py` (hunters walk, boost only out of zone; hunters = 1 + dead + time; non-hunters fire < 60 m). Own 14-match sim (finished after report): score 2.0, median death 100 s, 57% dead < 120 s, 12/14 by gun; squad 147/210 zone deaths. Added to plateau.md. Lesson: check what the score metric can see before tuning; aggression's earlier gain was measured on a floored score. Next: Tester A/B P1, P1+P2 by death_t.

- 2026-11-22, iteration 3: wrote `notes/ideas/movesets.md` (moves: boost-strafe, hop, backpedal, peek, roof escape, silent walk; weapon matchups and how to exploit each). Proposed A/B: `m_boost`, `m_hop`, `m_both`, `e_far`. Mortar pickup rejected (no aim, cook-off). Results pending.

- 2026-11-21, iteration 1 (third task): revised `notes/ideas/game-plan.md` for the Critic's review. High: (1) engaged = damaged by a mech only, threatened = hide; M1 fight-back needs no enemy laser unless we hold one, `e.hp ≤ 0.8 × self.hp`; (2) `find_cover` with `world.los` over 16 points, boost to cover from lasers; (3) new Z4: face outward during holds while the live edge is > 30 m away, inward after. Medium: Z2 clamp `max(0, …)` + snap off `blocked`; Z1 uses `self.in_zone`; `find_cover` capped at 32 `los` calls (about 10 ms), cached 1 s; unseen-attacker virtual threat; N1 stuck rule; estimates labeled guesses + measurement order. Low: all fixed (margin radius + 12, bisector, range order, gun-only retreat, drones). Added the "Changes after review" table. No disagreement; on #3 I chose facing over a backed wall spot for M1 (cheaper; wall in M2). Next: builders start M1; the Tester's first four measurements in §10.

- 2026-11-21, iteration 1 (second task): wrote `notes/ideas/strategies.md`. Seven styles: pacifist hider, camper/ambusher, vulture, roof sniper, drop chaser, farmer→turtle, adaptive. Each has rules, module needs, counters, expected mean, sim test, behavior when copied, and a review metric (§8). Evidence used: `notes/research/zone.md` (radius 0 at 415 s), `upgrades.md` (plating best), `map.md` (NE core is the densest cover, 244/250 roofs reachable), `stream.md` (gun-only lost to laser at 150 m; 6.4 s obs gap, so timers use `obs.t`; dealing damage resets regen). Ranking: adaptive 10.5–13 > farmer→turtle 9–11 ≈ edge-hold 9–11 > camper 8.5–10.5 > hider 8–10 ≈ vulture 8–10 > sniper 7–9 > drop chaser 6–8. Key reasoning: when the field hides, more matches reach the burn and HP decides, so farming for HP is the copy-robust edge, and pure hiding degrades (hiders tie at 1400 HP). Recommended A/Bs vs edge-hold: farmer→turtle, pacifist hider, ambush add-on. Next: the Tester's pool (d), then the A/Bs.

- 2026-11-21, iteration 1: wrote `notes/ideas/game-plan.md` (phase plan, zone rules Z1–Z3, fight-or-flee with DPS model and M1 simplification, F2 vulture, F3 disengage, L1 gun+laser, G1–G3 cubes/crates/NPCs, U1 upgrade order, S1 drops, EG1–EG5 endgame, aim priority, M1–M4 staging, sim measurement plan, uncertainties). Evidence: config extracted from `check/stream.jsonl.gz` hello (matches `notes/research/config.md`); stream `events` show our gun-only mech opened on a gun+laser mech at about 145 m at t = 5.7 s, took laser hits of 315 at t = 7.9/10.6/19.3/35.9 s, died about t = 37 s, place 13 (`end` line); zone closes at 415 s (Σ phases; agrees with `notes/research/zone.md`); max HP about 2980 lasts 11.5 s at 260 dps, so the burn, not 8:00, decides. Cited `zone.md`, `upgrades.md`, `map.md` (they appeared during the run; no contradictions found, gun sustained DPS 102 vs their 107 is a counting difference, noted). Result: plan ready for Critic. Next: Critic review, then sim ablations of the M1 rules.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
