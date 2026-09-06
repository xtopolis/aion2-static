import type { APIRoute } from "astro";
import { buildKeyMats } from "@/lib/key-mats";

/** The whole item list in one payload; 78 items is far too small to split. */
export const prerender = true;

export const GET: APIRoute = () =>
  new Response(JSON.stringify(buildKeyMats()), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
