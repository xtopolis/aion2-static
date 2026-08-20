import type { APIRoute, GetStaticPaths } from "astro";
import { buildRecipes, factions, type Faction } from "@/lib/crafting";

/** One file per faction; only the chosen side is ever fetched. */
export const prerender = true;

export const getStaticPaths: GetStaticPaths = () =>
  factions.map((faction) => ({ params: { faction } }));

export const GET: APIRoute = ({ params }) =>
  new Response(JSON.stringify(buildRecipes(params.faction as Faction)), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
