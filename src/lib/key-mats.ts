import raw from "@/data/key-mats.json";

/**
 * Every farmable material and currency, with every source we hold for it.
 * Built by scripts/build-key-mats.py; served whole to the Key Mats page.
 */

export type SourceKind = "dungeon" | "quest" | "shop" | "activity";

export type SourceGroup = "onetime" | "dungeon" | "other";

export interface KeyMatSource {
  kind: SourceKind;
  /** which sub-table the row lands in on the Key Mats page */
  group: SourceGroup;
  /** source name, e.g. "Duty quests" */
  label: string;
  /** short note; may be empty */
  detail: string;
  /** short figure like "14 / week" or "12%" */
  cap: string | null;
  /** "data" came from a captured table, "community" from guides */
  conf: "data" | "community";
}

export interface KeyMatItem {
  name: string;
  cat: string;
  sub: string | null;
  /** `/icons/...` path under public/, or null */
  icon: string | null;
  sources: KeyMatSource[];
}

export interface KeyMatsPayload {
  generated: string;
  items: KeyMatItem[];
}

const data = raw as unknown as KeyMatsPayload;

export const buildKeyMats = (): KeyMatItem[] => data.items;
