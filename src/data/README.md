# Titles dataset

`titles.json` (1,472 records) and `stats-glossary.json` (77 stat ids) are consumed at
build time by [`src/lib/titles.ts`](../lib/titles.ts), which reshapes them into the
payload served at `/data/titles.json`. Neither file is served to the browser directly.

**Baseline: Aion 2 Taiwan client, 2026-08.** Grades and stat values are exactly the
kind of data a patch moves, so re-verify against a Global pull before trusting numbers.

## Things that are not obvious from the data

- **Stat values are not all the same unit.** If a glossary entry has
  `isPercentBasisPoints: true`, the value is basis points and must be divided by 100
  (`500` → `5%`). Everything else is a flat integer. Never sum across different stats.
- **Two kinds of stats.** `equip_stats` apply only while the title occupies one of the
  three slots (attack / defense / utility). `collection_stats` apply permanently once
  the title is owned and stack across every title owned. All 844 stat-granting titles
  have both; the other 628 have `grants_stats: false` and are purely cosmetic.
- **`description` doubles as the obtain condition** for roughly 90% of titles. The rest
  is flavour text with no acquisition information. There are no structured
  step/count fields, and no drop rates or costs anywhere in the dataset.
- **Faction mirrors.** 526 title names are available to both factions, 225 are
  Elyos-only and 226 Asmodian-only. 93% of the exclusives have an opposite-faction
  counterpart with a different name but identical grade, slot and stats; only 16 have
  no equivalent. `src/lib/titles.ts` merges mirrored records into one row.
- **Grades.** 11 Common, 21 Rare, 31 Legendary, 41 Unique, 51 Mythic, 71 Special. The
  game only uses four colours (white / green / blue / gold), so Mythic and Special
  share Unique's gold and are told apart by label.
- Some titles reference content that will not exist at Global launch (later seasons,
  level-50 zones). There is no "available at launch" flag.

## daevanion.json

**Source: Aion 2 Global LST client, 2026-09-21.** Regenerate with
`python3 scripts/build-daevanion.py`; `--check` verifies without writing.

**This one is not a raw dump.** The pull carries 45 boards / 5,061 nodes (3.87 MB); this
is a **lossless normalization** of the 40 boards it emits, down to 100 KB. Every emitted
board is rebuilt from this file and compared field-by-field to the raw node records
during the build (everything except `name`, see below), and the build aborts on any
mismatch. `scripts/test_daevanion_math.py` re-checks that independently.

- **5 boards per class, not 8.** Global has Nezekan (Lv 12), Zikel (20), Vaizel (30),
  Triniel (40) and Azphel (45). **Ariel, Marchutan and Yustiel no longer exist**; Azphel
  keeps the game's slot `order: 6`, so orders are sparse. Azphel is bought with
  `battle_crystal`, the other four with `daevanion_crystal` (`costPointType` on each god).
- **Boards are smaller and cheaper.** The four skill boards are no longer 153-node,
  210-point grids: Nezekan, Zikel and Vaizel have **89 nodes / 134 points**, Triniel
  **117 / 168**, Azphel still **153 / 232**. A full set is **802 points per class**
  (was 1,768). `points` is recomputed from the layout at build time, never typed in.
- **Node values were cut, most by half or more.** Common tiles went Attack 5→3,
  Defense 50→30, Critical Hit / Resist 10→5 (HP 100 and MP 50 unchanged). Unique tiles:
  Combat Speed and Cooldown Reduction 2.5%→1.5% (Nezekan), Damage Boost / Tolerance
  5%→1.5% (Zikel), Critical Damage Boost / Tolerance 5%→1.5% and 4 tiles→2 (Vaizel),
  Multi-Hit Chance / Resist 3%→1.5% and 4 tiles→3 (Triniel), PvP Damage Boost /
  Tolerance 2.5%→1.5% (Azphel). The Unique Attack 50 / Defense 500 tiles (Nezekan)
  and Accuracy / Evasion 75 tiles (Zikel) are gone. Azphel's small PvP tiles: PvP
  Attack 5→3, PvP Defense 50→30, PvP Accuracy 10→5, PvP Evasion 10→3; PvP Critical
  Hit / Resist 5 and Status Effect Chance / Resist 1% are unchanged.
- **8 classes, one shared layout per board, plus overlays and patches.** All 8 classes
  share one stat template per god and differ only in which skills their 22 skill nodes
  point at (`overlays`, row-major over the skill nodes) — with one wrinkle: Gladiator
  has four Common stat nodes swapped relative to the other seven classes (a Penetration
  10 tile trades places with a Max MP 50 tile on Zikel, Vaizel and Triniel). Those
  four nodes are `patches[class][god]`, applied on top of the layout by position.
  Azphel has no skill nodes and no patches, so it is identical for every class.
