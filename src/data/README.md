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
