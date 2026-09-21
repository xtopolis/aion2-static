# Titles dataset

`titles.json` (1,494 records) and `stats-glossary.json` (86 stat ids) are consumed at
build time by [`src/lib/titles.ts`](../lib/titles.ts), which reshapes them into the
payload served at `/data/titles.json`. Neither file is served to the browser directly.

**Source: Aion 2 Global LST client, 2026-09-21.** Regenerate with
`scripts/build-titles.py` (reads `/home/claude/aion2-data/raw/titles.json`). Grades and
stat values are exactly the kind of data a patch moves: the 2026-08 Taiwan dump differed
from this pull on 731 records (stat values), 22 grades and 226 slot assignments.

## Things that are not obvious from the data

- **Stat values are not all the same unit.** If a glossary entry has
  `isPercentBasisPoints: true`, the value is basis points and must be divided by 100
  (`500` → `5%`). Everything else is a flat integer. Never sum across different stats.
- **Two kinds of stats.** `equip_stats` apply only while the title occupies one of the
  three slots (attack / defense / utility). `collection_stats` apply permanently once
  the title is owned and stack across every title owned. 994 titles grant stats: 838
  have both kinds, and the 156 ranked "[Season 2]" titles (Abyss, Arena, Ascension
  Trial, Nightmare, Subjugation, Transcendence) have `equip_stats` only. The other 500
  have `grants_stats: false` and are purely cosmetic.
- **`description` doubles as the obtain condition** for roughly 90% of titles. The rest
  is flavour text with no acquisition information. There are no structured
  step/count fields, and no drop rates or costs anywhere in the dataset.
- **Faction mirrors.** 492 title names are available to both factions, 45 are tagged
  `Both` (`race: all`), 225 are Elyos-only and 226 Asmodian-only. 92% of the exclusives
  have an opposite-faction counterpart with a different name but identical grade, slot
  and stats; 34 have no equivalent. `src/lib/titles.ts` merges mirrored records into one
  row (1,023 rows).
- **`is_visible` is not "obtainable".** 760 records are `false`, including 400 that
  grant stats (every ranked season title among them). It is passed through untouched
  and nothing in the UI filters on it.
- **Grades.** 11 Common, 21 Rare, 31 Legendary, 41 Unique, 51 Mythic, 71 Special. The
  game only uses four colours (white / green / blue / gold), so Mythic and Special
  share Unique's gold and are told apart by label.
- Some titles reference content that will not exist at Global launch (later seasons,
  level-50 zones). There is no "available at launch" flag.

## wings.json

Served verbatim at `/data/wings.json` by `src/pages/data/wings.json.ts` and rendered by
`WingFinder.astro`. **Source: Aion 2 Global LST client, 2026-09-21**, 66
raw records → 33 rows; regenerate with `scripts/build-wings.py`.

- **Faction mirrors are merged by name.** Every wing exists once per faction with
  identical grade and stats; the script refuses to run if a pair ever differs.
- **`stats[].base` / `max` are the enchant +0 and +`levelMax` values** from the raw
  `equipStats.enchants` table, percent stats already divided out of basis points. A stat
  that only appears at higher enchant levels has `base: 0`. `levelMax` is 0 when no stat
  moves with enchanting (Lesser Daeva Wings, all 8 cosmetic wings).
- **Not in the payload: `equipStats.mainStats`.** 50 of the 66 raw wings carry a second
  map of 1–4 stats (e.g. Brawler Wings: HP 500, Defense 400, Status Effect Chance 3%,
  Status Effect Resist 3%) whose in-game meaning is unverified, so the table shows enchant
  stats only, as it did for the Taiwan dump.
- The Taiwan dump had 67 wings; 34 of them (27 cosmetic, 7 Unique with stats: Azure Flash,
  Dead Ego, Dramata Nest, Fledgling Arch Daeva, Illusory Echo, Ornate Golden Motif,
  Salvation) are absent from the Global LST data. Their icons remain in
  `public/icons/wings/`.

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

