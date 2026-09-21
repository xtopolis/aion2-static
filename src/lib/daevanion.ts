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
 * One layout is shared by every class per board. The boards that carry skill
 * nodes differ per class only in which skills those nodes point at (the class
 * overlay), plus a handful of stat nodes that one class has swapped (the class
 * patches, applied on top of the layout by position). The level-45 board has
 * no skill nodes and no patches, so it is identical everywhere.
 *
 * Nothing here knows how many boards or classes there are — both come from
 * the data. The Global LST data has 5 boards (Nezekan, Zikel, Vaizel, Triniel,
 * Azphel) for 8 classes; the Taiwan dump had 8 boards for 9.
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
  /** the game's board slot, also the unlock order; slots can be sparse */
  order: number;
  needLevel: number;
  /** points to buy every node on the board, recomputed from the layout */
  points: number;
  /** currency the board's nodes are bought with, e.g. daevanion_crystal */
  costPointType?: string;
  /** board-level reset price; absent when the source does not carry it */
  resetGold?: number;
  /** false for a pure-stat board, which is class-agnostic */
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

export interface SkillMeta {
  name: string;
  slug: string;
  type: string;
  /** absent when the source carries no max level (the Global skills DB does not) */
  maxLevel?: number;
}

export interface ClassPayload {
  key: string;
  name: string;
  /** skills this class can level, keyed by skill id */
  skills: Record<string, SkillMeta>;
  /**
   * god -> skill id per skill node, in the same row-major order the layout's
   * skill nodes appear. Only boards with skill nodes have entries.
   */
  overlays: Record<string, string[]>;
  /**
   * god -> nodes that replace the shared layout's node at the same position
   * for this class. Values are display-scaled like the layout's. Usually empty.
   */
  patches: Record<string, LayoutNode[]>;
}

type RawShape = {
  grid: DaevanionIndex["grid"];
  gradeNames: Record<string, string>;
  gradeCost: Record<string, number>;
  classes: { key: string; name: string }[];
  gods: GodMeta[];
  layouts: Record<string, { nodes: LayoutNode[] }>;
  patches?: Record<string, Record<string, LayoutNode[]>>;
  skills: Record<
    string,
    { n: string; c: string; t: string; m?: number; s: string }
  >;
  overlays: Record<string, Record<string, string[]>>;
};

// TypeScript infers a huge literal union from the JSON import; the runtime shape
// is the documented schema, so widen through `unknown`.
const data = raw as unknown as RawShape;

export const godKeys = (): string[] => data.gods.map((g) => g.key);
export const classKeys = (): string[] => data.classes.map((c) => c.key);

/** Stat values scaled for display, so the client never sees basis points. */
const scaleNode = (n: LayoutNode): LayoutNode => {
  const node: LayoutNode = { r: n.r, c: n.c, g: n.g, t: n.t };
  if (n.e) node.e = n.e.map(([id, v]) => [id, scale(id, v)]);
  return node;
};

export function buildIndex(): DaevanionIndex {
  const used = new Set<string>();
  const collect = (nodes: LayoutNode[]) => {
    for (const n of nodes) for (const [id] of n.e ?? []) used.add(id);
  };
  for (const layout of Object.values(data.layouts)) collect(layout.nodes);
  for (const byGod of Object.values(data.patches ?? {})) {
    for (const nodes of Object.values(byGod)) collect(nodes);
  }

  return {
    grid: data.grid,
    gradeNames: data.gradeNames,
    gradeCost: data.gradeCost,
    // alphabetical, so the picker reads the way the sidebar does
    classes: [...data.classes].sort((a, b) => a.name.localeCompare(b.name)),
    gods: [...data.gods].sort((a, b) => a.order - b.order),
    stats: [...used]
      .map((id) => ({ id, label: labelOf(id), pct: isPercent(id) }))
      .sort((a, b) => a.label.localeCompare(b.label)),
  };
}

/** One board's shared grid. */
export function buildLayout(god: string): LayoutPayload {
  const layout = data.layouts[god];
  if (!layout) throw new Error(`daevanion: unknown board "${god}"`);
  return { key: god, nodes: layout.nodes.map(scaleNode) };
}

export function buildClass(key: string): ClassPayload {
  const cls = data.classes.find((c) => c.key === key);
  if (!cls) throw new Error(`daevanion: unknown class "${key}"`);

  const overlays = data.overlays[key] ?? {};
  // Only the skills this class actually reaches, so each class payload carries
  // its own 22 entries rather than the whole index.
  const skills: ClassPayload["skills"] = {};
  for (const id of new Set(Object.values(overlays).flat())) {
    const s = data.skills[id];
    if (!s) throw new Error(`daevanion: ${key} board points at unknown skill ${id}`);
    skills[id] = { name: s.n, slug: s.s, type: s.t };
    if (s.m !== undefined) skills[id].maxLevel = s.m;
  }

  const patches: ClassPayload["patches"] = {};
  for (const [god, nodes] of Object.entries(data.patches?.[key] ?? {})) {
    patches[god] = nodes.map(scaleNode);
  }

  return { key, name: cls.name, skills, overlays, patches };
}
