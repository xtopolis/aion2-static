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

**This one is not a raw dump.** The upstream handoff package ships all 72 boards as
separate node files (3.37 MB); this is a **lossless normalization** of it down to 196 KB.
Every one of the 72 boards is rebuilt from this file and compared field-by-field during
normalization, so nothing is lost — only redundancy.

- **9 classes × 8 god boards, but only 8 distinct layouts.** Boards 1–4 (Nezekan, Zikel,
  Vaizel, Triniel) share one stat template per god across all 9 classes and differ *only*
  in which skills their 22 skill nodes point at — that difference is the per-class
  `overlays`. Boards 5–8 (Ariel, Azphel, Marchutan, Yustiel) have no skill nodes at all
  and are identical for every class.
- **Adjacency is the prerequisite graph.** The dump carries no link field; a node is
  buyable when a 4-neighbour is owned. Neighbours are therefore derivable from `r`/`c`
  and are not stored.
- **Dropped because derivable:** `neighbors`, `cost` (from `grade` via `gradeCost`),
  `resetGold` (flat 500, 0 for start), `distanceFromStart`, and `minPointsToUnlock`
  (a Dijkstra from centre, exact — recompute in ~153 steps if an optimizer needs it).
- **⚠ Node names are dropped deliberately.** They are inconsistent in the dump: the same
  stat id is named two ways depending on the node (`fixingdamage` is "Attack" on 864
  nodes but "Attack Bonus" on 18; `defense` is "Defense" on 981 but "Defense Bonus" on
  18), and 13 skill nodes disagree with the skill index about their own skill's name
  (e.g. node "Armor of Protection" vs skill "Protection Armor"). The UI renders from the
  glossary label and the skill index instead, which are internally consistent.
- **Skill nodes always grant +1 level.** Stacking multiple nodes for the same skill is
  how you reach +2/+3; a skill can appear on two nodes on the same board.
- Skill icons live in `public/skills/<class>/<slug>.webp`, where `slug` is stored on each
  skill so the client never reimplements the slug rules.
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
