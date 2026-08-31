import type { APIRoute } from "astro";
import { buildSkillLevels } from "@/lib/skill-levels";

/**
 * The whole dataset in one payload — 27 KB covers all nine classes, which is
 * smaller than the per-class split would cost in extra round trips.
 */
export const prerender = true;

export const GET: APIRoute = () =>
  new Response(JSON.stringify(buildSkillLevels()), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
