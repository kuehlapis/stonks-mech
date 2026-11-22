# 16/56 match-run counterstrategy gate — 2026-11-22

Scope: process rule only. No bot code, simulator behavior, or match batch was
changed.

## Required run classification

After every 16-match screener or 56-match confirmation, classify both:

1. **Wins**
   - direct mech eliminations;
   - NPC/drone-assisted eliminations;
   - zone-assisted eliminations;
   - final-burn/placement outcome;
   - HP and position advantage.
2. **Deaths**
   - cause: gun, laser, lightning, mortar, drone/NPC, zone, collision, or unknown;
   - phase: `<120 s`, `120–300 s`, `300–415 s`, or `>415 s`;
   - cover/LOS state;
   - zone pressure;
   - hunter/squad count;
   - element-of-surprise state;
   - rear/exposed state.

Direct and assisted removals must remain separate. Zone-only or NPC-only
removals may explain placement but are not direct kills.

## Counterstrategy selection

Choose exactly one strongest counterstrategy. It must be justified by the
classified run data and give the largest plausible gain-to-risk ratio.
Evaluate the following themes first:

- element of surprise and a changed re-entry angle;
- cover/LOS breaks and short exposure;
- ambush timing and isolated approaches;
- zone route and position timing;
- safe drone use, routing, or taking/removing drone support;
- weakest-first or isolated squad-hunting, without opening on a group.

Reject alternatives explicitly; do not describe multiple counterstrategies as
simultaneously selected.

## Exactly-one corrective package

The selected package must contain:

- one named hypothesis;
- one primary metric;
- a 16-match screen or 56-match confirmation contract;
- guardrails and an explicit reject/promotion bar;
- direct/assisted removal attribution.

One package may include tightly coupled surprise/cover/ambush behavior if it
tests one mechanism, but it may not bundle independent hypotheses. Do not
launch or queue a second package until this package is classified and
accepted or rejected. Do not re-run an already rejected idea unchanged.

This gate is now in `CLAUDE.md`, `notes/decisions.md`,
`notes/progress.md`, and the ranked 16-match strategy queue.
