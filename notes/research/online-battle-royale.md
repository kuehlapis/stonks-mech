# Online research: battle royale strategy

Researcher (online), iteration 1, 2026-11-21. Sources are pro guides, team-org articles and data studies of PUBG, Fortnite, Apex and Warzone. Most BR "strategy" online is opinion; I mark each finding with its evidence level. Numbers in "For mechfight" come from `hello.config` (see `notes/research/config.md`) or are my own arithmetic on them.

Evidence levels: **[data]** measured or statistical; **[pro]** a named pro or a pro-org coaching article; **[guide]** community guide, unclear author; **[rule]** follows from mechfight rules, not from a source.

## 1. Placement beats kills, so fight only when you must

- Fortnite: "Placement will consist of almost all the best team's points throughout a tournament, as fighting is only done when necessary or advantageous." [pro] (Dignitas, https://dignitas.gg/articles/how-to-improve-your-rotations-and-start-placing-higher, search snippet). Same point for solo endgames: kill points should rank below placement [guide] (https://thegamehaus.com/esports/fortnite-maximizing-points-in-competitive-modes/2019/03/09/, snippet).
- Apex ranked: a go/no-go check ("if three or more of position, equipment, time-to-zone don't favor you, don't fight") [guide] (https://guildorder.com/ja/games/apex/guides/ranked-split-mindset, snippet; templated site, low trust).
- Fortnite ranked: rotating early lets you skip 3–4 fights by mid-game, so you reach endgame with more shield [guide] (https://tapin.gg/blogs/fortnite-ranked-tips-2026-92457120-6403-11f1-9c5b-c57b121fff33, snippet).

**For mechfight:** score is `16 − place` and kills are worth 0 directly [rule]. A fight is worth taking only if (a) we expect to win it with HP to spare, or (b) it blocks a must-have (zone entry, an uncontested drop). Encode a go/no-go check in Brain: fight if at least 2 of {our HP ≥ 60% of `max_hp`, our weapon beats theirs in the triangle or theirs is a gun, we have cover or they're facing away, we're inside `zone.next_radius`} hold, and no third mech is tracked within 160 m. Otherwise disengage and break line of sight.

## 2. Rotate early, along the quiet side ("deadside")

- Fortnite (Dignitas): players are pushed into the same side of each new zone; the already-safe uncrowded side is the "deadside" and is the low-pressure route. "Because the majority of players will be moving directly into the zone, the edge will likely be completely uncontested." Rotate early so you aren't held up. [pro] (https://dignitas.gg/articles/everything-you-need-to-know-about-positioning-and-rotation-in-fortnite, fetched).
- PUBG pro Ziphon (Dignitas): start planning the next rotation "within the first minute that the circle dropped"; crossing open ground late is the riskiest move; looting inside the circle beats long runs. [pro] (https://dignitas.gg/articles/professional-pubg-movement-positioning-and-rotations-with-ziphon, fetched).
- The worst outcome is "leaving late and slow"; early circles are big and forgiving, late ones aren't. [guide] (https://gamertagmythras.com/blog/pubg-battlegrounds/pubg-blue-zone-rotation-guide, snippet).

**For mechfight:** `obs.zone` always gives `next_center`, `next_radius`, `shrink_start`, `shrink_end`, so there is no guessing for the *next* circle [rule]. Rule: be inside the next circle by `shrink_start` with margin `m = 0.2 × next_radius` (at least 10 m), and start moving when `dist_to_target / walk_speed(11.7) × 1.5 + 5 s ≥ shrink_start − t` (1.5 = path detour factor; measure it on the map). Path to the point of the next circle nearest to us *offset away from tracked enemies* (deadside), not to `next_center`: everyone else (including the example bot) walks to the center.

## 3. Edge versus center

- PUBG pro: center is preferred *if* you can hold it (full squad, good loot); edge is "a solid second option, especially for the first few circles". [pro] (Ziphon, fetched).
- Guides: solo or outgunned → favor the edge; center minimizes rotation risk but is crowded; dead center isn't safe because the next circle can make it an edge. [guide] (gamertagmythras, guildorder, snippets).
- Warzone: edge play with "your back to the gas" so nobody flanks from behind, but the gas moves faster than it looks. [guide] (https://steelseries.com/en-tw/blog/call-duty-warzone-tips-205, https://guildorder.com/games/cod/guides/warzone-squad-tactics, snippets).

**For mechfight:** we are a solo in a 16-way FFA, so default to **inner edge**: stay 0.6–0.85 × `zone.next_radius` from `next_center` on the side with the fewest tracked enemies, with the zone wall behind us. The wall covers our rear (rear hits ×1.5 `mech.rear_mult`), and anyone coming from behind takes zone damage. Switch to center-ward in the last two phases (radius 25 → 0), when the circle is smaller than gun range and edge offers nothing. Test edge-vs-center as a parameter in the simulator; don't trust the guides on this.

## 4. Early zone damage is cheap; late zone damage is fatal

- Fortnite (Dignitas): you "shouldn't be afraid" to stay in the storm to finish a rotation. [pro]

**For mechfight:** phase-1 dps is 20 HP/s (`zone.phases[0].dps`): 10 s outside costs 200 HP, about 4.4 s of regen at 45 HP/s [rule]. But zone damage resets the 5 s regen timer and blocks regen (§7 protocol). So early on, cutting through the zone to avoid a fight is fine; from phase 4 (100 HP/s) on it isn't. Rule for Survival: allowed seconds outside = `0.15 × hp / dps`, and 0 when `dps ≥ 100`.

## 5. Third parties: avoid being one of the two, be the third

- Third parties hit fights in busy areas; finish fights fast and move; "the player who loots the box for a full minute standing in the open is the player who dies to the third party". [guide] (https://gamertagmythras.com/blog/pubg-battlegrounds/pubg-third-party-guide, snippet; Apex forum https://forums.ea.com/discussions/apex-legends-general-discussion-en/how-to-avoid-defeat-and-execute-third-party-attacks/5468156, opinion).
- Arrive fast after a fight ends, before the winner heals. [guide/opinion]

**For mechfight:** every gun shot is audible at 320 m, mortar at 420 m, death at 600 m, with bearing ±7° (`sound.bearing_noise_deg`) [rule]. So fights are public. Rules:
- After we win or break a fight, leave the spot within 2 s and break LOS before healing (regen needs 5 s of no damage either way).
- Track "fight spots": cluster sounds of weapon kinds from ≥ 2 distinct bearings/kinds within 10 s. Avoid moving toward one unless we're ≥ 70% HP *and* a `death` sound came from it (the survivor is likely hurt). Then approach to 100–150 m (outside lightning 45 m), and engage only if they're below 50% HP (`show_enemy_hp` is true, so we see their `hp`).

## 6. Hide and play for placement ("ratting"), and its counters

- Apex: ratting earns placement "by letting other teams fight things out and eliminate each other while you get a better placement" (search summary of a dotesports/Apex piece). Fortnite: build a small elim lead, then ratting is viable [guide]. Avoid sprinting because enemies hear you [guide].
- Counters: nothing is fully safe; final circles force everyone out.

**For mechfight:** moving below 5 m/s (`sound.step_speed`) is silent [rule], and tracked enemies are dropped after 5 s out of view (`vision.memory_s`). A hiding bot sits in cover inside the next circle, aimed at the most likely approach, moving at ≤ 0.4 move length. This is probably the single cheapest strategy for M1–M2 (mean 7–8). It fails in the last two phases, where the circle is 25 m and then 0 m. Its counter, which we also need for the endgame: mortar (arcs over cover, 7 m splash, `weapons.mortar.splash_radius`) and "fire into trees at a sound" (trees don't stop shots).

## 7. Endgame is a phase, not a moment

- "The single biggest endgame mistake is treating it as a moment instead of a phase" [guide] (gamertagmythras Fortnite endgame, snippet). PUBG pro solo endgame: get low and concealed near the center [pro] (Ziphon). Moving zones force spending resources; plan to [pro] (Dignitas Fortnite).

**For mechfight:** the last circle reaches radius 0 at 415 s (sum of `hold_s + shrink_s`, see `config.md`), and the match lasts until 480 s. So after 6:55 every survivor is outside the zone at 260 HP/s with no regen, and **the last mech alive is the one with the most HP at collapse** if no one kills anyone (armor doesn't reduce zone damage) [rule; verify in the simulator]. 1400 HP lasts 5.4 s; 10 cubes (+40%) and 3× `plating` (×1.52) give about 2980 HP = 11.5 s. Plan from phase 4 (≈ 295 s) on: full HP via regen or a drop, max HP via cubes and `plating`, and no trades that cost HP unless they kill.

## 8. Loot fast, then move; don't run across the map for loot

- Ziphon: looting inside the circle is usually worth more than long runs. Fortnite (Dignitas): loot and farm quickly, then move early. [pro]
- Data: in the Kaggle PUBG placement dataset, `walkDistance` is the top predictor of `winPlacePerc` (r ≈ 0.81 in one write-up); `boosts` and `weaponsAcquired` also rank high. [data] (https://core.ac.uk/download/401551796.pdf, https://sebmerkt.github.io/2019/02/08/First_Kaggle.html, snippets). **Caution:** this is correlation; players who live longer walk more. It does not mean "walk more".

**For mechfight:** loot only what is on the way to the next circle or within ~60 m of our path, before `shrink_start − travel_time`. Value per second, roughly: crate 300 HP (≈ 7 gun hits at 45) gives 1 cube and a 50% weapon; NPC 350 HP gives 2 cubes but shoots back (25 dmg, 90 m/s bullets, slow and dodgeable at > 60 m). Mortar/laser/lightning pickups (40 floor spawns) are free if no enemy is near.

## 9. Supply drops are bait

- Care packages in PUBG/Fortnite are known third-party magnets (folk wisdom, no source I'd cite as evidence).

**For mechfight:** drops are called at 70/140/210 s, land 25 s later, and **every mech sees them** in `obs.drops` and hears the landing at 600 m [rule]. Capturing needs 4 s alone in an 8 m ring: a stationary-ish target that mortars and lasers punish. Rule: go for a drop only if no other mech is tracked or heard (`step`/`boost`/weapon sounds) within 120 m of it in the last 5 s, and we can reach it within ~10 s of landing. While capturing, keep moving inside the ring (16 m across) and face the most likely threat bearing. If a rival is capturing, we can freeze their clock by stepping in, or mortar them from 100–200 m.

## 10. High ground

- Fortnite (Dignitas): in stacked lobbies, rotate over high elevation to deal long-range damage without overcommitting. PUBG: use high ground and treelines. [pro]

**For mechfight:** 100 energy climbs about 60 m (most roofs, not the 70 m towers) [rule]. A roof gives wide LOS over street-level buildings and sight past the 45 m proximity bubble of anyone below; ground bots without map logic (the example bot) can't follow. Costs: on a roof we're visible from far away, and a mortar shell can land on a roof. Test roof-camping inside the next circle as a Survival option in the simulator; the guides only support it as opinion.

## Sources I could not use

- Apex ALGS placement tables disagree between sources (guildorder vs expertbeacon); I didn't rely on them.
- Chen & Liu, "Strategy in Battle Royale Games" (https://aochen.netlify.app/uploads/Strategy_Battle_Royale.pdf): redirects to a homepage; not read.
- No source gives statistical evidence for edge vs center. Treat section 3 as opinion to test.
