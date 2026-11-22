# Decisions

Moderator's log, newest first. Each entry: what was decided, why, and what was rejected.

## 2026-11-22, match-run counterstrategy rule

- **After every 16-match screener or 56-match confirmation, classify wins and deaths before choosing another experiment.** Wins remain separated into direct kills, NPC/drone-assisted removals, zone-assisted removals, final-burn placement, and HP/position wins. Deaths are classified by weapon/cause, phase, cover and LOS state, zone pressure, hunter/squad size, surprise state, and rear/exposed state.
- **Identify exactly one strongest counterstrategy** per run. The selection uses the dominant loss/win evidence and chooses the highest plausible gain-to-risk response. Preferences, in order when applicable: element of surprise, cover/LOS, ambush timing, zone timing/position, safe drone use or drone routing, and isolated weakest-first squad hunting. A generic "fight better" response is not specific enough; record the exact mechanism and metric.
- **Build exactly one corrective package and no competing package.** It may contain only one named hypothesis, one primary metric, explicit guardrails, and either a 16-match screen or a 56-match confirmation contract. Stacking multiple hypotheses, re-running a rejected idea unchanged, or queueing two corrective arms is forbidden. The 16/56 result record must state why alternatives were rejected.
- The package must resist adaptation: vary angles, approach timing, cover, and re-engagement; do not add persistent camping or rear exposure. Drone and zone effects are support and must not be credited as direct kills.
- Applied to `CLAUDE.md`'s improvement loop and the existing ranked queue. Record each application in `notes/reviews/` or this decision log and update the Critic and Strategist journals.

## 2026-11-22, iteration 3: placement scoring, strategy and moveset A/B

- **Clarification:** zone and NPC/drone effects may support kills. The objective is for our mech to control the match so the field ends as a win: assisted eliminations count when they improve survival or reduce threats. The 1.6 submission is the baseline. Valid measurements must distinguish direct kills from assisted/external eliminations rather than forbid external effects.
- **Maximum-hard-squad and learning directive:** build the strongest defensible simulator opponent from protocol and evidence, then learn one root-cause countermeasure after each batch. Keep the opponent and bot changes isolated: never tune one to mask a weakness in the other.

- **Scoring is placement** (16 − place), confirmed by the user. The sim already scores this way (`sim/inproc.py` summarize).
- **The squad format is confirmed** by the user's paste of the track page: practice = us vs 15 house bots acting as one squad, and the leaderboard ranks the best practice score. The squad sim stays the test bed; a free-for-all batch was started on a wrong doubt and then stopped.
- **Waiting-spot (hold point) search off** (`survival.HOLD_SEARCH = False`, user request): 50–62 ms worst case, over budget. It is re-applied: a working-tree reset had dropped it.
- **New moves, off by default, for A/B:** `brain.STRAFE_BOOST_E` (boost-strafe above that energy) and `brain.STRAFE_JUMP` (hop chance on each strafe reversal). Why: `notes/ideas/movesets.md`.
- **Weapon pickups: no "nearest regardless".** We already take the nearest laser or lightning. Rejected the mortar: combat can't aim it, and holding one gives enemy lasers +60% on us. Testing `e_far` (walk 30 s for a weapon instead of 15 s).
- **Batches (112 squad matches each, seed 1):** strategies `s_base s_hide s_search_on s_close s_duck30 s_picky` (`notes/tests/strat/run_sq.sh`), then moves `m_boost m_hop m_both e_far` (`run_moves.sh`). Results and the AAR follow.

## 2026-11-21 night, iteration 2: the track is us vs a hunting squad

- **Fact that changed the plan** (track page): 15 house bots act as one squad (shared vision, never fight each other, hunt us weakest first, more as we kill them, all of them late). Our score = 15 − squad bots alive at our death. Hiding can't win; kills and late survival do.
- **`sim/bots/squad.py`** models the squad. `DEFEND_RANGE = 60` (non-hunters shoot us within 60 m) chosen by calibration: the example bot scores 1.01 here (1.70 at 0 m) vs 1.15 on the track.
- **Adopted (each measured against the squad sim, 112–140 matches):** aggression (fight edge 1.2, open fire on lone enemies at ratio < 1.2, gun-only enemies' damage × 0.6): 1.40 → 1.74; group fights (edge 1.5); fast random strafing (0.25–0.7 s); projectile dodge; lightning firing and laser-then-lightning pickups; eager cube pickup; laser duck; kiting at 130 m (neutral, kept).
- **Rejected or kept off, no measurable gain:** roof holding (`HOLD_ROOF`, also causes late answers), exposure weight changes, supply-drop changes, upgrade-order changes, fight ranges 100–170 m.
- **Root `Dockerfile` added** so the repo can be submitted as-is (builds `python/`). Full check passes under the Docker sandbox (ready 1.6 s, max tick 17 ms, 40 MB).
- **Plateau:** the squad sim sits at about 1.9–2.0 whatever the behaviour; its structure (shared vision, hunters added per kill) may cap it. Real submissions are the next measurement; the moderator can't submit (track sign-in), so the teammate must.

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

## 2026-11-22, iteration 3b: continuous agent feedback loop (user request)

- The moderator evaluates every agent report against evidence and sends feedback back to that agent (revise, go deeper, or next task) instead of one-shot launches.
- Chain: Strategist + Researcher (online) proposals → Critic review → moderator feedback → builder (switch, off by default) → squad A/B → results back to Strategist and Critic → next round. Runs until mean > 6.00 or the user stops it.

## 2026-11-22, iteration 3c: calibrate the squad to the track (user directive)

- The squad model must reproduce the track: the submitted bot (f803b02, `sim/versions/sub1`) scores 1.6 ± 0.2 and the example bot 1.15 ± 0.2, 40 seeds each. Until then no sim A/B decides anything.
- Why: nothing built this session beat the current bot, and the critic showed the sim's guesses (instant 30 s shared vision, hunter schedule, 60 m defend range) may squeeze every build to the same score. The only real behaviour data (`notes/research/house-bots.md`, one FFA recording) shows bots that boost, zigzag, lead and land full lasers, so realism changes come first, knob tuning second.
- Rejected: calibrating on the current `s_base` (876 lines newer than the submission).
