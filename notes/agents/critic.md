# Critic: journal

Owns: `notes/reviews/`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Brief (moderator, iteration 1): review `notes/ideas/game-plan.md` against `protocol.md`, `notes/research/*` and `objective.md` before any builder implements it. Output: `notes/reviews/game-plan.md`, findings ranked by score impact with evidence, fix, severity, and a verdict. Second pass later: compare with `notes/research/online-recommendations.md` once it exists. Next queued: review `notes/interfaces.md` (other modules) when the moderator writes them.

## Plan

1. Check each rule against protocol.md and config values for misreadings. (done)
2. Check M1 rules for logic that loses placement, using E1 (the recorded stream) as a test case. (done)
3. Rank findings by impact on mean score, crash risk and timing risk. (done)
4. Second pass: online-recommendations comparison; re-check the Strategist's fixes for findings 1–4, 6, 8. (open)

Done when every high-impact finding is fixed in the plan or accepted by the moderator in `notes/decisions.md`.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Nothing reviewed yet | Unchecked assumptions become bugs | Review the plan before building starts | done (game-plan review, 2026-11-21) |
| Findings rest on rule reasoning, not measurement | Severity of finding 3 (edge-hold rear exposure) and finding 9 (estimates) is a guess; wrong ranking wastes builder time | When the Tester's sim runs, ask for rear-hit share inward vs outward facing and the M1 death-time histogram; re-rank | open |
| No re-check of fixes yet | A fix can introduce a new error (e.g. outward facing while the edge closes) | Second pass on the revised plan: verify each high finding's fix against the same evidence | open |
| Online research not compared | Outside tactics may contradict edge-hold | Read `online-recommendations.md` when it lands; add a section | open |

## Lessons

- Running the plan's own evidence (E1) through its own M1 rules found the worst bug (finding 1): the simplified rule fights E1's losing fight. Next time: replay every cited example through the simplified rule, not only the full model.
- Plans written in parallel with a module assume that module is missing ("M1 without world"). Check what already exists in the tree (`python/world.py`, `notes/interfaces.md`) before accepting a fallback.
- Checking a single number in the stream (who hit first, where the enemy was aiming) settled a claim in minutes. Prefer one-line stream queries over arguing.

## Log (newest first)

- 2026-11-21, iteration 1: reviewed `notes/ideas/game-plan.md`. Evidence: protocol.md §2–§11, `notes/research/{config,zone,upgrades,map,stream}.md`, `notes/interfaces.md` (los ≤ 0.3 ms), `breakdown.md` §13; stream query `python -I -c "...events/mechs for t<12..."` over `check/stream.jsonl.gz` showed our first hit on mech 10 at t = 5.7 (rear, 144 m, mech 10 aim ~68° off us) before its first damage at 7.9. Result: `notes/reviews/game-plan.md`, 14 findings (3 high: M1 fight-back ignores weapons and repeats E1; M1 disengage doesn't break LOS vs hitscan laser + 5 s memory; edge-hold faces inward while arrivals come from behind during holds). Verdict: ready with listed fixes. `online-recommendations.md` absent. Next: second pass after the Strategist revises and the online file lands.
- 2026-11-21, iteration 0: journal created. Next: start the current task.
