# Online research: mech games

Researcher (online), iteration 1, 2026-11-21. Honest caveat: mech-game tactics online are almost all community forum posts and beginner guides; I found no data and no pro-coach material. The MWO forums and PC Gamer guides blocked or truncated fetches, so most findings below come from search snippets. Treat these as **opinion**, useful mainly because the mechfight rules make several of them exactly true.

## 1. Torso twist: keep your strong side toward the fire, and do it before you're hit

- MWO: twisting spreads incoming fire across components; "twisting in response to being shot is usually too late", so pre-twist toward where fire will come from. (Destructoid MWO tips https://www.destructoid.com/?p=199653; MWO forums https://mwomercs.com/forums/topic/265817-help-with-toros-twisting, snippets)
- BattleTech: turn the most damaged side away from fire while keeping the target in your firing arc. (https://www.magicgameworld.com/battletech-defensive-positioning-builds/, snippet; 403 on fetch)
- Trade-off: twist enough to block one enemy without exposing your rear to another. (MWO forum, snippet)

**For mechfight:** there are no components, only a front/rear split: hits from outside the 180° front arc around our *aim yaw* do ×1.5 (`mech.front_arc_deg`, `mech.rear_mult`) [rule]. Legs and torso are independent, so:
- **Always keep the aim within ±90° of the most dangerous known threat**, even while walking away. Retreating with the torso turned back costs nothing in armor.
- **Pre-twist:** with no visible enemy, keep aim toward the bearing of the most recent `damaged.bearing` / weapon sound, not toward our walking direction.
- **On `damaged.rear: true`**, turn toward `bearing` immediately (180° takes 0.79 s at `turn_rate` 4 rad/s).
- **Two threats:** aim at the bisector if they're ≤ 180° apart (both stay in the front arc); otherwise put the higher-dps one in front and move so the angle between them shrinks (back toward a wall or the zone edge).
- Proxy in `objective.md`: rear-hit share of damage ≤ 20%.

## 2. Peek, shoot, hide, relocate

- MWO: poke cautiously; after you peek once and draw a lot of fire, relocate or stay hidden 20–30 s; never abandon cover. (MWO forum guide "guide to fight a good fight", https://mwomercs.com/forums/topic/252948-guide-to-fight-a-good-fight, snippet; the page was behind a browser check.)

**For mechfight:** regen starts 5 s after the last damage dealt *or* taken, at 45 HP/s (`mech.regen_delay`, `mech.regen_per_s`). So every exchange costs 5 s plus heal time. Rules:
- Poke from a cover edge, fire a burst (gun: up to the 12-round magazine, 2.9 s) or one laser shot, then step back out of LOS. Repeat from a different edge after ≥ 2 s so the enemy's lead and prediction is stale.
- If our HP is < 50% and the enemy isn't nearly dead, break LOS and wait ≥ 5 s + `(max_hp − hp)/45` s. That's 5 + 700/45 ≈ 21 s from 50% to full on base HP. MWO's 20–30 s matches this.
- The `nanites` upgrade (+60% regen, delay −1.5 s) makes poke-and-heal much stronger. Rank it high if we play this way.

## 3. Energy is mobility; keep a reserve

- Armored Core: "Reckless boosting drains the energy reservoir rapidly, depleting it entirely", leaving you on foot and easier to hit; output matters more than capacity. (https://armoredcore6.wiki.fextralife.com/Combat, fetched; https://wccftech.com/armored-core-vi-fires-of-rubicon-tips/amp/, snippet)
- MWO heat: keep your most heat-efficient weapon group active until the fight demands more. (MWO forum guide, snippet)

**For mechfight:** one energy pool feeds boost (17/s), jet (15/s), lightning (3 per shot) and absorbs mortar concussion (−45) [rule]. Regen is 18/s after 0.6 s of not spending: 0 → 100 in 6.2 s. Rules:
- Keep ≥ 35 energy in any fight (≈ 2 s of boost ≈ 39 m of escape, or one concussion) unless finishing a kill.
- Don't boost in the open early: boosting is audible at 90 m (`sound.range.boost`), walking at 40 m, and < 5 m/s is silent.
- Lightning at full rate is 12 energy/s and blocks regen, so a 100-energy pool gives ~8 s of lightning. Pair lightning with walking, not boosting.
- Upgrade picks (`capacitor`, `reactor`, `jets`) matter only if the bot actually uses jets/roofs. Measure energy use in the simulator before ranking them.

## 4. Weapon pairing and range bands

- Armored Core: right arm main weapon, left arm complementary; MWO: don't brawl a mech better equipped for close range. (fextralife; MWO forum guide, snippets)

**For mechfight:** our own DPS arithmetic from `hello.config` (base, no cubes) [rule]:

| Weapon | Burst DPS | Sustained DPS | Band | Notes |
|---|---|---|---|---|
| gun | 45/0.24 = 188 | 540 / (2.88 + 2.4) ≈ 102 | 20–230 m | needs lead; bullets visible and dodgeable at range |
| lightning | 60/0.25 = 240 (+chains) | 240, until energy runs out (~8 s) | ≤ 45 m, 30° cone | no aim lead; shorts lasers |
| laser | 315 per 2.4 s cycle | ≈ 131 | ≤ 280 m | hitscan; telegraphed; +60% on mortar holders |
| mortar | 200 direct + 160 splash per 2.6 s | ≈ 77–138 | ~30–235 m | hard against movers (1.4 s flight at 100 m); great against campers and drop holders |

Pairings for a survival bot: **gun + laser** (both long range, and the laser covers the mortar threat). Swap to lightning only if we expect close fights, e.g. the last two circles (radius 25 m is inside lightning range). Keep the triangle in mind: if the nearest threat holds lightning, stay > 45 m; if it holds a laser, close inside 45 m only with lightning in hand.

## 5. Cover and verticality

- MWO/BattleTech: cover is used to move; high ground for sightlines. (snippets, opinion)
- Armored Core: fights are 3D; boosters for altitude. (fextralife)

**For mechfight:** bullets, shells and lasers hit buildings exactly; trees only block sight, not shots [rule]. So:
- Cover = buildings, bridges, terrain. Trees are concealment only: we can be hit through them by anyone firing at our sound.
- Roofs: reachable with ≈ 60 m of jet per 100 energy. Being high raises our eye above street-level occluders. Getting down is free (fall), getting up costs ~4 s and is audible (`jet` 90 m). Treat roof positions as candidate points in the minimum-risk scorer, with an exposure penalty for open sightlines. Test, don't assume.
- Bigger is worse: each cube makes us 5% bigger with no cap (`cubes.size_per_cube`), so a 10-cube mech is 1.5× the target. Past the 10-cube `stat_cap` cubes add only size. Cubes beyond 10 are a liability, except for upgrade thresholds (15, 21, ...).

## 6. Titanfall, Hawken, Gundam

Nothing citable found in the time spent; skipped.
