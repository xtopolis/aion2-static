import type { APIRoute } from "astro";
import { buildIndex } from "@/lib/crafting";

/** Items, gatherables and the icon table — shared by both factions. */
export const prerender = true;

export const GET: APIRoute = () =>
  new Response(JSON.stringify(buildIndex()), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