Source: **Aion 2 Global LST client, 2026-09-21**, built by `scripts/build-crafting.py` (2.35 MB raw → 196 KB). Icons are
the 64px set already in `public/icons/crafting/`; the Global pull references 269 of the 522
on disk plus one that is missing (`Icon_Item_Craft_Drop_Draconic_Soul_All_A_u_001a`,
Balaur's Essence, id 600590001 — a new drop material with no icon file yet).

The Taiwan 2026-08 dump had 1,908 recipes; the Global LST has **528** (264 per faction).
Every surviving id existed before; nothing new was added. What went away:

| Removed | Count | What it was |
|---|---|---|
| Grade 51 recipes | 380 | Noble / Horned / Genesis Dragon Lord, Corroded Sovereign's, Lava Heart and every Heroic transfer. No Mythic craft exists now |
| Splendent-for-kinah | 276 | "Splendent X" from X + kinah (500,000 to 60,000,000, plus the kinah=1 placeholder twins). Replaced by material recipes, see below |
| Dragon Lord Core (Bound) variants | 200 | The same gear crafted from a bound core instead of a tier-1 base item |
| Direct crafts above the True/Star tier | 168 | White/Dark, Wise/Ebony, Celestial/Demonic, Obsidian/Crimson from N x tier-1 bases. Only the transfer route remains, and the Celestial and Obsidian tiers are gone entirely |
| kinah=1 placeholder twins of transfers | 152 | |
| Crafting Transfer Stone transfers | 84 | The stone is gone; transfers now consume a tier-1 Artisan's Splendent piece instead |
| Abyss tab | 80 | Guardian / Archon High Commander gear bought with Abyss Points and Medals of Merit (was 190 rows including their grade-51 kin) |
| Other | 40 | Gauntlet (all 16 remaining), Brooch (2), Sharp/Precise Balaur refinements (16), Superior Absorption / Tailwind / Critical Hit scrolls (6) |

- **Combo stubs are back in the raw pull and are dropped at build time.** 570 of the 1,098
  raw rows have `learnType: "combo"` and no inputs: they are proc *results* listed as
  their own recipe (their id's second digit is 3/4 rather than 1/2). 77 of their product
  ids are not produced by any surviving recipe, so they are vestiges of deleted crafts.
- **⚠ Faction pairs are not mirrors.** The id's **second digit** is the faction (1 = light,
  2 = dark), and 254 of 264 pair 1:1 — the 10 unpaired per side are the profession
  advancement items (Novice / Professional Hammer, Fabric, Magnifying Glass, Scale,
  Seasoning; `learnType: "advancement"`, ids differ by more than the faction digit). Within
  a pair the **name differs on 144, the output on 199 and the materials on 132**. A faction
  toggle must filter, never dedupe. Only 44 pairs are byte-identical apart from id.
- **Dropped as derivable:** `craftedBy` / `comboOf` / `usedIn` from `items.json` are just
  indexes over these same recipes and gatherables, rebuilt client-side on load.
- **No currency is listed as an input any more.** `goldCost` is still 0 everywhere, and
  the "Kina (All)" / Abyss Points / Medal of Merit input lines the Taiwan dump carried are
  gone with the recipes that used them. The `isCurrency` flag (5th item tuple slot) is kept
  in the schema and is 0 on all 703 items; the UI shows every kinah cost as "TBD" — never
  as free. `scripts/build-crafting.py` re-flags by `mainCategory: "currency"` should they
  return.
- **Splendent upgrades now cost materials, not kinah.** Each grade-41 tier has a "Splendent
  X" recipe taking 2 to 5 same-tier draconic materials (e.g. Splendent Star Dragon Lord
  Longsword: 11 Fine Thick Balaur Horn + 4 Wrathful Mind, was 1,000,000 kinah; Splendent
  Ebony Dragon Lord Dagger: 2 Artisan's Ultimate Refining Stone + 21 Fine Durable Balaur
  Horn + 7 Wrathful Ego + 2 Radiant Orichalcum Ore + 3 Radiant Odyle, was 10,000,000).
  **⚠ The base item is not listed as an input** (the Taiwan dump did not list it either),
  so the recipe reads as if the Splendent piece were built from those materials alone.
  Treat it as an upgrade of the plain piece.
- **No recipe consumes the item it produces.** The 40 "(Upgrade)" rows were Heroic
  transfers and are gone. The UI's `isUpgrade` detection is kept and simply never fires.
- **The grade-41 ladder per slot is now: direct craft (True/Star, Professional Lv. 5 or
  10) → transfer (White/Dark, Wise/Ebony, ungated) → Splendent (ungated).** 19 slots (9
  weapons, 7 armor, 3 accessories) x 2 factions: 38 direct, 76 transfer, 114 Splendent.
  Transfers consume 1 Artisan's Splendent tier-1 piece plus materials.
- **Material counts came down on the direct crafts.** Star Dragon Lord Longsword: Refining
  Stone 5 → 4, Radiant Orichalcum Ore 12 → 9, Radiant Odyle 7 → 5 (horn 22 and Wrathful
  Mind 10 unchanged). Transfers went slightly **up**: Ebony Dragon Lord Dagger was a
  Transfer Stone + 6 / 41 / 21 Ego / 15 / 9 and is now a tier-1 base + 6 / 41 / 3 Mind
  + 3 Will + 20 Ego / 15 / 9.
