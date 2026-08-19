import type { APIRoute, GetStaticPaths } from "astro";
import { buildClass, classKeys } from "@/lib/daevanion";

/**
 * One file per class (9 total), carrying just that class's 22 skills and the
 * skill-node overlays for boards 1-4.
 */
export const prerender = true;

export const getStaticPaths: GetStaticPaths = () =>
  classKeys().map((cls) => ({ params: { cls } }));

export const GET: APIRoute = ({ params }) =>
  new Response(JSON.stringify(buildClass(params.cls!)), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
