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
  dungeon drops, vendor items. QuestLog's recipe DB carries no drop tables or vendor
  listings. Expanding every recipe to its leaves lands on unsourced items 7,706 times vs
  2,254 on gatherables, so "obtained from content" is a first-class answer, not an error.
- **Guard recursion:** 40 recipes are in-place upgrades (output id also appears as an
  input) and 20 items sit in a craft cycle. Track visited per path, not globally. Craft
  depth is shallow though — at most 4.
- Item **stats** are not here, only crafting identity.
