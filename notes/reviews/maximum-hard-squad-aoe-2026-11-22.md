# Critic review: maximum-hard squad / AOE model

Critic, 2026-11-22. Scope: `notes/ideas/maximum-hard-squad-2026-11-22.md`,
`protocol.md`, live config findings in `notes/research/config.md`,
`hello.config`/`notes/research/hello.json`, and existing house/squad evidence.
No code was edited and no match batch or simulator run was launched.

## Verdict

The document is **not a protocol-derived “maximum hard” model**. It can be a
bounded simulator specification for one side of a 15-house-bot track page,
but several values are guesses, user/track rules, or assumptions that
conflict with what an individual mech is permitted to observe. It also
omits several mechanics needed to make the AOE behavior exact.

Promote no arm or tier schedule from this document alone. Before
implementation, use it only as an assumption ledger and fix the blocking
findings below.

## Ranked findings

### H1 — 30 s shared memory and 3 s projection are not protocol vision

Protocol §8 gives individual memory of 5 s (`vision.memory_s`) and says the
tracked position remains real/current while out of view. The proposal keeps
a shared entry for 30 s and linearly projects it for up to 3 s. Its 30 s
entry is 6× individual memory, and continued projection can turn stale
history into a current-wall/target position after LOS loss. This is extra
information and can overstate the squad's pursuit.

**Required correction:** remove 30 s shared pursuit and 3 s interpolation.
Share only observations made in the last 5 s, while all goals remain visible
or current-memory targets under the live `vision.memory_s`. Do not share
behind-wall state or a target whose only evidence is an unobserved beam or
damage bearing. Track-page shared vision may merge observations, but it must
not expand any member's personal 5 s memory or LOS.

### H2 — A 30 s “stale target” can never be used to classify real contact

The proposal calls 30 s a valid table window and bucket pursuer memory from
0–30 s. Protocol has no 30 s mech-memory field. A 30 s bucket is therefore
not a per-mech rule claim; it is either a house-model aggregate registry or
an invalid stale memory implementation.

**Required correction:** use live observed age and live
`vision.memory_s`; add no aggregate 30 s bucket. If the track page itself
authorizes a shared registry, label that registry as an external match rule,
not as protocol vision.

### H3 — Shared damage-bearing guesses create pseudo-positions

The proposal says a gun-hit event may post a bearing guess, and the
documented implementation gives a guessed point 80 m along that bearing.
Protocol emits a bearing toward the source, but does not say that the source
has a known 2-D position. An 80 m synthetic position can place the house
squad behind cover or in a false room and is not LOS observation.

**Required correction:** damage bearing may update retaliation/aim direction
only. It may not create a shared target position or replace missing LOS.
Store a retaliating state and expiry of no more than the live memory window;
the target may not be used for shared registry pursuit while position is
unknown.

### H4 — Exact hard/expert aim and tier schedules are unsupported guesses

`4 easy / 4 medium / 4 hard / 3 expert`, the exact aim/noise/lead/reaction
table, and the AR(1) formula are not protocol values. The track page supplies
proportions, not those aim constants. The recorded n=1 opponent is evidence
for some engine behavior, but no measured tier identity and no squad evidence.

The stated 0.73× steady-state claim also means the AR(1) formula does not
implement the listed `noise` exactly. It is a different aim distribution
unless the “tier noise” field is calibrated intentionally.

**Required correction:** mark every tier number and formula as a simulator
hypothesis. Define a table of at least easy/medium/hard/expert only after
evidence, and state explicitly whether its table value is steady-state sigma
or per-tick sigma. Do not call the schedule exact or protocol-derived.

### H5 — Hunter pressure schedule and retaliation are exact only in the sim

The exact 1 + squad-deaths + time additions, at 150/240/300 s, and 30 s
retaliation are not protocol quantities. The proposal itself says the
schedule is a guess. The house-bots track text means one early hunter, more
as candidates are removed, all late, but it does not give these thresholds.
A 30 s answer cannot claim a 31 s evidence lower bound: n=1 FFA showed
31 s only that a contact persisted; it did not establish a retaliation timer.

**Required correction:** treat this as a sensitivity matrix, not a fixed
maximum-hard schedule. The 150/240/300 thresholds and 30/31 s timers require
separate labels and paired sensitivity runs.

### H6 — “Never fight each other” requires engine-level AOE exclusions

Shared target selection is insufficient for friendly fire. Protocol mortar
splash and lightning can affect nearby mechs, and no protocol-wide team
immunity is specified. The proposal does not say whether target exclusion
also applies to lightning chains, mortar blast falloff, concussion, and the
chain nearest-target list.

**Required correction:** if the track match rule says squad members never fight
each other, encode that rule explicitly for every weapon:
candidate/other squad slots are excluded from lightning primary and chain
targets, mortar aim and splash targets, and no friendly kill/assist credit.
A protocol-level “never fight” rule cannot be inferred from target selection
alone.

### H7 — Mortar AOE behavior is incomplete and cannot be exact

The proposal names the mortar in comparisons but never specifies the launch
arc, direct/splash test, 50% self-splash, 7 m config falloff, wall blocking,
concussion, knock, or energy-drain fraction. It also proposes no minimum
range/firing discipline. Protocol states: 72 m/s, 22 m/s², 200 direct,
160 splash to 30% at 7 m, 50% own splash, and concussion.

