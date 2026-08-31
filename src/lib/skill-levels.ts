import raw from "@/data/skill-levels.json";

/**
 * Every source that can raise one skill's level, shaped for the Skill Levels
 * page. Built at build time from the client dump by scripts/build-skill-levels.py.
 *
 * The structure is identical for all nine classes — 12 actives and 10 passives,
 * each reachable from exactly one small-pool arcana card plus Chalice and
 * Scales, and each granted +4 across the four crystal boards. Actives take one
 * node per board; passives take two on either Nezekan or Zikel and none on the
 * other. Only the membership differs, which is why this page needs a picker.
 */

export interface SkillRow {
  id: string;
  /** name */
  n: string;
  /** "active" | "passive" */
  t: string;
  icon: string;
  /**
   * Per crystal board, in unlock order: [node count, points to take them all].
   * Actives carry one node on every board; passives carry TWO on either Nezekan
   * or Zikel and none on the other, so a count of 0 is normal and the points are
   * a Steiner cost rather than a sum of the two nodes' individual paths.
   */
  dv: [number, number][];
  /** total levels the boards grant — always 4 */
  lv: number;
  /** the node's own point cost — 3 for actives (Legendary), 2 for passives (Rare) */
  dc: number;
  /** small-pool arcana card key: parchment | compass | bell | mirror */
  card: string;
}

export interface SkillLevelsPayload {
  classes: { key: string; name: string }[];
  boards: { name: string; needLevel: number }[];
  cards: Record<string, string>;
  /** share of a soul bind draw that lands on a skill rather than a stat */
  skillDrawChance: number;
  activePool: number;
  passivePool: number;
  cardPool: { small: { active: number; passive: number }; union: number };
  byClass: Record<string, { weapon: string | null; skills: SkillRow[] }>;
}

const data = raw as unknown as SkillLevelsPayload;

export const buildSkillLevels = (): SkillLevelsPayload => data;
