# Researcher (online): journal

Owns: `notes/research/online-*.md`. Rules: `CLAUDE.md` (Agent journals). Goal: `objective.md`.

## Current task

Iteration 1 brief from the moderator: research online (BR strategy, bot competitions, game AI methods for 50 ms Python, mech games, FFA game theory) and translate it into mechfight rules with config names and numbers. Write `online-battle-royale.md`, `online-bot-competitions.md`, `online-game-ai.md`, `online-mech-games.md`, and a ranked top-15 `online-recommendations.md`. Status: **done** (2026-11-21).

## Plan

1. Read the rules (`breakdown.md`, `protocol.md` §4, §7–§10, `notes/research/config.md`). Done.
2. Robocode first (closest analogue): targeting, movement, radar, melee. Done.
3. Competition post-mortems: Halite, CodinGame, Battlecode, StarCraft AI. Done.
4. BR pro guides and data: PUBG, Fortnite, Apex, Warzone, Kaggle PUBG. Done.
5. Game AI methods: utility/FSM/GOAP, Killzone position evaluation, influence maps, intercept math, JPS and flow fields. Done.
6. Mech games: MWO, BattleTech, Armored Core. Done (weak sources).
7. Ranked recommendations with effect, effort, module and simulator measure. Done.

Next run: whatever the moderator assigns. Candidates are in the table below.

## Areas of improvement