**Required correction:** specify the trajectory solver, wall-block rule,
direct/splash/concussion falloff, and self damage. Add firing discipline
that does not intentionally stand inside its own blast. Read all values from
live config; do not hard-code 72/22/200/160/7/50%.

### H8 — Lightning description is close, but no-target fire is omitted

Protocol lightning has a live `range`, `cone_deg`, LOS, nearest-target
selection, up to 2 chains within 14 m at 0.7 falloff, and 3 energy per shot.
It also fires with no target and costs energy. The proposal does not state
no-target/no-LOS behavior and says only “if ... currently holds it.”

**Required correction:** use live config for range/cone/cooldown/energy/chain
fields. Compute primary target as nearest mech/NPC/crate in the cone with
LOS, excluding squad members if “never fight” is a match rule. Chains may go
to 2 more targets only within 14 m. Fire only at the live cooldown and pay
the energy cost even on no target.

### H9 — Laser description is incomplete

Laser is chargeable to 0.75 s, damage scales 35%→315, charge is visible,
charging halves move speed, and full-charge/long-hold behavior is exact.
The proposal says to hold for clear LOS and release at full charge, but
does not give short-charge/min-charge, cooldown, 280 m range, or LOS and
charging dodge risk.

**Required correction:** implement from live config: 0.15 s min charge,
0.75 s full charge, 2 s over-charge, 1.65 s cooldown, 280 m range,
half-speed charging, and visible charge/laser sound.

### M1 — NPC/drone “home” assumption is unsupported

Protocol drones have a true home/wander leash of 30 m and a random current
position. The proposal's “first sight position = home” is false: the first
sight can be anywhere inside 30 m of a hidden home. No home position is
present in `obs`. A squad may learn a first sight only as a drone position,
not its home.

**Required correction:** store observed drone positions for avoidance/farm
decisions, not “homes.” Farm only while in zone and within actual live aggro/
deaggro/leash distances. A 50 m avoidance radius can reject valid goals and
does not itself correspond to the 45 m aggro or 60 m chase-leash rule.

### M2 — “Weak laser/crate/NPC preference” is an invented tier policy

NPC and crate farming are not tier rules in protocol. Medium/hard/expert
farm behavior is a house-model guess. It can be plausible, but it must not
be called exact tier behavior.

**Required correction:** use tier policy only as a tunable. Keep farming
tighter than 50 m where the proposal is most speculative and disable it
during hunting or zone escape. Preserve NPC/crate/drop attribution.

### M3 — Zone behavior contains config and engine assumptions

The protocol supplies live phase times/radii/DPS and the last shrink ends at
415 s by default. The model's fixed 150/240/300/415 s, 25 m, 15 m, 10 s
warnings and 60/80/100 m defender arm can be wrong if config changes. The
`next_center` and `next_radius` fields should determine movement; clamping
only by a 15 m margin is one policy, not a protocol rule.

**Required correction:** read every radius/time/dps/defender value from live
config or explicitly define it as a simulator-only tuning value. Use
`shrink_start/end`, live radii and live zone DPS. No pre-415 squad death is
a match-rule gate, not a protocol prediction.

### M4 — Jump and jet-hop thresholds are not exact evidence

Protocol permits jump and jet, but it does not specify a fixed 0.3 s stuck
trigger, 0.5 s grounded jump, 3 s goal discard, 4 s side flip, or 0.3–0.6 s
juke cadence. The n=1 observation supports some boost/jet/strafe but does not
support exact reversal or stuck thresholds.

**Required correction:** make these tunables, cap them against live energy/
accel/jet config, and prevent zone/LOS logic from issuing contradictory
goals.

### M5 — Upgrade fixed order may be mechanically incomplete

The fixed order is possible but protocol upgrades are offered by currently
held weapon and available stacks. Plating/armor/laser/gun choices depend on
live offers and stats. The proposal does not state offer expiry or timeout
choice.

**Required correction:** select only offered choices, apply timeout behavior,
and use live upgrade IDs/stacks. Treat the fixed order as a default preference
only; it is not protocol-mandated.

## Smallest defensible model

A valid concentrated simulator revision should contain only:

1. 15 members, 4/4/4/3 tiers, each member with normal protocol vision.
2. Merge only real observations seen by squad members; do not merge LOS,
   post 5 s memory, or create positions from bearings.
3. No friendly target damage or squad attribution for every AOE and hit
   weapon, if the track match rule requires this.
4. Exact weapon mechanics from live config, including mortar arc/splash/
   concussion and lightning target/chain/no-target behavior.
5. Zone immunity as an explicit user/track match override, never as default
   protocol behavior.
6. NPCs use live aggro/leash and observed positions, not inferred homes.
7. Tier aim, hunter schedule, pressure range and mobility thresholds are
   separate labeled hypotheses. Test 60/80/100 only after vision and AOE
   validity are fixed.

## Evidence and acceptance

- `protocol.md §7`: exact weapon mechanics and self-splash/concussion.
- `protocol.md §8`: 120°/200 m/45 m vision, 5 s memory, sound/beam rules.
- `protocol.md §9`: live zone phases and 415 s default final shrink.
- `protocol.md §11`: buildings/terrain/line of sight and map assumptions.
- `notes/research/house-bots.md`: n=1 recorded bot; no squad or tier evidence.
- `sim/bots/squad.py`: existing 4/4/4/3 guess table and shared-vision
  implementation.

Blocking gate: do not claim “maximum-hard” or run a pressure/score arm until
H1–H9 are corrected or explicitly relabeled as simulator-only match overrides.
