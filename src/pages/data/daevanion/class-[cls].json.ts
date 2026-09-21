import type { APIRoute, GetStaticPaths } from "astro";
import { buildClass, classKeys } from "@/lib/daevanion";

/**
 * One file per class, carrying just that class's skills, the skill-node
 * overlays for the boards that have skill nodes, and any per-class node patches.
 */
export const prerender = true;

export const getStaticPaths: GetStaticPaths = () =>
  classKeys().map((cls) => ({ params: { cls } }));

export const GET: APIRoute = ({ params }) =>
  new Response(JSON.stringify(buildClass(params.cls!)), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
