# Critic: journal

Owns: `notes/reviews/`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Review the concentrated maximum-hard squad-AOE proposal against protocol:
shared vision, friendly fire, lightning chain, mortar splash, laser timing,
30° lightning cone, NPC support, zone, and exact tier behavior. No code or
match launch is part of this task.

## Previous task

Enforce the match-run counterstrategy gate: after every 16-match screener or
56-match confirmation, review the run's win/death classification, challenge
the selected single strongest counterstrategy, and verify that exactly one
corrective package is proposed. Evidence must cover element-of-surprise,
cover/LOS, ambush, zone, drone, and squad-hunting adaptations. No code or
match launch is part of this task.

Iteration-evaluation review, 2026-11-22: continued from
`notes/progress.md`, the 56-match `b_peek` evidence, and the rebuilt
`c_aim` snapshot. Highest-impact loop change: return to simulator
calibration and raise squad pressure before any bot-switch promotion.
Evidence and exact gates:
`notes/reviews/iteration-evaluation-2026-11-22.md`.
No bot behavior or competing match batch was changed.

Reviewed the next isolated switch after the laser-defense A/B queue:
`AIM_PREDICT` in `python/combat.py` versus `sim/versions/c_aim`.
Found the existing c_aim snapshot is invalid for an isolation test because
it has extra brain/economy differences and is missing s_base2 run-hit fixes.
Output: `notes/reviews/aim-predict-ab-spec-2026-11-22.md`.
No code was edited and no competing match batch was run.

Iteration 3, calibration handoff: identify the highest-value action after
the zone-death trace. Done: trace/fix the v2 squad's pre-415 zone deaths
before any rerun or bot switch work. Evidence and the bounded stop plan are
in `notes/reviews/calibration-next-action-2026-11-22.md`.

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
6. Current: block bot A/B and shipped-bot edits until the squad model has
   0 zone deaths before 415 s on a trace/small smoke and on 40 seeds.

