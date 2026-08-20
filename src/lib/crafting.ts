import raw from "@/data/crafting.json";
import vendor from "@/data/vendor-prices.json";

/**
 * Shapes the crafting dataset into the payloads the recipe browser fetches.
 * Run at build time only — see src/pages/data/crafting/.
 *
 * Split by faction: light and dark recipes are 1:1 twins but genuinely differ
 * (different names, outputs and materials), so a visitor only ever needs one
 * side. Items, gatherables and the icon table are shared.
 */

export interface Recipe {
  /** recipe id */
  i: string;
  n: string;
  /** index into the shared icon table */
  c: number;
  /** index into `professions` */
  p: number;
  /** the game's own grouping label, e.g. "Sword" */
  t: string;
  g: number;
  /** 0 = light, 1 = dark */
  f: number;
  /** [itemId, quantity][] */
  in: [string, number][];
  /** [itemId, quantity] */
  out: [string, number];
  /** crafting skill required, absent when the recipe is ungated */
  m?: number;
  mg?: string;
  /** proc chance as a percentage, absent when the recipe cannot proc */
  cp?: number;
  /** the upgraded item produced on a proc */
  co?: string;
}

/** [name, iconIndex, grade, sourceKind] */
export type ItemTuple = [string, number, number, string];

export interface Gatherable {
  i: string;
  n: string;
  c: number;
  g: number;
  cat: string;
  m: number;
  /** [itemId, count, isBonus][] */
  d: [string, number, number][];
}

export interface CraftingIndex {
  professions: string[];
  /** icon basenames; the client builds /icons/crafting/<slug>.webp */
  icons: string[];
  items: Record<string, ItemTuple>;
  /**
   * Item ids that a gathering node drops. Only the ids ship: the browser asks
   * "is this gathered", and the full drop tables are 23 KB of detail nothing
   * renders yet. `gatherables` stays in src/data for when a nodes page exists.
   */
  gathered: string[];
  /** recipe count per faction, so the UI can label the toggle before fetching */
  counts: { light: number; dark: number };
  /** item id -> kinah per unit, for the items known to be vendor-bought */
  vendorPrices: Record<string, number>;
}

type RawRecipe = Recipe & { gauge: number };

type RawShape = {
  professions: string[];
  icons: string[];
  recipes: RawRecipe[];
  items: Record<string, ItemTuple>;
  gatherables: Gatherable[];
};

// TypeScript infers a huge literal union from the JSON import; the runtime shape
// is the documented schema, so widen through `unknown`.
const data = raw as unknown as RawShape;

const vendorPrices: Record<string, number> = Object.fromEntries(
  Object.entries(
    (vendor as unknown as { prices: Record<string, { kinah: number }> }).prices
  ).map(([id, v]) => [id, v.kinah])
);

/**
 * Recipes consuming this are gear-conversion entries rather than crafts, and are
 * excluded everywhere — see src/data/README.md.
 */
const GEAR_CHANGE_VOUCHER = "632510022";
const isExcluded = (r: Recipe) => r.in.some(([id]) => id === GEAR_CHANGE_VOUCHER);

/**
 * The dump's profession keys are not what the client calls them. Confirmed
 * in-game: a `tailoring` recipe reads "Armorsmithing Proficiency", and
 * `jewelcrafting` is Handicrafting. `alchemy` and `cooking` are unverified and
 * pass through as-is.
 */
const PROFESSION_NAMES: Record<string, string> = {
  blacksmithing: "Blacksmithing",
  tailoring: "Armorsmithing",
  jewelcrafting: "Handicrafting",
  alchemy: "Alchemy",
  cooking: "Cooking",
};

const professionName = (key: string) =>
  PROFESSION_NAMES[key] ?? key.charAt(0).toUpperCase() + key.slice(1);

export const factions = ["light", "dark"] as const;
export type Faction = (typeof factions)[number];

export function buildIndex(): CraftingIndex {
  return {
    // display names, so nothing downstream has to know the dump's keys
    professions: data.professions.map(professionName),
    icons: data.icons,
    items: data.items,
    gathered: [...new Set(data.gatherables.flatMap((g) => g.d.map(([id]) => id)))],
    counts: {
      light: buildRecipes("light").length,
      dark: buildRecipes("dark").length,
    },
    vendorPrices,
  };
}

export function buildRecipes(faction: Faction): Recipe[] {
  const want = faction === "light" ? 0 : 1;
  // `gauge` is dropped: it is nearly a pure function of grade, so it told the
  // reader nothing the grade chip did not. See src/data/README.md.
  return data.recipes
    .filter((r) => r.f === want && !isExcluded(r))
    .map(({ gauge, ...rest }) => rest);
}

