# Decisions

Moderator's log, newest first. Each entry: what was decided, why, and what was rejected.

## 2026-11-21, iteration 1: start

- **Strategy is chosen by experiment, not by argument.** At the user's request the Strategist writes alternative whole-match strategies (pacifist hider/runner, camper/ambusher, and others) in `notes/ideas/strategies.md`. The top 2–3 get built as A/B candidates against edge-hold and compared in the simulator, then on the track. Rejected: committing to one plan before any measurement.

- **Added a Researcher (online) role** at the user's request: outside research on battle royale strategy, bot competitions, game AI and mech games. A separate agent so it runs in parallel with the local Researcher instead of delaying it.

- **Work branch `iter-1`.** Docs committed there (eaab86f) so worktree agents see the rules and journals. Merge to `main` when the iteration passes the full check.
- **First wave, in parallel:** Researcher (config, map, upgrades, zone), Strategist (game plan), Tester (local simulator), World builder (`python/world.py`). These four don't depend on each other's output.
  - Why: the map model and the simulator are the two long poles, and every later module needs the research facts and the plan.
  - Rejected: building all seven modules at once. Their interfaces depend on the plan, so they'd be rewritten.
- **Simulator reuses `python/world.py`** for geometry instead of its own copy.
  - Why: smallest code; one geometry to fix.
  - Risk accepted: a geometry bug shows up in both bot and sim, so the sim can't catch it. The real track score is the check on that.
- **Python 3.12 is installed locally; the image runs 3.13.** Code must run on both; the Docker check is the one that counts.
- **All four first-wave agents work in the main tree, not worktrees.** Their files don't overlap (notes/research, notes/ideas, sim/, python/world.py), and the Tester needs to see `python/world.py` as soon as it lands. Worktrees return for builders that share files.
