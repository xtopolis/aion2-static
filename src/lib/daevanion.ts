import raw from "@/data/daevanion.json";
import { labelOf, isPercent, scale } from "./stats";

/**
 * Shapes the normalized Daevanion dataset into the payloads the board page
 * fetches. Run at build time only — see src/pages/data/daevanion/.
 *
 * Split three ways so a visitor only pays for what they look at:
 *   index          — always; class list, board list, stat vocabulary
 *   layout-<god>   — one per board, fetched when that board is first opened
 *   class-<key>    — one per class, fetched when that class is first chosen
 *
 * The 8 layouts are shared by all 9 classes: boards 1-4 differ only in which
 * skills their 22 skill nodes point at (that is the class overlay), and boards
 * 5-8 have no skill nodes at all, so they are identical everywhere.
 */

/** Node kinds, as stored in the normalized data. */
export const NODE_START = 0;
export const NODE_STAT = 1;
export const NODE_SKILL = 2;

export interface StatMeta {
  id: string;
  label: string;
  /** true when values should render with a % sign */
  pct: boolean;
}

export interface GodMeta {
  key: string;
  /** board slot 1-8, also the unlock order */
  order: number;
  needLevel: number;
  /** points to buy every node on the board */
  points: number;
  resetGold: number;
  /** false for boards 5-8, which are pure stats and class-agnostic */
  hasSkills: boolean;
}

export interface DaevanionIndex {
  grid: { rows: number; cols: number; origin: { row: number; col: number } };
  gradeNames: Record<string, string>;
  gradeCost: Record<string, number>;
  classes: { key: string; name: string }[];
  gods: GodMeta[];
  /** every stat any board grants, alphabetical by label */
  stats: StatMeta[];
}

export interface LayoutNode {
  /** 1-indexed grid position */
  r: number;
  c: number;
  /** grade; also determines cost via index.gradeCost */
  g: number;
  /** NODE_START | NODE_STAT | NODE_SKILL */
  t: number;
  /** [statId, displayScaledValue][] — absent on start and skill nodes */
  e?: [string, number][];
}

export interface LayoutPayload {
  key: string;
  nodes: LayoutNode[];
}

export interface ClassPayload {
  key: string;
  name: string;
  /** skills this class can level, keyed by skill id */
  skills: Record<
    string,
    { name: string; slug: string; type: string; maxLevel: number }
  >;
  /**
   * god -> skill id per skill node, in the same row-major order the layout's
   * skill nodes appear. Only boards 1-4 have entries.
   */
  overlays: Record<string, string[]>;
}

type RawShape = {
  grid: DaevanionIndex["grid"];
  gradeNames: Record<string, string>;
  gradeCost: Record<string, number>;
  classes: { key: string; name: string }[];
  gods: GodMeta[];
  layouts: Record<string, { nodes: LayoutNode[] }>;
  skills: Record<
    string,
    { n: string; c: string; t: string; m: number; s: string }
  >;
  overlays: Record<string, Record<string, string[]>>;
};

// TypeScript infers a huge literal union from the JSON import; the runtime shape
// is the documented schema, so widen through `unknown`.
const data = raw as unknown as RawShape;

export const godKeys = (): string[] => data.gods.map((g) => g.key);
export const classKeys = (): string[] => data.classes.map((c) => c.key);

export function buildIndex(): DaevanionIndex {
  const used = new Set<string>();
  for (const layout of Object.values(data.layouts)) {
    for (const n of layout.nodes) for (const [id] of n.e ?? []) used.add(id);
  }

  return {
    grid: data.grid,
    gradeNames: data.gradeNames,
    gradeCost: data.gradeCost,
    // alphabetical, so the picker reads the way the sidebar does
    classes: [...data.classes].sort((a, b) => a.name.localeCompare(b.name)),
    gods: data.gods,
    stats: [...used]
      .map((id) => ({ id, label: labelOf(id), pct: isPercent(id) }))
      .sort((a, b) => a.label.localeCompare(b.label)),
  };
}

/**
 * One board's grid. Stat values are scaled for display here so the client never
 * has to know the basis-point rule.
 */
export function buildLayout(god: string): LayoutPayload {
  const layout = data.layouts[god];
  if (!layout) throw new Error(`daevanion: unknown board "${god}"`);

  return {
    key: god,
    nodes: layout.nodes.map((n) => {
      const node: LayoutNode = { r: n.r, c: n.c, g: n.g, t: n.t };
      if (n.e) node.e = n.e.map(([id, v]) => [id, scale(id, v)]);
      return node;
    }),
  };
}

export function buildClass(key: string): ClassPayload {
  const cls = data.classes.find((c) => c.key === key);
  if (!cls) throw new Error(`daevanion: unknown class "${key}"`);

  const overlays = data.overlays[key] ?? {};
  // Only the skills this class actually reaches, so each class payload carries
  // 22 entries rather than all 198.
  const skills: ClassPayload["skills"] = {};
  for (const id of new Set(Object.values(overlays).flat())) {
    const s = data.skills[id];
    skills[id] = { name: s.n, slug: s.s, type: s.t, maxLevel: s.m };
  }

  return { key, name: cls.name, skills, overlays };
}
