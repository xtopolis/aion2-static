import type { APIRoute } from "astro";
import { buildIndex } from "@/lib/daevanion";

/**
 * Class list, board list and stat vocabulary — the only payload the page always
 * needs. Layouts and class overlays are fetched on demand alongside it.
 */
export const prerender = true;

export const GET: APIRoute = () =>
  new Response(JSON.stringify(buildIndex()), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