Done when every high-impact finding is fixed in the plan or accepted by the moderator in `notes/decisions.md`.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Maximum-hard model mixes protocol rules with guessed/track-only values | 30 s/3 s memory, exact tier/pressure, and hard-coded zone/weapon values can create a simulator that is more omniscient or different from the engine | Review the concentrated AOE proposal in `notes/reviews/maximum-hard-squad-aoe-2026-11-22.md`; keep protocol vision 5 s, explicit friendly-fire exclusions, live weapon/zone config, and label tier/pressure/movement values as hypotheses | done (2026-11-22) |
| FPS inspiration could become camp, cadence or copy-overfit behaviour | A fixed corner, fixed peek cadence or replay-specific route hides as aim/surprise while reducing adaptation | Reviewed FPS/TenZ/Shroud analogies in `notes/reviews/fps-tactics-2026-11-22.md`: keep protocol bounds, one lever, paired 16/56 gates, no-camping, opponent diversity and direct/assisted kill separation | done (2026-11-22) |
| Post-16/56 runs can become a multitheory stack | Multiple unclassified losses invite parallel fixes and weaken attribution | Require win/death classification, one counterstrategy, and exactly one corrective package | done (2026-11-22) |
| `c_aim` is not an isolated s_base2 snapshot | Extra brain/economy diffs and missing run-hit fixes would confound the AIM_PREDICT effect | Rebuild/review c_aim as a byte-normalized s_base2 copy with only AIM_PREDICT=True; do not run until isolation is proven | in progress |
| Evaluation loop is currently calibration-first, not switch-first | Standalone or uncalibrated A/Bs can improve a proxy while remaining below the track target | Raise squad pressure once, rerun 40-seed paired anchors, then admit only one 56-paired bot switch | in progress |
| v2 squad calibration invalid before bot A/B work | c1 has 407 squad zone deaths in 40 sub1 seeds and 357 in example seeds, so the score columns do not test bot placement | Trace/fix only `sim/bots/squad.py`, 4-match smoke to 0, then 40-seed calibration | done for bounded smoke |
| Sim squad ignores sound and never boosts | Over-rewards run/hide plans (P1/P3) vs track | Ask Tester for a boost+hearing squad variant in A/Bs | open |
| Squad sim calibration unverified | Fixes 3/4 in squad-sim review are guesses | Re-check after Tester runs example vs f803b02 paired on the trace-valid model | open |
| First-fight TTK treats gun-only as weak and spaces every duel at 130 m | Can voluntarily reveal us to a stronger hunter at laser-favourable range | A/B the two isolated, default-off switches in `first-fight-switch-spec-2026-11-22.md` only after calibration | open |
| Nothing reviewed yet | Unchecked assumptions become bugs | Review the plan before building starts | done (game-plan review, 2026-11-21) |
| Findings rest on rule reasoning, not measurement | Severity of finding 3 (edge-hold rear exposure) and finding 9 (estimates) is a guess; wrong ranking wastes builder time | When the Tester's sim runs, ask for rear-hit share inward vs outward facing and the M1 death-time histogram; re-rank | open |
| No re-check of fixes yet | A fix can introduce a new error | Second pass on the revised plan: verify each fix against the same evidence | done: found N1 (fix #6's cap + fix #2's 'no cover = cornered' recreate E1) |
| Online research not compared | Outside tactics may contradict edge-hold | Read `online-recommendations.md` when it lands; add a section | done (summary only; source files `online-*.md` not read) |
| M1 code not reviewed | N1 could survive into code even if the plan is fixed | Review the M1 Brain/Survival diff for the cornered rule and the time guard | open |
| FPS analogies are not yet bounded to protocol mechanics | TenZ/Shroud terms can imply ADS, smoke, headshots or crouch peeks that do not exist | Keep cover/LOS, 50 ms, rear armor, laser timing, zone timing and 5 s memory in every FPS-tactics review; maintain exposure and guardrail limits | done (2026-11-22) |

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
- 2026-11-22, maximum-hard squad-AOE protocol review: read
  `notes/ideas/maximum-hard-squad-2026-11-22.md`, `protocol.md`,
  `notes/research/config.md`, `notes/research/hello.json`,
  `notes/research/house-bots.md`, and `sim/bots/squad.py`. Wrote
  `notes/reviews/maximum-hard-squad-aoe-2026-11-22.md`.
  Verdict: the concentrated model is not protocol-derived. Blocking findings:
  30 s shared memory and 3 s projection exceed the 5 s protocol memory;
  damage bearings must not become synthetic positions; exact tier/pressure
  schedules are unsupported guesses; friendly-fire exclusions are missing;
  mortar, laser and no-target lightning behaviors are incomplete; first-sight
  drone position is not a true drone home; and fixed 150/240/300/415 s and
  25/15 m values require live-config or explicit simulator-only labels.
  No code or match launch was performed.
- 2026-11-22, FPS elite-tactics review: read
  `notes/ideas/fps-elite-tactics-2026-11-22.md`, `protocol.md`,
  `notes/interfaces.md`, `objective.md`, and the existing 16/56 queue.
  Verdict: the document is protocol-valid as strategy only. One package has
  exactly one named lever, with module ownership and evidence/primary metric
  defined. Highest risks are fixed-cadence peeking, corner camping and
  post-hoc opponent fitting. Enforce expiry, relocation, paired seed testing,
  diverse opponent pools, and direct/assisted removal separation. No code or
  match batch was changed.
- 2026-11-22, FPS tactic protocol review: updated
  `notes/reviews/fps-tactics-2026-11-22.md`. Rejected ADS, recoil,
  smoke/flash, headshots, wall-bangs, eco rounds and generic counter-strafe
  as mechanics absent from `mechfight/1`. Marked peeking, pre-aim,
  strafing, crossfire, real cover/LOS and surprise as valid only within
  protocol bounds: 50 ms decisions, gun/mortar/laser timing, rear ×1.5,
  5 s tracks, 1400 base HP, 45 HP/s regen, 415 s final-circle collapse,
  and the 15-mech hunt. Proposed no code or match; next if requested is only
  a bounded laser-aware cover-peek A/B.
- 2026-11-22, post-run counterstrategy gate: read `notes/progress.md`,
  `CLAUDE.md`, the 56-match evidence, and the ranked strategy queue. Added
  a hard rule that every 16/56 run must classify wins/deaths, select one
  strongest counterstrategy, and define exactly one corrective package.
  Reviewed themes: surprise, cover/LOS, ambush, zone, drone, and
  squad-hunting. No code or match was launched.
- 2026-11-22, cover-and-engage review: reviewed
  `notes/ideas/iteration-brainstorm-2026-11-22.md` item 4,
  `notes/ideas/strategies.md` camper/ambusher, `python/brain.py`,
  `python/survival.py`, and `notes/ideas/game-plan.md` against the
  requested corner exposure, camp, zone, rear, timer, economy, and
  `_fight`/`_evade` conflicts. Wrote 9 evidence-ranked findings in
  `notes/reviews/cover-engage-2026-11-22.md`; no code or matches changed.
  Highest impact: a corner camp can become a 2–4 hunter trap and may
  defeat normal zone/TTK/cover priorities if added as a persistent mode.
- 2026-11-22, iteration evaluation: read `objective.md`, `notes/progress.md`,
  `notes/decisions.md`, the 56-match `b_peek` report, the `c_aim` rebuild
  report/spec, and authoritative/post-fix calibration outputs. Evidence:
  `b_peek` 1.96 ± 0.26 versus rerun baseline 2.00 ± 0.25, paired score
  -0.20 ± 0.20 and kills -0.14 ± 0.14; early-death share worsened
  48.2%→51.8%, so PEEK_AFTER_BEAM stays off. `c_aim` is now isolated
  (normalized diff only `AIM_PREDICT`) but has no 56-match result.
  Authoritative current-squad 40-seed results are sub1 1.98 ± 0.29,
  s_base2 2.20 ± 0.29, example 1.40 ± 0.28, all with 0 pre-415 squad zone
  deaths. These miss the 1.6 ±0.2 calibration balance for sub1/s_base2.
  Verdict: the highest-impact loop change is to raise squad pressure once
  (DEFEND_RANGE 60→80, prefer it over changing the hunter schedule), rerun
  40-seed anchors, and hold bot switches until calibration passes.
  Wrote `notes/reviews/iteration-evaluation-2026-11-22.md`; no behavior
  changed and no match batch was launched.

- 2026-11-22, AIM_PREDICT next-switch review: inspected `python/combat.py`,
  `sim/versions/c_aim/combat.py`, `sim/versions/s_base2/combat.py`,
  `python/tests/test_combat.py`, and the 56-match s_base2 baseline.
  Verdict: existing c_aim is invalid for an isolated A/B due to extra
  `brain.py`/`economy.py` diffs and omitted run-hit fixes. Wrote exact
  baseline/candidate commands, isolation requirement, paired metrics,
  promotion gates and runtime/validity guardrails in
  `notes/reviews/aim-predict-ab-spec-2026-11-22.md`. No code or batch changed.

- 2026-11-22, bounded zone fix: replayed seed 2100000 slot 15 and ran a
  4-match pre-fix smoke. The first smoke found an exact-centre
  `ZeroDivisionError` in `sim/bots/squad.py` rather than a remaining zone
  death. Added a simulator-only non-zero-distance guard. Post-fix smoke:
  60 squad mechs, 0 pre-415 zone deaths, 0 errors, 0 late answers.
  Raw: `notes/tests/zone-smoke-4-fixed.json`.
  `python -m unittest discover sim/tests`: 50/50 passed.
  Result: bounded stop condition met; no shipped bot behavior changed.

- 2026-11-22, calibration handoff: ranked the next action after the v2
  calibration and zone traces. c1 sub1 2.23 ± 0.31 and example 1.62 ± 0.34
  are invalid because raw rows contain 407/357 squad zone deaths before
  415 s. Drone routing is also only a 4-match 2.25 smoke, not a 40-seed
  result. Verdict: trace/fix simulator zone routing first, then 40-seed
  sub1/example/s_base2 calibration; no shipped-bot edit or bot switch A/B.
  Output: `notes/reviews/calibration-next-action-2026-11-22.md`.

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
