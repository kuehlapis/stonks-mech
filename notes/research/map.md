# Map: arena/v2

Evidence: scratch script `map.py` (stdlib; parses `world.json`, unpacks `terrain.i16` as `<h` × 1070·724, bilinear sampling per protocol §11, rasterises prism footprints at 1 m). Runtime 18 s in pure Python, so **the world module must not rasterise like this at startup** (5 s budget); use bounding boxes or a coarse grid. Numbers below are its raw output.

## Bounds and terrain

- `bounds`: x −512.38 … 555.08 (1067.5 m), y −333.09 … 388.64 (721.7 m). Map area 770,418 m². The edge is a wall (§7).
- `terrain.i16`: 1,549,360 bytes = 1070 × 724 × 2 ✔. Grid origin (−513, −334), step 1 m.
- Height range **−9.61 … 49.17 m**, mean 0.43. Origin 0.01 m, zone start center (41.3, −72.8) 1.82 m.
- Histogram (5 m bins): −10…−5: 135,267 cells; −5…0: 251,456; 0…5: 315,042; 5…10: 53,100; ≥10: 19,810.
- **All 19,810 cells above 10 m are within 150 m of the stadium center (−276.3, 128.7)**: the stadium bowl and stands are terrain (field at `stadium.fieldZ` −9.23). Outside the stadium the ground is gentle, −10 … +10 m.
- Cells steeper than `max_slope_deg` 50°: 5,357 of 772,887; **5,292 of them are in the stadium**, only 65 elsewhere. So outside the stadium, slope is almost never a pathing constraint; inside it, the stands are unwalkable walls of terrain.
- Stadium entrances: `stadium.openings` has 2 gate corridors, at (−245, 43) and (−327, 54), both on the south side, 12 m wide. The stadium interior is a 9 m-deep pit with no trees (open region 3 below).

## Prisms

259 prisms (`stats` agrees): **223 building, 27 stadium, 9 bridge**, grouped into 64 named `blocks`. 59 prisms have holes (up to 8).

"Rise" = prism `top` − lowest ground under its ring vertices and centroid = the climb from the street.

| Rise (m) | Prisms (building + stadium) |
|---|---|
| 0–5 | 31 |
| 5–10 | 59 |
| 10–15 | 46 |
| 15–20 | 47 |
| 20–30 | 46 |
| 30–40 | 12 |
| 40–50 | 3 |
| 50–65 | **0** |
| 65–70 | 2 |
| 70–80 | 4 |

