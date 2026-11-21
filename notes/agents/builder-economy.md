# Builder: economy: journal

Owns: `python/economy.py` and `python/tests/test_economy.py`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration 1 / M1 (moderator brief): `python/economy.py` per `notes/interfaces.md` "M1 modules": `pick` (U1), `wanted_pickup` and `take` (L1, lasers only). Built; awaiting Critic review.

## Plan

1. Rank pickups, crates and cubes by value, distance and danger.
2. Weapon choice by the triangle.
3. Upgrade pick priority.
4. Supply drop capture when uncontested.

Done when the module meets `notes/interfaces.md`, its tests pass, and the full check passes with timing inside the budget.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| Takes any weapon, picks upgrade 0 | Wasted power growth | Value-based pickup and upgrade choice | done for M1 (U1 order + L1 lasers) |
| No lightning fallback (L1) | Slot 1 often empty if no laser near; lightning shorts enemy lasers | Take lightning at t ≥ 60 s with eta ≤ 4 s, swap for a laser later | open (deferred by game-plan §9) |
| We never drop a mortar we hold | A held mortar takes +60% from lasers (cook-off) | Only matters if Brain/others ever take one; add `drop` of a mortar slot if seen | open |
| Threat check uses straight distance and threat's last known pos | May walk into a mech that moved | Use threat velocity × age once Perception gives reliable vel | open |
| Cubes, crates, drops, NPC farming not built | G1–G3, supply drops: +0.3 to +1 (game-plan §5 guess) | M2 | open |

## Lessons

- `check/stream.jsonl.gz` has no `offer` and no `took`/`take_failed` events (300 obs); offer tests use the protocol §10 shape with real ids from `config.upgrades`.
- Process `take_failed` events in a helper called by both `wanted_pickup` and `take`, so the backoff works whichever one Brain calls (idempotent per obs).

## Log (newest first)

- 2026-11-21, iteration 1: built `python/economy.py` (~85 lines) and `python/tests/test_economy.py` (12 tests). `python -m unittest python.tests.test_economy -v` → 12 OK on Python 3.12.4 (3.13 not installed on this machine). Stream replay of 300 obs: pick+wanted_pickup+take well under 1 ms/tick (test asserts < 1 ms). U1 fallback for ids not in the plan list: their `config.upgrades` order, then unknown ids, ties by offer index. `drop` with both slots full: the non-gun slot (slot 1 if neither is a gun). Not done: lightning fallback (deferred), "detour keeps Z1" (Brain's job), never-swap-while-engaged (Brain's job). Next: Critic review, then M2 cubes/crates.

- 2026-11-21, iteration 0: journal created. Next: start the current task.
