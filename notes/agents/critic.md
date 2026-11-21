# Critic: journal

Owns: `notes/reviews/`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

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
| Nothing reviewed yet | Unchecked assumptions become bugs | Review the plan before building starts | done (game-plan review, 2026-11-21) |
| Findings rest on rule reasoning, not measurement | Severity of finding 3 (edge-hold rear exposure) and finding 9 (estimates) is a guess; wrong ranking wastes builder time | When the Tester's sim runs, ask for rear-hit share inward vs outward facing and the M1 death-time histogram; re-rank | open |
| No re-check of fixes yet | A fix can introduce a new error | Second pass on the revised plan: verify each fix against the same evidence | done: found N1 (fix #6's cap + fix #2's 'no cover = cornered' recreate E1) |
| Online research not compared | Outside tactics may contradict edge-hold | Read `online-recommendations.md` when it lands; add a section | done (summary only; source files `online-*.md` not read) |
| M1 code not reviewed | N1 could survive into code even if the plan is fixed | Review the M1 Brain/Survival diff for the cornered rule and the time guard | open |

## Lessons

- Fixes interact: a cap added for timing (#6) plus "none = cornered" (#2) made a new E1 path. On a second pass, trace each original failure case (E1, open ground, 2+ threats, no map) through the combined fixes, not each fix alone.

- Running the plan's own evidence (E1) through its own M1 rules found the worst bug (finding 1): the simplified rule fights E1's losing fight. Next time: replay every cited example through the simplified rule, not only the full model.
- Plans written in parallel with a module assume that module is missing ("M1 without world"). Check what already exists in the tree (`python/world.py`, `notes/interfaces.md`) before accepting a fallback.
- Checking a single number in the stream (who hit first, where the enemy was aiming) settled a claim in minutes. Prefer one-line stream queries over arguing.

## Log (newest first)

- 2026-11-21, iteration 1, second pass: verified the revised plan's "Changes after review" line by line against its §1, §3, §4 text. 13/14 fixed, #2 partly. New: N1 (high, M1-blocking): `find_cover` returning none (open ground within 30 m, ≥2 threats exhausting the 32-call cap, or no world) makes M1 'cornered' and fire back, i.e. E1 again; fix = cornered also needs threat ≤ 60 m or energy < 20, else boost away. N2 (medium): no perf_counter guard (`CLAUDE.md` L114 sets budget, no guard). N3 (low): `strategies.md` §7 keeps the old double-1.3 Z1 formula. Online top 15: 7 covered, online #2 (≥2-of-4 go rule) and #14 mortar use rejected with §7 evidence, top M2+ adds: gun lead → M2, min-risk hold side, oldest-scanned sweep, move inside drop ring, dodge (M3). Written to `notes/reviews/game-plan.md` "Second pass". Next: review M1 code for N1/N2.

- 2026-11-21, iteration 1: reviewed `notes/ideas/game-plan.md`. Evidence: protocol.md §2–§11, `notes/research/{config,zone,upgrades,map,stream}.md`, `notes/interfaces.md` (los ≤ 0.3 ms), `breakdown.md` §13; stream query `python -I -c "...events/mechs for t<12..."` over `check/stream.jsonl.gz` showed our first hit on mech 10 at t = 5.7 (rear, 144 m, mech 10 aim ~68° off us) before its first damage at 7.9. Result: `notes/reviews/game-plan.md`, 14 findings (3 high: M1 fight-back ignores weapons and repeats E1; M1 disengage doesn't break LOS vs hitscan laser + 5 s memory; edge-hold faces inward while arrivals come from behind during holds). Verdict: ready with listed fixes. `online-recommendations.md` absent. Next: second pass after the Strategist revises and the online file lands.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