- **Refined draconic materials come from Balaur's Essence.** Fine/Enhanced/Tanned Thick,
  Hard and Durable horn/scale/leather each take 2 Balaur's Essence + the tier's hammer /
  hardener / softener; the raw Thick/Hard/Durable Balaur Horn etc. inputs are gone.
- **Mastery maps onto the game's proficiency display, but is encoded.** `masteryGrade` is
  the tier — `beginner` is **Novice**, `intermediate` is **Professional** — and
  `masteryLevel` is one 1–100 bar. The game shows the level *within* the tier, so subtract
  50 for Professional. Verified against the Taiwan client on three points:

  | Dataset | In-game |
  |---|---|
  | beginner 3 | Novice Lv. 3 |
  | intermediate 55 | Professional Lv. 5 |
  | intermediate 115 | Professional Lv. 65 |

  The split is exact: beginner is only ever 1–50, intermediate only ever 51–100 (the
  Taiwan dump went to 115; nothing above Professional Lv. 50 is required now). The five
  Novice cooking recipes dropped 4-5 levels (Curry Meat Stirfry Lv. 5 → 1, Steamed Cypri
  10 → 5, Kukuru Fried Meat 15 → 10).
- **Mastery gates 338 recipes (64%).** The other 190 have no `masteryLevel` at all, and
  every one is a grade-41 transfer or Splendent recipe; every direct craft is gated. The
  UI filters by tier rather than a slider, since a slider implies a continuum and hides
  the 36% that are ungated.
- **`craftGauge` is dropped from the payload.** It is per-craft effort (400–1,000) and a
  near-pure function of grade — 11→400/600, 21→400/700, 31→400/800, 41→1,000 — so it
  told the reader nothing the grade chip did not.
- **No descriptions anywhere.** Neither recipes nor items carry description or effect
  text, and item stats are in a different dataset — so a recipe detail view can only show
  identity, materials, costs and proc odds.
- **Recipe name always equals its output name** (all 528), so never show both.
- **Procs.** 296 recipes carry a proc (20 / 25 / 30%; the old 10% tier is gone). Two
  Status Effect Resist Scroll recipes report a 10% chance with no proc product, and the
  Superior Speed / Courage / Benediction scrolls lost theirs (the proc products no longer
  exist in `items.json`); all are shipped without `cp`/`co`.
- **⚠ The dump's profession keys are not the client's names.** Confirmed in-game:
  `tailoring` recipes read **"Armorsmithing Proficiency"** (Orichalcum Breastplate, True
  Dragon Lord Pauldrons) and `jewelcrafting` is **Handicrafting**. `blacksmithing` is
  correct as-is. `alchemy` and `cooking` are **unverified** — they pass through unchanged.
  Mapped in `lib/crafting.ts`; the payload ships display names so nothing downstream needs
  the keys.
- **Grade 51 (Mythic) is orange in game, not gold.** Grades 41 and 51 shared one colour
  until it was checked against the client; they are now `--g-gold` and `--g-mythic`
  respectively, in `src/styles/finder.css` and TitleFinder. Both tokens are theme-tuned —
  the dark orange only reaches 2.9:1 on white, so light mode uses a darker one. No
  crafting recipe is grade 51 any more; the chip stays for titles.
- **Focusing one recipe uses `?r=<id>` rather than a page per recipe.** Generating all
  recipes as Starlight pages was tried on the 1,908-recipe dump and measured: ~37 KB each,
  taking dist from 5.6 MB to 81 MB and the build from 3.3 s to 13.6 s, and they had to be
  marked `pagefind: false` or they swamped site search. The query-parameter view costs
  nothing and is still linkable.
- **31 of the 50 unsourced items are vendor stock**, confirmed in-game on the Taiwan client
  and recorded in `vendor-prices.json`. Those show as **buy** with the kinah cost. The
  remaining 19 are labelled **buy/drop**, deliberately vague: the dump has no vendor
  listings *or* drop tables, so either is possible. They are the Refining Stones,
  Wrathful Mind / Will / Ego, Balaur's Essence, Lesser (Abyssal) Manastone / Soulstone,
  Spiritstone, Raw Leather, and the raw cooking ingredients.
- **`vendor-prices.json` is the only source for those prices.** It is hand-recorded from
  the in-game shop, not derived from the dump, so nothing regenerates it — edit it by hand
  and keep the item ids stable. 4 of its 36 ids (Absorption Scroll, Elatrite Hammer,
  Ultimate Dragon Leather Softener, Ultimate Dragon Scale Hardener) are no longer used
  by any recipe; they still exist as items and are kept.
- **The Gear Change Voucher exclusion in `lib/crafting.ts` is now a no-op.** The 22
  gear-conversion entries consuming *Gear Change Voucher: Bargott (Bound)* (632510022)
  were grade 51 and are gone; the guard stays so they are excluded again if they return.
  Faction counts read 264 each.
