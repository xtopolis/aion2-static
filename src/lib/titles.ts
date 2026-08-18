import rawTitles from "@/data/titles.json";
import rawGlossary from "@/data/stats-glossary.json";

/**
 * Shapes the raw title dump into the compact payload the Titles page ships to
 * the browser. Run at build time only — see src/pages/data/titles.json.ts.
 */

export type Slot = "attack" | "defense" | "utility";

/**
 * One stat on one title. Deliberately minimal: the label is looked up from
 * `TitlesPayload.stats` by id, and the display string is formatted from
 * `num`/`pct`, so neither is repeated across ~2,600 entries.
 */
export interface StatEntry {
  /** stat id, e.g. "pvpaddgrade" — also the sub-filter key */
  id: string;
  /** value scaled for display: percents already divided out of basis points */
  num: number;
  /** true when `num` is a percentage */
  pct: boolean;
  /** true when the stat applies only while the title is equipped in its slot */
  equipped: boolean;
}

export interface TitleRow {
  name: string;
  grade: number;
  gradeName: string;
  /** null for cosmetic titles, which grant nothing and occupy no slot */
  slot: Slot | null;
  /** obtain bucket: quest | adventure | growth | challenge | dungeon | item */
  category: string;
  /** doubles as the obtain condition for most titles, pure flavour for the rest */
  description: string;
  /** Elyos / Asmodian / both, merged from faction-mirrored records */
  factions: string[];
  stats: StatEntry[];
  /** ids active only while the title is slotted */
  equipIds: string[];
  /** ids granted permanently just for owning the title */
  collIds: string[];
}

export interface StatMeta {
  id: string;
  label: string;
}

export interface TitlesPayload {
  rows: TitleRow[];
  /** every stat in use, alphabetical by label, for the sub-level filter */
  stats: StatMeta[];
  /** stat ids present per top-level slot, so sub-filters can adjust dynamically */
  statsBySlot: Record<string, string[]>;
}

type RawTitle = {
  name: string;
  grade: number;
  grade_name: string;
  main_category: string;
  equip_category: string | null;
  description: string;
  faction?: string | null;
  equip_stats?: Record<string, number> | null;
  collection_stats?: Record<string, number> | null;
};

type RawStat = {
  label: string;
  isPercentBasisPoints?: boolean;
};

const glossary = (rawGlossary as unknown as { stats: Record<string, RawStat> })
  .stats;

/** Friendly name for a stat, falling back to the raw id if unmapped. */
const labelOf = (id: string): string => glossary[id]?.label ?? id;

/**
 * Percent stats are stored as basis points (500 => 5%); everything else is a
 * flat integer.
 */
function toStat(id: string, value: number, equipped: boolean): StatEntry {
  const pct = glossary[id]?.isPercentBasisPoints === true;
  return { id, num: pct ? value / 100 : value, pct, equipped };
}

/** Faction mirrors share everything but faction and (sometimes) obtain text. */
function mergeKey(t: RawTitle): string {
  return [
    t.name,
    t.grade,
    t.equip_category ?? "",
    JSON.stringify(t.equip_stats ?? {}),
    JSON.stringify(t.collection_stats ?? {}),
  ].join("|");
}

export function buildTitlesPayload(): TitlesPayload {
  // TypeScript infers a huge literal union from the JSON import; the runtime
  // shape is the documented schema, so widen through `unknown`.
  const titles = (rawTitles as unknown as { titles: RawTitle[] }).titles;

  const groups = new Map<string, RawTitle[]>();
  for (const t of titles) {
    const k = mergeKey(t);
    const g = groups.get(k);
    if (g) g.push(t);
    else groups.set(k, [t]);
  }

  const rows: TitleRow[] = [];
  for (const group of groups.values()) {
    const t = group[0];
    const stats: StatEntry[] = [];
    for (const [id, v] of Object.entries(t.equip_stats ?? {})) {
      stats.push(toStat(id, v, true));
    }
    for (const [id, v] of Object.entries(t.collection_stats ?? {})) {
      stats.push(toStat(id, v, false));
    }
    // equipped first, then collection: the table shows them in this order, and
    // collection bonuses are the incidental ones
    stats.sort(
      (a, b) =>
        Number(b.equipped) - Number(a.equipped) ||
        labelOf(a.id).localeCompare(labelOf(b.id))
    );

    // Titles available to everyone are tagged "Both" in the dump; faction
    // mirrors merge into two records. Normalise both to explicit faction names
    // so the UI only ever renders real factions.
    const factionSet = new Set<string>();
    for (const x of group) {
      if (!x.faction) continue;
      if (x.faction === "Both") {
        factionSet.add("Elyos");
        factionSet.add("Asmodian");
      } else {
        factionSet.add(x.faction);
      }
    }
    const order = ["Elyos", "Asmodian"];
    const factions = [...factionSet].sort(
      (a, b) => order.indexOf(a) - order.indexOf(b)
    );

    rows.push({
      name: t.name,
      grade: t.grade,
      gradeName: t.grade_name,
      slot: (t.equip_category as Slot | null) ?? null,
      category: t.main_category,
      description: t.description ?? "",
      factions,
      stats,
      equipIds: [...new Set(stats.filter((s) => s.equipped).map((s) => s.id))],
      collIds: [...new Set(stats.filter((s) => !s.equipped).map((s) => s.id))],
    });
  }

  // Highest grade first, then alphabetical — stable and useful by default.
  rows.sort((a, b) => b.grade - a.grade || a.name.localeCompare(b.name));

  const usedStatIds = new Set(rows.flatMap((r) => [...r.equipIds, ...r.collIds]));
  const stats: StatMeta[] = [...usedStatIds]
    .map((id) => ({ id, label: labelOf(id) }))
    .sort((a, b) => a.label.localeCompare(b.label));

  const statsBySlot: Record<string, Set<string>> = {
    all: new Set(),
    attack: new Set(),
    defense: new Set(),
    utility: new Set(),
  };
  for (const r of rows) {
    for (const id of [...r.equipIds, ...r.collIds]) {
      statsBySlot.all.add(id);
      if (r.slot) statsBySlot[r.slot].add(id);
    }
  }

  return {
    rows,
    stats,
    statsBySlot: Object.fromEntries(
      Object.entries(statsBySlot).map(([k, v]) => [k, [...v]])
    ),
  };
}
