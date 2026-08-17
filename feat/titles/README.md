# Aion 2 — Titles dataset (static-site handoff package)

Extracted from the QuestLog.gg Taiwan-client dump (`characterBuilder.getTitles`),
normalized. **TW baseline, 2026-08 — re-verify against a Global data pull after
launch (Sept 30, 2026); grades/stats are VALUES-tier data that patches can move.**

## Files

| File | What |
|---|---|
| `titles.json` | 1,472 title records (schema below) |
| `stats-glossary.json` | Display metadata for all 77 stat ids used by titles |
| `title-finder-prototype.html` | Working reference implementation (vanilla JS) — steal its logic/UX freely |

## titles.json record schema

```jsonc
{
  "id": "23020043",          // stable string id
  "name": "Treading on White Wings",
  "description": "...",       // ALSO the obtain condition ~90% of the time (flavor-y for the rest)
  "grade": 41,                // see grade enum below
  "grade_name": "Unique",     // present for 11/21/31/41; see caveats for 51/71
  "main_category": "quest",   // obtain bucket: quest|adventure|growth|challenge|dungeon|item
  "equip_category": "attack", // equip slot: attack|defense|utility|null (null = collection-only)
  "race": "light",            // faction: light (Elyos) | dark (Asmodian) | all
  "is_visible": true,
  "order": 123,               // in-game list ordering
  "icon": "assets/...",       // sprite path (from game UI atlas; may need your own asset pipeline)
  "grants_stats": true,
  "equip_stats":      { "pvpadddamage": 35, "pvpaccuracy": 110 },  // active ONLY while equipped in its slot
  "collection_stats": { "pvpcritical": 10 }                         // permanent passive from OWNING the title
}
```

## Core game semantics

- **Three equip slots** — one title equipped per `equip_category` (attack / defense /
  utility). 844 titles have equip stats; 628 have `equip_category: null` and exist
  only for collection stats / cosmetics.
- **Collection stats stack from EVERY owned title**, equipped or not. A title with
  both stat sets contributes `collection_stats` always and `equip_stats` only
  while slotted.
- **Faction mirrors**: almost every title exists as a light + dark pair with
  identical stats and mirrored obtain text (714/714/44-shared). Dedupe by name if
  you show a single-faction view.

## Stat display rules (stats-glossary.json)

Each stat has `label`, `description`, `indicator`. **If `indicator` contains
"percent", the value is basis points: divide by 100** (`combatspeed: 500` renders
as `Combat Speed +5%`). Otherwise it's a flat integer (`accuracy: 90` → `+90`).
Sort UI stat lists by `sortOrder` for game-consistent ordering.

## Grade enum

| grade | name | count | note |
|---|---|---|---|
| 11 | Common | 274 | |
| 21 | Rare | 538 | green |
| 31 | Legend | 292 | blue |
| 41 | Unique | 160 | orange — the chase tier |
| 51 | (Heroic/Epic — unconfirmed label) | 164 | mostly season/ranked rewards |
| 71 | (special/event — unconfirmed label) | 44 | all `race: "all"`; contest/collab titles |

## Known caveats

1. `description` doubles as the obtain condition for ~90% of titles; the rest are
   pure flavor ("Title bestowed by those who witnessed such a sight"). No
   structured step/count fields exist beyond the text.
2. No drop rates / acquisition costs in this dataset.
3. 51/71 grade display names are not confirmed from data — pick neutral labels.
4. Some titles reference content that will NOT exist at Global launch
   (Season N, level-50 zones, later raids). There is no "available at launch"
   flag — deriving one from description keywords (Season, lv50 zone names) is a
   reasonable v2 enhancement.

## Suggested site features (proven in the prototype)

- Stat multi-select → score = Σ selected stat values (equip + collection),
  ranked list + best-per-slot cards.
- Filters: slot, faction, grade, obtain category, free-text over name+description.
- Per-title pages: statically generate 1,472 routes from `id`.