- **244 of 250 roofs are within 50 m of the street: reachable with one tank of jet** (100 energy / 15 per s × 10 m/s = 66.7 m theoretical, "about 60 m" in §7). Highest reachable: stadium prism #235 rise 49.5 m, Baker Systems #124 46.5 m, Thompson Library #50 40.5 m.
- **6 are out of reach**, with a clean gap from 49.5 to 67.3 m, so the threshold choice does not matter:
  - Morrill Tower (#68 rise 72.9, 1,254 m²; cap #69 76.3) at (−460, −50)
  - Lincoln Tower (#38 rise 72.7, 1,249 m²; cap #39 76.3) at (−467, −225)
  - Central Service Building #246 (67.4, 17 m²) at (−7, 30) and #94 (67.3, 13 m²) at (−20, 127): chimney-sized stacks, not roofs.
- Building tops span −0.39 … 71.49 m; stadium prisms −0.63 … 44.47.
- A quarter of crates and floor loot spawn on roofs (`crates.roof_fraction`, `loot.floor_roof_fraction` 0.25); nearly all roofs are reachable, so roof loot is fair game. Roof combat is exposed: the roof is visible from every taller roof and from range.

## Bridges

| # | at | base | top | ground under | clearance under | What it is for a mech (height 9 m, +5%/cube) |
|---|---|---|---|---|---|---|
| 0 | (−423, −57) | −1.71 | 0.29 | −4.31 … 0.06 | ≤ 2.6 | low deck, walk **on** it |
| 1 | (−431, −221) | −1.72 | 0.28 | −4.40 … 0.06 | ≤ 2.7 | low deck |
| 2 | (−477, −76) | −1.70 | 0.30 | −5.40 … −0.43 | ≤ 3.7 | low deck |
| 3 | (−480, −190) | −1.88 | 0.12 | −5.03 … −0.56 | ≤ 3.2 | low deck |
| 4 | (−116, −32) | 6.59 | 8.59 | −5.22 … −4.64 | 11.2 … 11.8 | **walk under** (fits up to 4 cubes: 9 × 1.2 = 10.8) |
| 5 | (23, 231) | 9.65 | 11.65 | 0.57 … 0.84 | 8.8 … 9.1 | marginal: a wall at 0 cubes on part of it |
| 6 | (87, 194) | 8.91 | 10.91 | 1.89 … 3.80 | 5.1 … 7.0 | wall (low overhang) |
| 7 | (373, 230) | 14.13 | 16.13 | 4.64 … 5.21 | 8.9 … 9.5 | marginal; wall from 1 cube (9.45 m) |
| 8 | (441, 243) | 14.13 | 16.13 | 4.88 … 5.26 | 8.9 … 9.3 | marginal; wall from 1 cube |

The four low decks are all in the far west (x −423 … −480) and cross the river (`water` river, level −7.51). Treat #5–#8 as walls for pathing; only #4 is a safe underpass. Bridges stop jets from below (§7).

## Footprint vs open ground

- Union of building + stadium footprints (1 m raster): **175,912 m² = 22.8% of the map**. Open ground ≈ 594,500 m² (77%). (Sum of prism areas 176,037 m² for buildings + stadium; stacked prisms barely overlap.)
- Start zone (center (41.3, −72.8), radius 560) covers **717,859 m² = 93.2% of the map**. Only the four corners are outside (corner distances 612, 721, 576, 691 m). The zone center is on open ground (not in a footprint).

## Trees

- **1,560 trees**. Height 4.1 … 49.6 m, mean crown radius 3.94 m, mean crown base 3.84 m. **1,524 have the crown starting below 9 m**, so trees hide mechs from sight (canopy fades vision per `rules.canopyDensity` 0.35, `canopyBlockT` 0.25) but never from shots (§7).
- Fields: `x, y, z, height, crownR, crownBase, trunkR, osm, crownX, crownY`. **`crownX/crownY` is the crown center and is not the trunk `x, y`** (first tree: trunk (520.75, 122.25), crown (519.07, 122.59)). Vision code must test the crown at `crownX/crownY`. protocol.md lists the fields only as "`...`".

## Layout (25 m cells)

`#` ≥ 50% footprint, `+` 15–50%, `.` some footprint, blank = open, `T` open with ≥ 8 trees, `o`/`t` = open and outside the start zone, `Z` = zone start center. North is up; x runs −512 → 555 left to right; the row label is the cell's y.

```
ASCII 43x29, cell 25 m, x from -512, y top = 389
  379 |ooooooooo          T....+.. .  . ...o..ooo.|
  354 |oooooooo         +####++##+##.#+.   .+ooooo|
  329 |ooooooo         +##+++.+##+##+###+#+#+oooo+|
  304 |oooooo          .++++#+.########.+##+  ooo+|
  279 |ootoo           +###### #####.++..+ . #+o+#|
  254 |oooo  .+++++.   ####### ++....+#..#+#+++o##|
  229 |ooo   +.   .+.  +###+#+.+#+###+#+ #+#### ##|
  204 |ooo  ..     .+  #++#+##++#+#.#+#+ #+ ### .o|
  179 |oo   +       +  #+##++#.##+#+#+#+ ++ .++ .+|
  154 |oo   +       +  ++.++## +#+++..+.   ..+# ##|
  129 |o    +       +    .#+.# ...+# ##+  T  .#.##|
  104 |o    +       +   .### #. #### ++++++#.   ++|
   79 |o    +      .+ .++### .. #.++   +#++  ...+#|
   54 |     ++.  ..+. .++###    ++++    ++++####+#|
   29 |      +.  +#+     +##.     +. +#.####.++#.#|
    4 |      +++..+ T        ++  +##.##++++++##+ #|
  -21 | .+     ....    ++##+ ##  ++.        .+.   |
  -46 | ##. T       .+++###. +#                   |
  -71 | ##. T     .+###+#+..ZZ#                   |
  -96 |     T     .####+##.#+#+ ...               |
 -121 |            ####.##+##+.####               |
 -146 |            ######+ +.  ####              .|
 -171 |            +++.. .  ...+#++             ++|
 -196 | +.          ####.#++###               .+##|
 -221 |+##          ####.#++###           +++#####|
 -246 |.#+ .        +###+  +#.#        +#+##.##+++|
 -271 |o   +.       . ##+T ..++.       .+... .    |
 -296 |oo            +####. ###.      T           |
 -321 |oo            .####. +##+ ++.             o|
```

Largest connected open areas (25 m cells with zero footprint):

| Region | Area | x range | y range | Trees | Notes |
|---|---|---|---|---|---|
| West | ~203,000 m² | −500 … 25 | −321 … 379 | 399 | parking lots around the stadium, river, the two dorm towers on the west edge |
| South-east | ~127,500 m² | 25 … 550 | −321 … 104 | 423 | the Oval / Mirror Lake side; the recorded match spawned here (320, −280) |
| Stadium bowl | ~28,750 m² | −350 … −200 | 29 … 229 | 0 | 9 m pit, 2 gates on the south |
| NE corner | ~15,000 m² | 425 … 550 | 154 … 379 | 37 | |

Dense building clusters (cover, short sight lines):
- **North-east campus core**, x −100 … 555, y 30 … 389: almost every cell `#`/`+`. Best area for breaking line of sight and for hiding at the start. Most of it is inside the start zone; its far north-east corner (x > 450, y > 250) is outside.
- **South-central block**, x −200 … 50, y −330 … −20, around and just south-west of the zone start center.
- A thin row in the south-east, x 300 … 555, y −270 … −170.

## What the pathfinder and a hiding strategy should know

1. Outside the stadium, terrain is nearly flat (−10 … +10 m, 65 steep cells); the obstacles are prisms and the map edge. A 2-D occupancy grid of prism footprints (plus the stadium stands as steep terrain) is enough for ground pathing.
2. Any roof is a jet target except the two dorm towers and two chimneys. Climbing costs about 15 energy per 10 m; land with energy to spare (energy regenerates 18/s after 0.6 s).
3. The big open areas (west parking, south-east Oval) are where long-range laser and gun fights happen; the recorded mech died in the south-east open area to a laser + gun mech shooting from 150 m (see `stream.md`). Cross them along tree lines, or not at all.
4. The NE campus core is the densest cover. The zone's later circles are random per match (the recorded match's first next-center was (−42.1, 7.1)), so cover choice must be made per phase.
5. Mirror Lake (level −3.73, 2,825 m²) and the river (−7.51, 7,015 m²) do not slow or block (§11).
6. `barriers` (185 lines) are scenery the server ignores (§11), **although 20 fences carry `"blocks": true` in `world.json`**. protocol.md is the source of truth: ignore them. Worth one observation in a real match to confirm.
