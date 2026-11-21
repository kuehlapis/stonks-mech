# CLAUDE.md: how agents work on this repo

Goal: `objective.md`: mean score ≥ 12.00 and ≥ 50% wins (current highest score on the track: 6.00).
Rules: `protocol.md` (source of truth), `breakdown.md` (summary), `mechfight.schema.json` (message format).

One **moderator** agent (the main session) coordinates **subagents** that each own one part. The moderator alone decides what ships.

**Always use ponytail.** Every agent, moderator and subagents alike, invokes the `ponytail:ponytail` skill (level `full`) before starting work, and the moderator puts "Invoke the ponytail:ponytail skill first" at the top of every subagent brief. Critics and reviewers use `ponytail:ponytail-review`; whole-repo audits use `ponytail:ponytail-audit`.

## Roles

### Moderator (main session)
- Runs the improvement loop (below) until the objective is met.
- Breaks work into tasks, assigns each to one subagent with a clear brief, and sets the interfaces between modules.
- Resolves conflicts between proposals. When two ideas compete, picks one and records why in `notes/decisions.md`.
- Integrates finished work, runs the full check, and is the **only** agent that commits or merges.
- Writes the final bot and the final report.

### Subagents

| Role | Journal | Does | Produces | Never |
|---|---|---|---|---|
| **Researcher** | `notes/agents/researcher.md` | Reads `protocol.md`, the map files, the recorded stream and the config; answers factual questions with evidence (section numbers, measured values) | `notes/research/<topic>.md` | Writes bot code |
| **Strategist** (ideation) | `notes/agents/strategist.md` | Proposes behaviors that raise the score: phase plans, when to fight or flee, loot priorities, upgrade picks. Each proposal states its expected effect on mean score. | `notes/ideas/<topic>.md` | Writes bot code |
| **Module builder** | `notes/agents/builder-<module>.md` | Implements one module against its interface, with unit tests | Its module file plus tests | Edits another module's file |
| **Critic** | `notes/agents/critic.md` | Reviews proposals and diffs against `objective.md` and the rules: logic errors, rule misreadings, timing risk, crash risk, wasted complexity | `notes/reviews/<target>.md`, findings ranked by impact | Fixes the code itself |
| **Tester** | `notes/agents/tester.md` | Runs the full check and timing; builds and maintains the local simulator and the proxy metrics in `objective.md` | `notes/tests/<date>-<target>.md` with commands and raw results | Changes bot behavior |

### Modules (one builder each)