- **50 items are `unsourced`, and that is structural, not a gap** — boss and dungeon drops,
  vendor items. The recipe DB carries no drop tables or vendor listings. Expanding
  every recipe to its leaves lands on unsourced items 1,490 times vs 798 on gatherables
  and 198 on proc-only products (items such as Splendent Orichalcum Longsword that feed
  the next tier but only exist as a 25% proc), so "obtained from content" is a first-class
  answer, not an error.
- **Guard recursion anyway:** no craft cycle exists in this pull (the 20-item cycle was
  the Heroic transfer ladder), but track visited per path regardless. Craft depth is
  shallow — at most 4.
- **Gatherables are unchanged**: all 119 nodes, categories, mastery levels and drop
  tables are identical to the Taiwan dump.
- Item **stats** are not here, only crafting identity.

## key-mats.json

Built by `scripts/build-key-mats.py`, served whole to the Key Mats page through
[`src/lib/key-mats.ts`](../lib/key-mats.ts). 47 roster items, 165 source rows.

**Source: Aion 2 Global LST client, 2026-09-21** for the quest rows
(`/home/claude/aion2-data/raw/quests.json`, 1,313 quests with `questRewardsItems`).
Everything else is hand-curated or frozen:

| Row kind | Where it comes from | Status |
|---|---|---|
| `quest` | Global LST quest pull, joined by exact reward item name | regenerated (Global) |
| `dungeon` | `dungeons.json` (boss cube tables read from screenshots) | **frozen** |
| `activity` "Ordeal" | `dungeons.json` (Ordeal reward ladder) | **frozen** |
| `shop` | `SHOPS` table in the script (Trade Shop screenshots, Sep 2026) | hand-curated |
| `activity` (community) | `ROSTER` table in the script | hand-curated |

- **Frozen rows.** The curated `dungeons.json` (path in `KEYMATS_DUNGEONS`, default
  `/root/aion2/data/curated/dungeons.json`) is not regenerable from the client pull and is not in
  this container. When the file is absent the script carries the 57 `dungeon` and `Ordeal`
  rows over from the committed `key-mats.json` unchanged, keyed by item name. Those rows
  are therefore still the **Taiwan 2026-08** tables and stay that way until the curated file
  is available again. Everything that touches them (drop chances, ×quantities, boss lists,
  "All 12 dungeons") has not been re-verified against Global.
- **Quest counts are per record.** Light and dark mirrors of a quest are separate records
  and are both counted ("116 quests" = 58 per faction). The `detail` examples dedupe by
  name and show up to three, sorted by level then id.
- **Level is `recommendedLevel`**, not `unlockLevel` (Unspoken Story unlocks at 10, is
  recommended at 16; the page shows Lv 16, as the Taiwan build did).
- **Quest categories** (`mainCategory`): hero → "Story quests", district → "District
  quests", exploration → "Sealed dungeons", ascension, gathercraftmastery → "Crafting
  mastery quests", daevagauge, dutymission → "Duty quests", dutyscroll → "Command scrolls".
  Only Duty quests and Command scrolls land in the repeatable group.
- **⚠ Sealed-dungeon (exploration) quests have empty reward lists in Global.** All 204
  `exploration` records carry `questRewardsItems: []` (race `all`), so no item is credited
  to them any more. The Taiwan pull credited them with a title and a Daevanion Crystal
  each; that is the main reason Daevanion Crystal dropped from 172 to 116 quests. Whether
  the in-game reward is really gone or just missing from the pull is unverified.
- **Level 46+ district quests are not in Global** (the pull tops out at Lv 45 apart from
  six invalid Lv 99 event stubs). Rows that only came from those quests are gone: Skin
  Chest (10 times) (was 3 × 6 quests), Sync Stone (Unique) (was 16), and half of the
  Clash Rune Chest (16 → 8) and Rare Theostone Chest (14 → 6) quests.
- **Reward swaps at Lv 45.** The Spacetime Rift chain now pays Abyss Points instead of
  Stigma Shard (Stigma Shard: 14 quests → none), and the Lv 45 Ariel quests (Creeping
  Darkness, Unfinished Operation, Awaiting the Dawn…) pay `Odyle (Bound)` ×5 instead of
  Daevanion Crystal: Ariel (10 quests → none). `Odyle (Bound)` is not joined to the
  "Odyle Energy" roster row because the names differ.
- Every one of the 116 valid district quests rewards Wisdom Stone ×1 + Daevanion
  Crystal ×1 (guaranteed) plus a title. Wisdom Stone is not a roster item.
- Item names have " (Bound)" stripped in the output; the join uses the full name.
