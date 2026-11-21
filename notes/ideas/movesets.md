# Movesets and weapon matchups

Strategist, 2026-11-22. All numbers from `protocol.md` §7–8 and `hello.config` (`check/stream.jsonl.gz`).
Each idea says what the bot does today, the proposal, and the A/B that decides it.

## Movement facts that matter

| Fact | Value | Consequence |
|---|---|---|
| Walk / boost speed | 11.7 / 19.5 m/s | Boost moves us 67% further sideways per bullet flight |
| Boost drain / energy regen | 17/s, regen 18/s after 0.6 s idle | About 6 s of continuous boost from 100 energy; short pulses refill |
| Jump speed, gravity | 11 m/s, 22 m/s² | A hop lasts 1.0 s and rises 2.75 m; our path stops being a straight line |
| Jet | 34 m/s² up, cap 10 m/s, 15 energy/s | 100 energy climbs about 60 m: almost every roof |
| Turn rate | 4 rad/s yaw | Nobody can be out-circled: from 45 m an orbit at 19.5 m/s is 0.43 rad/s |
| Rear arc | Outside the 180° front arc: ×1.5 | Movement is independent of aim, so we can back off while facing the enemy |
| Gun bullet | 252 m/s | 0.52 s to 130 m, 0.9 s to 230 m |
| Sound | Steps above 5 m/s, boost is louder | Slow walking is silent |

## Moves

| Move | Today | Proposal | Why | Test |
|---|---|---|---|---|
| **Strafe left/right** | Walk speed, random reversal every 0.25–0.7 s | Boost-strafe while energy > 40 (`STRAFE_BOOST_E`) | A shooter leading at 130 m has to guess 10 m of sideways travel instead of 6 m; our radius is 2.5 m | `m_boost` |
| **Hop** | Never jumps in fights | 30% chance to hop on each reversal (`STRAFE_JUMP`) | Shooters that lead in a straight line, as the house bots likely do, miss a gravity curve | `m_hop`, `m_both` |
| **Backpedal** | `away` term in the strafe, facing the enemy | Keep; never turn our back to run unless out of sight | A rear hit costs 1.5× | — |
| **Peek** | Duck to cover only within 10 m when a laser charges | Duck within 30 m (`s_duck30`), and peek out right after their beam fires (1.65 s cooldown) | A laser is hitscan, so a visible charge can't be dodged by moving, only blocked | `s_duck30` now; peek is next |
| **Jet to a roof** | `HOLD_ROOF` tested: no gain, late answers | Only as an escape when hunted by two or more and a roof is within 10 m | Hunters must climb, and the climb uses their energy | later |
| **Silent walk** | Quiet mode on some travel | Walk slowly when hiding and no enemy has seen us in 5 s | Steps carry sound, so slow walking hides our bearing | later |

## Weapon matchups (what they hold, how we exploit it)

| Enemy holds | Its weakness | Our play |
|---|---|---|
| **Gun only** | 12-round magazine, then a 2.4 s reload; needs to lead; 45 per hit | Strafe or hop to make its lead miss. Push or fire a full laser during its reload: our `hit` events stop, and 12 shots take 2.9 s |
| **Laser** | Charging is visible (`charging: true`, plus a sound); half speed while charging; 1.65 s cooldown after firing | Break line of sight while it charges. Peek and punish during the cooldown. **Lightning shorts it**: no charge for 2 s. Close to under 45 m if we hold lightning |
| **Lightning** | 45 m range, 30° cone, 3 energy per shot | Stay beyond 70 m (`_range_pref` does this). A mortar throws it out of range and drains its energy. Never fight it at close range with only a laser |
| **Mortar** | Shell at 72 m/s takes 1.5–3 s; 50% self-splash up close; +60% laser cook-off on its holder | Keep moving (`DODGE` on). Close to under 20 m, where it hurts itself. A full laser does 504 |
| **Laser + lightning** | Lightning is short range; the laser cooldown is long | Fight from 100 m or more. Peek after each beam |

What we pick up: laser first (outranges everything, cook-off), then lightning (counters the laser, which the house bots probably favour). We never pick up a mortar: holding one gives every laser +60% on us.

## Test plan

1. Running now: `s_*` strategy variants vs the squad, 112 matches each.
2. Next: `m_boost`, `m_hop`, `m_both` vs the squad, same seeds, compared with `s_base`.
3. If a variant beats `s_base` by more than 2 SE: build the peek-after-beam and reload-push moves.
