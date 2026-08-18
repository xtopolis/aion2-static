import type { APIRoute } from "astro";
import { buildTitlesPayload } from "@/lib/titles";

/**
 * Emits the Titles dataset as a static file at /data/titles.json.
 *
 * Kept out of the page HTML so the payload stays cacheable on its own and does
 * not get scanned into the Pagefind search index.
 */
export const prerender = true;

export const GET: APIRoute = () =>
  new Response(JSON.stringify(buildTitlesPayload()), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
