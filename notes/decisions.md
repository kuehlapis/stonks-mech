# Decisions

Moderator's log, newest first. Each entry: what was decided, why, and what was rejected.

## 2026-11-21, iteration 2 (new moderator session): measurement first, then the brain rewrite

- **Ponytail skill waived.** It is not installed on this machine; CLAUDE.md's "always use ponytail" can't be followed. Recorded so later sessions know why.
- **The moderator builds directly; subagents only for large self-contained jobs** (sim phase 2). Why: every behaviour change needs a sim A/B and traces; a builder round-trip per change was too slow. The user gave full control and asked for maximum effort.
- **In-process runner `sim/inproc.py`** (bots as objects, parallel matches, per-slot trace, per-directory module namespaces so old versions can play): 160 matches in about 2 minutes. Rejected: subprocess runner only (slower, no traces).
- **Opponent pool `sim/bots/` (hunter, camper, rusher)** modelled on the recorded built-in (gun + laser, full-charge laser, leads shots, picks up weapons, shoots crates and drones). The real built-ins are unknown; a field of competent aggressive bots is the conservative guess (3 deaths by 37 s in the recorded match).
- **M1 snapshot `sim/versions/m1/`** is the regression baseline. M1 scored 6.9 against 15 example bots: below the example bots themselves.
- **Brain rewrite** (fight model by time-to-kill, strafing, return fire while evading, hysteresis, zone urgency, NPC fights, farming), **2.5D nav with jets** (roofs and the stadium no longer trap us; random trips 40/40 vs 37/40, 17% faster), **path-distance hold point beside walls**, **shadow-side cover search** from wall cells at our own height.
- Measured on sim phase 2 against the pool, 160 matches each: M1 8.41 to new 10.49 (SE 0.32). Zone deaths 0-2%, NPC deaths 0.

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

## 2026-11-21, iteration 1: M1 build

- **M1 interfaces written** (`notes/interfaces.md`) from the revised game plan (all 14 Critic findings addressed). Six builders start in parallel: Perception, Survival, Nav, Combat, Economy, Brain. `python/bot.py` (moderator) wires them, and the Dockerfile now runs `bot.py`.
- **Builders share the main tree.** Each owns one file plus one test file, with no overlaps, and Brain needs the others' real files to integrate. Worktrees would add merges for no gain.
- **Deferred past M1** (per the plan): DPS model, vulture, crates, drones, supply drops, cover map, lightning fallback.
