# Critic: journal

Owns: `notes/reviews/`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Brief (moderator, 2026-11-22 #8): specify exactly two off-default first-fight
switches (conservative gun-only opening and laser-aware range) without code
edits. Done: `notes/reviews/first-fight-switch-spec-2026-11-22.md`.

Brief (moderator, 2026-11-22 #7): critic round 2: why two bots both 1.60; fight model first-engagement loser; review Strategist Round 2 when it appears (pending; session ended, carry over).

Brief (moderator, 2026-11-22 #6): rank assumptions A1-A23, cheapest checks, how to reach 6.00; output Critic section in notes/ideas/assumptions-discussion.md. Done.

Brief (moderator, 2026-11-22 #5): review plateau.md Zone-smart ZS1-3; output notes/reviews/zone-smart-2026-11-22.md. Done.

Brief (moderator, 2026-11-22 #4): diff review 5bc9b89..65bd2fe python/; output notes/reviews/diff-65bd2fe.md. Done.

Brief (moderator, 2026-11-22 #3): review notes/ideas/plateau.md P1-P4; output notes/reviews/plateau-2026-11-22.md. Done.

Brief (moderator, 2026-11-22 #2): review online-squad-survival.md vs the floor effect; output notes/reviews/squad-survival-2026-11-22.md. Done.

Brief (moderator, 2026-11-22): review squad sim for harshness/uniformity/bugs; output `notes/reviews/squad-sim-2026-11-22.md`. Done.

Earlier:

Brief (moderator, iteration 1): review `notes/ideas/game-plan.md` against `protocol.md`, `notes/research/*` and `objective.md` before any builder implements it. Output: `notes/reviews/game-plan.md`, findings ranked by score impact with evidence, fix, severity, and a verdict. Second pass (done 2026-11-21): verify the 14 fixes in the revised plan, compare with `online-recommendations.md`, check `strategies.md`, flag M1 items separately. Next queued: review `notes/interfaces.md` (other modules) when the moderator writes them.

## Plan

1. Check each rule against protocol.md and config values for misreadings. (done)
2. Check M1 rules for logic that loses placement, using E1 (the recorded stream) as a test case. (done)
3. Rank findings by impact on mean score, crash risk and timing risk. (done)
4. Second pass: online-recommendations comparison; re-check the Strategist's fixes. (done: 13 fixed, #2 partly; new N1 M1-blocking, N2, N3)
5. Re-check N1 fix in plan/code when M1 lands; review M1 diffs. (open)

Done when every high-impact finding is fixed in the plan or accepted by the moderator in `notes/decisions.md`.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Sim squad ignores sound and never boosts | Over-rewards run/hide plans (P1/P3) vs track | Ask Tester for a boost+hearing squad variant in A/Bs | open |
| Squad sim calibration unverified | Fixes 3/4 in squad-sim review are guesses | Re-check after Tester runs example vs f803b02 paired | open |
| First-fight TTK treats gun-only as weak and spaces every duel at 130 m | Can voluntarily reveal us to a stronger hunter at laser-favourable range | A/B the two isolated, default-off switches in `first-fight-switch-spec-2026-11-22.md` only after calibration | open |
| Nothing reviewed yet | Unchecked assumptions become bugs | Review the plan before building starts | done (game-plan review, 2026-11-21) |
| Findings rest on rule reasoning, not measurement | Severity of finding 3 (edge-hold rear exposure) and finding 9 (estimates) is a guess; wrong ranking wastes builder time | When the Tester's sim runs, ask for rear-hit share inward vs outward facing and the M1 death-time histogram; re-rank | open |
| No re-check of fixes yet | A fix can introduce a new error | Second pass on the revised plan: verify each fix against the same evidence | done: found N1 (fix #6's cap + fix #2's 'no cover = cornered' recreate E1) |
| Online research not compared | Outside tactics may contradict edge-hold | Read `online-recommendations.md` when it lands; add a section | done (summary only; source files `online-*.md` not read) |
| M1 code not reviewed | N1 could survive into code even if the plan is fixed | Review the M1 Brain/Survival diff for the cornered rule and the time guard | open |

## Lessons

- 'Looks weak' gates: check what every tier looks like at the start (all tiers start gun-only), not only the weak tier.
- New fight modes must be traced through post-filters (FIRE_POLICY fire/reload) or they silently do nothing.
- Hide logic: check where the opponent model *goes* (squad walks to last known + 3 s vel), not only whether LOS is broken. Hiding at the last-seen spot invites the hunter in.
- Speed claims: compute the sustained average from drain/regen (boost here: ~15.5 m/s pulsed vs 11.7 walk), then compare with weapon range. Outrunning a 230 m gun is not escape.
- A score that never moves can be a floor effect, not a bug: check what the score can see (here: only squad deaths before ours) before blaming the model.

- Movement proposals: check the air model (air_accel, what boost does airborne) before judging a dodge.

- Fixes interact: a cap added for timing (#6) plus "none = cornered" (#2) made a new E1 path. On a second pass, trace each original failure case (E1, open ground, 2+ threats, no map) through the combined fixes, not each fix alone.

- Running the plan's own evidence (E1) through its own M1 rules found the worst bug (finding 1): the simplified rule fights E1's losing fight. Next time: replay every cited example through the simplified rule, not only the full model.
- Plans written in parallel with a module assume that module is missing ("M1 without world"). Check what already exists in the tree (`python/world.py`, `notes/interfaces.md`) before accepting a fallback.
- Checking a single number in the stream (who hit first, where the enemy was aiming) settled a claim in minutes. Prefer one-line stream queries over arguing.

## Log (newest first)

- 2026-11-22 #8: inspected `brain.py` opening, TTK, and range paths. Wrote
  `notes/reviews/first-fight-switch-spec-2026-11-22.md`: exactly two default-off
  A/Bs, no code edits. Switch A changes the gun-only multiplier to 1.0 plus
  voluntary-open edge to 0.8 only while enabled; Switch B uses a 50 m target
  only versus an enemy laser when we lack one. Deferred remembered-enemy and
  laser-alpha modelling to avoid confounding these A/Bs. Evidence: brain.py
  lines 25–26, 355–366, 575–596, 739–753; discussion Round 2 lines 116–121.

- 2026-11-22 #7: round 2. Track rounds to 1 decimal (scores.md '1.6'), SE ~0.2 so equal 1.60 is weak evidence. Cheapest decisive check: scorer-style docker run, grep 'world load failed' (bot.py:15 silent map-free fallback). Fight loser: OPEN_EDGE 1.2 + WEAK_GUN 0.6 open fights vs gun-only hard bots; kiting to 130 m favours lasers. Strategist Round 2 not yet written.
- 2026-11-22 #6: assumptions ranking. Top: A23 (is 6.00 from this squad?), A4/A3 (check (16-place)-kills from track end messages), A7, A8 (sim sensitivity runs), A15 (cross-version comparisons invalid). Recommend no builds until checks 1-2.
- 2026-11-22 #5: zone-smart review. Burn HP math right (2981 HP/11.5 s) but 3 plating unlikely; gun-only != easy (all tiers start gun-only); ladder hits mediums after kill 2 (n=1+dead) -> cap 2 kills/150 s; FIRE_POLICY blocks ladder shots (brain.py:137) and reload in the open (:152). Expect ZS1 ~+1.
- 2026-11-22 #4: diff 65bd2fe review. Must fix: run-wait holds at last-seen spot (squad walks there), stale _run_spot, run-wait blocks non-urgent zone travel 30 s. Should: boost without cover, run-finish not 'alone', tests. No crash or >50 ms path found (worst ~45 los).
- 2026-11-22 #3: plateau review. P1 must break LOS, not outrun (boost avg ~15.5 vs 11.7 m/s, gun 230 m); trees block vision (protocol.md:369-372) so 'never trees' is a misread; squad memory is 30 s (squad.py:118); P3 vs ZONE_LEAN conflict + edge speed 7.2 m/s > 5 m/s silent; P2 regen before 375 s; sim over-rewards P1/P3 (no sound, no boost).
- 2026-11-22 #2: squad-survival review. Keep R6 (fix: hold fire only once LOS is broken; regen also needs no damage taken, protocol.md:291), R3, R1 (funnel + fallback share one LOS_CAP=40 counter, survival.py:223/250/277), R4a. Drop R4b, R2'.
- 2026-11-22: squad sim review. 2-match run seed 7: squad deaths 19 zone/7 NPC/2 us, median 395 s; ours 148 s, score 1.0. Finding 1: score is a floor effect; use death_t. No scoring bug. File: notes/reviews/squad-sim-2026-11-22.md.

- 2026-11-22, iteration 1: reviewed movesets diff + `notes/ideas/movesets.md` -> `notes/reviews/movesets-2026-11-22.md`. Top: hop misreads air control (`air_accel` 12 vs 58.5, protocol L279) so a hop is a 1 s straight line; boost while airborne = jet (L227) so `m_both` jets; boost-strafe at E>40 starves lightning (17+12 energy/s, regen delay 0.6 s). HOLD_SEARCH off is fine. Next: re-check after A/B results.

- 2026-11-21, iteration 1, second pass: verified the revised plan's "Changes after review" line by line against its §1, §3, §4 text. 13/14 fixed, #2 partly. New: N1 (high, M1-blocking): `find_cover` returning none (open ground within 30 m, ≥2 threats exhausting the 32-call cap, or no world) makes M1 'cornered' and fire back, i.e. E1 again; fix = cornered also needs threat ≤ 60 m or energy < 20, else boost away. N2 (medium): no perf_counter guard (`CLAUDE.md` L114 sets budget, no guard). N3 (low): `strategies.md` §7 keeps the old double-1.3 Z1 formula. Online top 15: 7 covered, online #2 (≥2-of-4 go rule) and #14 mortar use rejected with §7 evidence, top M2+ adds: gun lead → M2, min-risk hold side, oldest-scanned sweep, move inside drop ring, dodge (M3). Written to `notes/reviews/game-plan.md` "Second pass". Next: review M1 code for N1/N2.

- 2026-11-21, iteration 1: reviewed `notes/ideas/game-plan.md`. Evidence: protocol.md §2–§11, `notes/research/{config,zone,upgrades,map,stream}.md`, `notes/interfaces.md` (los ≤ 0.3 ms), `breakdown.md` §13; stream query `python -I -c "...events/mechs for t<12..."` over `check/stream.jsonl.gz` showed our first hit on mech 10 at t = 5.7 (rear, 144 m, mech 10 aim ~68° off us) before its first damage at 7.9. Result: `notes/reviews/game-plan.md`, 14 findings (3 high: M1 fight-back ignores weapons and repeats E1; M1 disengage doesn't break LOS vs hitscan laser + 5 s memory; edge-hold faces inward while arrivals come from behind during holds). Verdict: ready with listed fixes. `online-recommendations.md` absent. Next: second pass after the Strategist revises and the online file lands.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
