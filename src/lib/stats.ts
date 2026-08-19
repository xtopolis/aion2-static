import rawGlossary from "@/data/stats-glossary.json";

/**
 * Shared stat vocabulary. Every dataset in src/data/ refers to stats by the
 * same ids, so labels and units are resolved here rather than per-feature.
 *
 * Build time only — importing this pulls in the whole glossary.
 */

export interface StatMeta {
  id: string;
  label: string;
}

/** One stat value, already scaled for display. */
export interface StatValue {
  id: string;
  /** percents are divided out of basis points; flat stats pass through */
  num: number;
  /** true when `num` should render with a % sign */
  pct: boolean;
}

type RawStat = {
  label: string;
  isPercentBasisPoints?: boolean;
};

const glossary = (rawGlossary as unknown as { stats: Record<string, RawStat> })
  .stats;

/** Friendly name for a stat, falling back to the raw id if unmapped. */
export const labelOf = (id: string): string => glossary[id]?.label ?? id;

/**
 * Percent stats are stored as basis points (500 => 5%); everything else is a
 * flat integer. Getting this wrong renders 10bp as "10%" instead of "0.1%".
 */
export const isPercent = (id: string): boolean =>
  glossary[id]?.isPercentBasisPoints === true;

/** Raw dataset value -> display-scaled value. */
export const scale = (id: string, value: number): number =>
  isPercent(id) ? value / 100 : value;

export const toStat = (id: string, value: number): StatValue => ({
  id,
  num: scale(id, value),
  pct: isPercent(id),
});

/** Dedupes ids and resolves labels, alphabetical — the shape filter UIs want. */
export function statMeta(ids: Iterable<string>): StatMeta[] {
  return [...new Set(ids)]
    .map((id) => ({ id, label: labelOf(id) }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

/** Sort comparator putting stats in label order. */
export const byLabel = (a: { id: string }, b: { id: string }): number =>
  labelOf(a.id).localeCompare(labelOf(b.id));