| What | Why (effect on score or proxy) | How to be better | Status |
|---|---|---|---|
| No outside knowledge used yet | Proven tactics from other games and contests can skip trial and error | Survey and translate them to mechfight rules | done (5 files, iteration 1) |
| Effect estimates are reasoned, not measured | The ranking could be wrong; ±0.7 noise per submission | Re-rank after the Tester's simulator reports mean place per feature | open |
| Edge vs center has no evidence, only opinion | Positioning drives mid-game survival (rec #6) | Ask the Tester for a sweep of the radius fraction 0.3–0.9 in the simulator | open |
| Final-collapse HP tiebreak is derived from rules, not checked | If true, `plating` and cubes decide wins (rec #7) | Ask the Researcher (offline) or Tester to confirm zone dps at radius 0 from 415 s to 480 s, and how same-tick deaths share a place | open |
| Built-in bot behavior unknown | Which guns and movements to counter (linear lead vs GF; dodging value) | Analyze enemy `vel` straightness and aim in `check/stream.jsonl.gz` (offline Researcher's area) | open |
| Squad-survival rules rest on search snippets only | R1–R6 effects are guesses | Fetch one game-AI pursuit-evasion source; get Tester A/B of R1 (funnel) and R3 (zero-LOS + silence) | open |
| Body-shield rule (R2) depends on unknown friendly-fire rule | Wasted build if shots pass through mechs | Checked `protocol.md:306,317`: no rule, dropped; kept lightning chain pick | done |
| Several primary sources unreadable (Game AI Pro PDFs, Killzone slides, AIIDE reports, MWO forums) | Some findings rest on search snippets | Retry with another mirror, or extract the PDFs with the scratch extractor (worked for Battlecode, not for font-encoded PDFs) | open, low priority |

## Lessons

- RoboWiki pages fetch cleanly and are the best evidence-per-minute for this game; BR guides are mostly opinion or templated sites (guildorder appears in 9 languages with the same text). Prefer team-org pieces (Dignitas) and named-pro interviews.
- WebFetch can't read many PDFs (compressed or font-encoded). A 15-line zlib + `Tj/TJ` extractor in the scratchpad (`scratchpad/scripts/pdftxt.py`, run with `python -I`) recovered the Battlecode PDF text but not Game AI Pro (custom font encoding). Don't sink more time into image-only slides.
- The most valuable findings came from doing arithmetic on `hello.config` after reading a source (bullet flight vs mech radius, regen time, final-collapse HP), not from the sources themselves. Next time, compute the key numbers before searching, so searches target the open questions.
- Windows Python prints cp1252; with `-I` the `PYTHONIOENCODING` variable is ignored, so write bytes to `sys.stdout.buffer`.

## Log (newest first)

- 2026-11-22, iteration 1, assumptions discussion: appended "Researcher (online)" to `notes/ideas/assumptions-discussion.md`. Findings: tiered bots differ by ReactionTime (≈0.6 s easy to ≈0 s expert, community BotProfile.db copies), which bears on A10, gives a first-shot window; mobile-BR bots move toward gunfire sound (fan guide, against A12); horde AI staggers attackers (fits A7); no source on bots and zone damage (A4). Evidence: 3 searches, 1 fetch refused (Valve wiki 403). Next: offline Researcher measures per-bot reaction delay and sound-turning in the stream.

- 2026-11-22, iteration 1 (squad era), rev 2 after moderator feedback: fetched arXiv 1110.4838 (3 pursuers suffice with full info, so evasion only works undetected), plus horde-AI attack-token/Kung-Fu circle and LLM-BR sources (snippets). R2 settled from `protocol.md:306,317`: general body shield dropped (no mech-blocks-shot rule), narrowed to lightning chain pick `b_chain`. R3/R6 rewritten as deltas `REGEN_HIDE`, `BURN_QUIET`; loot-silence and R5 dropped (already built). R1 costed: 8 wall cells x 5 hunters = 40 los (= LOS_CAP) at 0.04 ms = 1.6 ms, cached 1 s, no path search (the cause of the 50-62 ms hold search). Variants: s_funnel, b_regen_hide, s_zone_lean, b_burn_quiet, b_chain. Next: Tester A/B in that order.

- 2026-11-22, iteration 1 (squad era): brief = survive 15 coordinated hunters with shared vision. Wrote `notes/research/online-squad-survival.md`: R1 funnel to spots with 1–2 LOS shooters, R3 zero-LOS break plus 5 s silence, R4 pre-position inside next circle and fight hunters still outside, R5 lowest time-to-kill target, R2 body-shield (needs a friendly-fire fact check), R6 loot silence late. Evidence: 2 web searches (snippets, no fetches). Effects unmeasured. Next: Researcher (offline) confirms whether shots stop at the first mech; Tester A/Bs R1 and R3.

- 2026-11-22, iteration 1 (squad era): brief = movement tech and survival when hunted. Wrote `notes/research/online-movement.md`: minimum-risk LOS-count movement, jiggle peek to bait lasers then punish the 1.65 s cooldown, re-peek from a new spot, reversal timing tied to gun flight, pack-edge fighting. Evidence: 2 RoboWiki fetches, 1 search on CS2 peeking. Effects unmeasured. Next: re-rank after the Tester runs `s_minrisk`, `s_jiggle`, `m_flight`.

- 2026-11-21, iteration 1: wrote `notes/research/online-battle-royale.md`, `online-bot-competitions.md`, `online-game-ai.md`, `online-mech-games.md`, `online-recommendations.md`. Evidence: ~30 searches and ~35 fetches. Fetched and read: 11 RoboWiki pages, 2 Dignitas articles, the Halite III post-mortem, 3 reCurse CodinGame post-mortems, Wikipedia (Halite, Truel, Projectile motion), arXiv 2410.04936, Battlecode 2019 PDF (text extracted), AC6 wiki. Failed: AIIDE reports (connection refused), gamedeveloper.com (403), Game AI Pro and Killzone PDFs (unreadable), MWO forums and PMC (browser check), PC Gamer (truncated), magicgameworld (403), Chen & Liu BR paper (redirect). Key derived numbers: gun flight 0.40 s at 100 m vs 4.6 m of walking target movement; dodge on sight only from ≳ 110 m; 50% → full HP in ≈ 21 s hidden; final circle radius 0 at 415 s with the match lasting to 480 s, so HP pool (≤ 2980 with 10 cubes + 3× plating) likely decides passive endgames. Result: top 15 ranked, led by zone discipline, fight selection and the simulator. Next: re-rank once the simulator measures effects; confirm the final-collapse rule.
- 2026-11-21, iteration 1: journal created. Next: start the current task.
