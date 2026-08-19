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