- **Brawler (`fighter`) is deliberately left out.** The pull has its 5 boards, but they
  are byte-identical to the Taiwan 2026-08 boards (153 nodes, 210 points, the old
  node values) and only 5 of its 22 board skills exist in the Global skills DB, so the
  class is a stale carry-over rather than Global data. `EXCLUDE_CLASSES` in the build
  script documents this and re-checks it on every run.
- **⚠ `defensepierce` nodes named "Max HP" / "Max MP".** Ten Common tiles (one per class
  on Zikel, plus Gladiator's Vaizel and Triniel ones) carry `statName: defensepierce`
  (Penetration) 10 but are *named* Max HP or Max MP in the raw data. The structured
  effect is what is stored, so the UI shows Penetration; the name is dropped.
- **Adjacency is the prerequisite graph.** The dump carries no link field; a node is
  buyable when a 4-neighbour is owned. Neighbours are therefore derivable from `r`/`c`
  and are not stored. Every node on every board is reachable from the centre.
- **Dropped because derivable:** node `id` (board id + zero-padded row-major cell
  index), `cost` (from `grade` via `gradeCost`), `resetGold` (flat 500, 0 for start),
  `needLevel` (the board's), `isAutoLearn` (start only) and `icon` (by grade). The
  Global pull has no `neighbors`, `distanceFromStart` or `minPointsToUnlock`; a
  Dijkstra from the centre recomputes the last one.
- **Dropped because absent in the source:** the board-level `resetGold` (76,000 in
  the Taiwan dump) and the skill `maxLevel` (`m`). The Global skills DB has no max
  level field and its per-level tables are incomplete (many actives list only level
  1), so nothing is derived; the UI omits "max level" when the field is missing.
- **⚠ Node names are dropped deliberately.** They are inconsistent in the dump: the
  same stat id is named two ways depending on the node (`fixingdamage` is "Attack" on
  442 nodes but "Attack Bonus" on 2; `defense` likewise), and the `defensepierce` tiles
  above are named after a different stat entirely. The UI renders from the glossary
  label and the skill index instead, which are internally consistent.
- **Skill nodes always grant +1 level.** Actives (Legendary, 3 pts) appear once per skill
  board; passives (Rare, 2 pts) twice on exactly one of Nezekan/Zikel and once on
  Vaizel and Triniel, so every skill reaches +4 across the four boards.
- Skill icons live in `public/skills/<class>/<slug>.webp`, where `slug` is stored on each
  skill (lower-case, apostrophes dropped, other punctuation to `_`) so the client never
  reimplements the slug rules. Every emitted skill has its icon.
- **Not in this dump:** crystal acquisition rates (so a points budget is user input), and
  any full-board completion bonus.

## crafting.json

Normalized from the crafting handoff package (3.42 MB → 582 KB). Icons resized 256→64px
into `public/icons/crafting/` (8.3 MB → 1.19 MB).

- **Combo stubs were already removed upstream.** The raw DB returns 2,936 recipes but
  1,028 have `learnType: "combo"` and no inputs — they are proc *results* listed as their
  own recipe. Only the 1,908 real recipes are here.
- **⚠ Faction pairs are not mirrors.** The README that shipped with the package suggests
  deduping by name for a single-faction view; that is wrong. The id's **second digit** is
  the faction (1 = light, 2 = dark), and 944 of 954 pair 1:1 — but within a pair the
  **name differs on 771, the output on 829 and the materials on 539**. A faction toggle
  must filter, never dedupe. Only 63 pairs are byte-identical apart from id.
- **Dropped as derivable:** `craftedBy` / `comboOf` / `usedIn` from `items.json` are just
  indexes over these same recipes and gatherables, rebuilt client-side on load.
- **⚠ Kinah IS in the dataset — as an input, not as `goldCost`.** The package README says
  the amount is unknown; that is only half true. `goldCost` is indeed 0 everywhere, but
  **740 recipes (39%) list an item called "Kina (All)" among their inputs**, from 1 up to
  100,000,000. Four other currencies appear the same way (Abyss Points, and silver/gold/
  platinum Medal of Merit). These are flagged `isCurrency` in the payload so the UI can
  show them as a cost rather than a material. The remaining 1,168 recipes have no kinah
  line at all and are shown as "TBD" — never as free.
  - Watch out: **342 of the 740 list a kinah quantity of exactly 1**, which looks like a
    placeholder rather than a real price. The other 398 range 500,000 to 100,000,000.
- **Mastery maps onto the game's proficiency display, but is encoded.** `masteryGrade` is
  the tier — `beginner` is **Novice**, `intermediate` is **Professional** — and
  `masteryLevel` is one 1–115 bar. The game shows the level *within* the tier, so subtract
  50 for Professional. Verified against the client on three points:

  | Dataset | In-game |
  |---|---|
  | beginner 3 | Novice Lv. 3 |
  | intermediate 55 | Professional Lv. 5 |
  | intermediate 115 | Professional Lv. 65 |

  The split is exact: beginner is only ever 1–50, intermediate only ever 51–115. Novice
  runs to Lv. 50 and Professional to Lv. 65.
- **Mastery gates only 786 recipes (41%).** The other 1,122 have no `masteryLevel` at all,
  and every one is grade 41 or 51. Since grade 41 recipes *can* carry a requirement (True
  Dragon Lord Pauldrons is Professional Lv. 5), being ungated is not simply a function of
  grade — still unexplained. The UI filters by tier rather than a slider, since a slider
  implies a continuum and hides the 59% that are ungated.
- **`craftGauge` is dropped from the payload.** It is per-craft effort (400–1,200) and
  nearly a pure function of grade — 11→400/600, 21→400/700, 31→400/800, 41→400/1,000,
  51→1,200 — so it told the reader nothing the grade chip did not.
- **40 recipes consume the item they produce** (20 items × 2 factions): the transfer/upgrade
  ladder. They share a name with the build-from-scratch recipe, so the UI appends
  **"(Upgrade)"** to tell the pair apart. Detect with `r.in.some(([id]) => id === r.out[0])`.
- **No descriptions anywhere.** Neither recipes nor items carry description or effect
  text, and item stats are in a different dataset — so a recipe detail view can only show
  identity, materials, costs and proc odds.
- **Recipe name always equals its output name** (all 1,908), so never show both.
- **⚠ The dump's profession keys are not the client's names.** Confirmed in-game:
  `tailoring` recipes read **"Armorsmithing Proficiency"** (Orichalcum Breastplate, True
  Dragon Lord Pauldrons) and `jewelcrafting` is **Handicrafting**. `blacksmithing` is
  correct as-is. `alchemy` and `cooking` are **unverified** — they pass through unchanged.
  Mapped in `lib/crafting.ts`; the payload ships display names so nothing downstream needs
  the keys.
- **Grade 51 (Mythic) is orange in game, not gold.** Grades 41 and 51 shared one colour
  until it was checked against the client; they are now `--g-gold` and `--g-mythic`
  respectively, in `src/styles/finder.css` and TitleFinder. Both tokens are theme-tuned —
  the dark orange only reaches 2.9:1 on white, so light mode uses a darker one.
- **Focusing one recipe uses `?r=<id>` rather than a page per recipe.** Generating all
  1,908 as Starlight pages was tried and measured: ~37 KB each, taking dist from 5.6 MB to
  81 MB and the build from 3.3 s to 13.6 s, and they had to be marked `pagefind: false` or
  they swamped site search. The query-parameter view costs nothing and is still linkable.
- **35 of the unsourced items turned out to be vendor stock**, confirmed in-game and
  recorded in `vendor-prices.json` — the suspicion about the "(Bound)" consumables was
  right. Those now show as **buy** with the actual kinah cost. The remaining unknowns are
  labelled **buy/drop**, deliberately vague: the dump has no vendor listings *or* drop
  tables, so either is possible.
- **`vendor-prices.json` is the only source for those prices.** It is hand-recorded from
  the in-game shop, not derived from the dump, so nothing regenerates it — edit it by hand
  and keep the item ids stable.
- **22 recipes are excluded at build time.** They consume *Gear Change Voucher: Bargott
  (Bound)* and are gear-conversion entries rather than crafts (all grade 51, 11 per
  faction). Excluded in `lib/crafting.ts`, so faction counts read 943 rather than 954. The
  records stay in `crafting.json`.
- **124 items are `unsourced`, and that is structural, not a gap** — currencies, boss and
  dungeon drops, vendor items. The recipe DB carries no drop tables or vendor
  listings. Expanding every recipe to its leaves lands on unsourced items 7,706 times vs
  2,254 on gatherables, so "obtained from content" is a first-class answer, not an error.
- **Guard recursion:** 40 recipes are in-place upgrades (output id also appears as an
  input) and 20 items sit in a craft cycle. Track visited per path, not globally. Craft
  depth is shallow though — at most 4.
- Item **stats** are not here, only crafting identity.
