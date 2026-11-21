# Objective

Build the mechfight bot with the **highest mean score on the Mech Royale track**, finishing **1st (last mech alive) in at least half of its matches**.

Rules and numbers: `protocol.md` and `hello.config`. Summary: `breakdown.md`.

## Where we start

- **Current highest score: 6.00.** That is a mean of about 10th place out of 16.
- Our own bot: not yet submitted. The example bot is the starting code.

## How score works

- Each match gives `16 − place` points: 1st = 15, 2nd = 14, …, 16th = 0.
- A submission's score is the mean over its **48 practice matches**.
- If the clock runs out (8:00), survivors are ranked by HP.
- Kills give no points by themselves.
- **Noise:** with 48 matches, the mean moves by about ±0.7 between identical submissions. A difference under **1.0** between two submissions is not evidence that one is better.

## The objective (done when all are true)

| # | Requirement | Number |
|---|---|---|
| O1 | Mean score on one submission | **≥ 12.00** |
| O2 | Same requirement held on the next submission with no code change in between, or the mean of two consecutive submissions | **≥ 12.00** |
| O3 | Win rate, if the submission page shows placements | **≥ 50%** (≥ 24 of 48 matches in 1st) |
| O4 | Conformance check at submission | **passes, first try** |

12.00 is twice the current best and means an average place of 4th or better. Together with O3, it means the bot wins most matches and places near the top in the rest.

## Milestones (in order)

| Milestone | Mean score | What it takes |
|---|---|---|
| M0: Valid | any score, check passes | Bot builds, passes `check.py` under the Docker sandbox, never crashes |
| M1: Best on track | **> 6.00** (aim ≥ 7.00 to clear the noise) | Survives the zone every match, avoids early fights |
| M2: Top half | **≥ 8.00** | Average place 8th or better: safe looting, regen, disengaging |
| M3: Top quarter | **≥ 10.00** | Average place 6th or better: wins most fights it takes, good weapons and cubes |
| M4: Objective | **≥ 12.00**, plus O2–O4 | Strong endgame: last-circle positioning, aiming, finishing weakened opponents |

## Guardrails (must hold on every build, measured locally)

| Metric | Limit | How measured |
|---|---|---|
| Conformance check | passes directly and under the Docker sandbox | `check.py` commands in `CLAUDE.md` |
| Crashes or exceptions in `act()` | **0** over the recorded stream and every local test | stderr log count |
| Per-tick decision time | **mean ≤ 15 ms, p99 ≤ 35 ms, max < 45 ms** on 1 CPU | timing over `check/stream.jsonl.gz` |
| Late answers | **0%** (the check fails above 2%) | `check.py` report |
| `ready` time including map load | **≤ 5 s** (limit is 20 s) | timed in the Docker run |
| Memory | **≤ 256 MB** (limit is 512 MB) | `docker stats` during the check |
| Repo size at submit | **≤ 10 MB** (limit is 20 MB) | `git count-objects -vH` |
| Docker build time | **≤ 3 min** (limit is 10 min) | timed `docker build` |

## Local proxy targets (once a local simulator exists)

The track shows only the mean score, and matches show no logs. So the team needs a local simulator (owned by the Tester) to measure behavior between submissions. Targets on it, over at least 100 simulated matches against copies of earlier versions and the example bot:

| Metric | Target |
|---|---|
| Deaths to the zone | **0%** of matches |
| Time spent outside the zone | **≤ 2%** of ticks alive |
| Mean place against the example bot × 15 | **≤ 2.0** |
| Win rate against the previous best version × 15 | **≥ 1/16 + 10 points** (better than an even share) |
| Gun hit rate on moving targets 50–150 m away | **≥ 40%** |
| Rear-hit share of damage taken | **≤ 20%** |
| HP when fewer than 3 mechs remain | **≥ 60% of max** on average |
| Supply drops captured when uncontested | **≥ 80%** |

These are proxies. A change that improves them but lowers the real score is reverted.

## Priorities, highest first

1. **Never lose the bot:** no crash, no late answer, no idling.
2. **Never die to the zone.** Be inside the next circle before the shrink.
3. **Avoid fights you would lose.** Disengage, break line of sight, regen (45 HP/s after 5 s).
4. **Get stronger safely:** crates, cubes, weapons by the triangle, uncontested supply drops.
5. **Win the endgame:** face threats (rear hits do ×1.5), lead shots, use cover.
6. **High HP late:** HP decides the order if time runs out.

## Hard constraints

- Python 3.13, standard library only, or vendored dependencies. No network at runtime.
- 1 CPU, 512 MB, read-only disk except `/tmp`, uid 65534.
- 50 ms per decision, round trip.
- Repo ≤ 20 MB, Docker build ≤ 10 minutes on linux/amd64.
- Every balance number read from `hello.config`.

## Non-goals

Kill counts, style, spectator appeal, generality beyond `mechfight/1`, exact physics.

## Recording progress

Every submission gets a row in `notes/scores.md`: date, commit, mean score, win rate if shown, milestone reached, and what changed since the last submission.
