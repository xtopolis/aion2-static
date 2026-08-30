import type { APIRoute } from "astro";
import payload from "@/data/wings.json";

/**
 * Emits the Wings dataset as a static file at /data/wings.json.
 *
 * Unlike titles, the payload in src/data/wings.json is already in its final
 * shape (faction mirrors merged, stat values scaled, +0/max-enchant pairs
 * precomputed), so this route serves it verbatim. Kept out of the page HTML so
 * the payload stays cacheable on its own and does not get scanned into the
 * Pagefind search index.
 */
export const prerender = true;

export const GET: APIRoute = () =>
  new Response(JSON.stringify(payload), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