All bot code lives in `python/` (it becomes the submitted repo's top level).

| Module | File | Journal | Responsibility |
|---|---|---|---|
| World | `python/world.py` | `builder-world.md` | Load `world.json` and `terrain.i16`; height lookup, inside-prism test, line of sight, walkability. Precompute at startup within 5 s. |
| Navigation | `python/nav.py` | `builder-nav.md` | Pathing: walls, ledges, roofs, jet usage, stuck detection |
| Perception | `python/perception.py` | `builder-perception.md` | Track enemies (position, velocity, weapons, HP), sounds, beams, damage bearings; threat estimates |
| Combat | `python/combat.py` | `builder-combat.md` | Aim with lead (gun intercept, mortar arc), laser charge and release, lightning cone, firing discipline, reloads |
| Economy | `python/economy.py` | `builder-economy.md` | Crates, cubes, weapon pickups and swaps, NPC farming, supply drops, upgrade picks |
| Survival | `python/survival.py` | `builder-survival.md` | Zone timing, safe positions, HP and energy management, retreat, cover, facing threats |
| Brain | `python/brain.py` | `builder-brain.md` | Picks the winning goal each tick and combines module outputs into one action |
| Entry | `python/bot.py` | (moderator) | `mf.run(Bot)`: wires the modules together. The Dockerfile entrypoint points here. |

The moderator may add, merge or split modules or roles. When that happens, update these tables and create or archive the matching journal.

## Agent journals (required)

Every agent has a journal at `notes/agents/<name>.md`. It is the agent's memory between runs: a subagent starts cold, so it **reads its journal first** and **updates it before reporting back**. No journal update means the task is not done.

Each journal keeps these sections current:

1. **Current task:** what the agent is working on now, and the brief it came from.
2. **Plan:** the steps it will take and how it will know it's done.
3. **Areas of improvement:** a table, one row per area:
   - *What* is weak or missing
   - *Why* it matters, with the expected effect on mean score or on a proxy metric in `objective.md`
   - *How to be better:* the concrete next change
   - *Status:* open, in progress, done, or dropped (with the reason)
4. **Lessons:** what worked, what didn't and why, and what the agent will do differently next time.
5. **Log:** newest first. One entry per run: date, iteration number, what was done, evidence (commands, numbers, file links), result, next step.

Rules:
- Append to the log; never delete history. Superseded plans move to the log, they aren't erased.
- Every claim needs evidence: a command and its output, a number, a section of `protocol.md`, or a file link.
- The moderator reads every journal at the start of each iteration and picks the next work from their *Areas of improvement*.
- The moderator's own journal (`notes/agents/moderator.md`) also tracks the iteration number, the current milestone and the score history summary.

## The improvement loop

The moderator runs this loop **continuously until the objective in `objective.md` is met** or the user says stop.

1. **Review.** Read `objective.md`, `notes/scores.md` and every journal. State the current milestone and the gap to the next one.
2. **Choose.** Pick the 1–3 improvements with the largest expected gain in mean score per unit of effort. Write the choice and the reasoning in `notes/decisions.md` and the moderator journal.
3. **Research and ideate** where a question is open (Researcher, Strategist). The Critic reviews the proposal before anyone builds it.
4. **Interface.** Update `notes/interfaces.md` when a module's inputs or outputs change.
5. **Build** in parallel: one builder per module, each in its own git worktree (`isolation: "worktree"`).
6. **Review.** The Critic reviews each diff. The builder fixes; the Critic re-checks.
7. **Test.** The Tester runs the full check, the timing and the local simulator, and reports against the guardrails and proxy targets in `objective.md`.
8. **Integrate.** The moderator merges, reruns the full check and commits. Any guardrail failure blocks the merge. Any proxy regression is reverted unless the Critic and the moderator record why it's acceptable.
9. **Submit.** When the build beats the last submission on the proxies, the moderator asks the user to push and submit (or for permission to push), then records the score in `notes/scores.md`.
10. **Record.** The Tester appends this iteration's row to every table in `notes/results.md`: guardrails, local proxies, the change made and its measured effect. Each table also gets the track score once it's known. Every row shows Δ against the previous row and against the baseline. A row is never edited after the fact; a correction is a new row that says what it corrects.
11. **Learn.** Every agent updates its journal: what moved the score, what didn't, and its next areas of improvement. Go to step 1.

Between submissions the loop continues on the local proxies; it does not wait for a score. If a submitted score drops by 1.0 or more, the next iteration starts by finding the cause.

Run in parallel only tasks that are independent. Don't spawn a subagent for a quick question the moderator can answer from the files.

## Briefing a subagent

Every brief from the moderator includes:
- "Invoke the ponytail:ponytail skill first. Read your journal at `notes/agents/<name>.md` first, and update it before you report."
- the role and the one task (one module, one question, one review)
- the files it may read and the files it may write
- the interface it must meet (link `notes/interfaces.md`)
- what "done" means and how it will be checked, in numbers where possible
- the expected output and its file path

Subagents report back: what they did, what they did not do, evidence, open risks, and confirmation that the journal is updated.

## Code rules

- Python 3.13, standard library only. Any dependency must be vendored into the image and justified in `notes/decisions.md`.
- Use `python/mechfight.py` as it is; change it only with a moderator decision.
- Read every balance number from `hello.config`. Never hard-code rule values.
- **Time budget:** `act()` mean ≤ 15 ms, p99 ≤ 35 ms on 1 CPU. Heavy work goes into startup or is spread across ticks.
- **Never crash:** `__init__` and `act()` survive bad or missing data. If the world model fails to load, fall back to map-free behavior (move toward the zone center, fight what you see).
- Logs to stderr via `mf.log`. Nothing but protocol messages on stdout.
- Write files only under `/tmp`.
- Each module has tests in `python/tests/test_<module>.py`, run with `python -m unittest discover python/tests`.
- Smallest change that does the job; no speculative options or abstraction.

## Full check (must pass before any commit to `main`)

```sh
python -m unittest discover python/tests
python3 check/check.py -- python3 -u python/bot.py
docker build -t my-bot python
python3 check/check.py --map-dir /arena -- docker run --rm -i --network none --cpus 1 --memory 512m --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "$PWD/arena:/arena:ro" my-bot
```

Also report per-tick timing (mean, p99, max), `ready` time and memory against the guardrails in `objective.md`.

## Notes layout

```
notes/
  agents/           one journal per agent (required, see above)
  decisions.md      moderator's decision log: what, why, alternatives rejected
  interfaces.md     module signatures and data shapes
  results.md        per-iteration results with deltas: track score, guardrails, proxies, changes
  scores.md         one row per submission
  research/         researcher findings
  ideas/            strategist proposals
  reviews/          critic reviews
  tests/            tester reports
```

## Finalizing

The moderator finalizes when:
1. The objective in `objective.md` is met (O1–O4), as recorded in `notes/scores.md`.
2. The full check passes with every guardrail inside its limit.
3. Every high-impact Critic finding is fixed or explicitly accepted in `notes/decisions.md`.
4. The final report in `notes/decisions.md` states what the bot does, what was tested, what wasn't, and the known risks.

Pushing a public repo and submitting on the track page are outward-facing: the moderator asks the user before each one, unless the user has given standing permission in writing.
