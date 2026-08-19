import type { APIRoute, GetStaticPaths } from "astro";
import { buildLayout, godKeys } from "@/lib/daevanion";

/**
 * One file per board (8 total), fetched the first time that board is opened and
 * cached thereafter. The layouts are class-agnostic, so switching class never
 * refetches them.
 */
export const prerender = true;

export const getStaticPaths: GetStaticPaths = () =>
  godKeys().map((god) => ({ params: { god } }));

export const GET: APIRoute = ({ params }) =>
  new Response(JSON.stringify(buildLayout(params.god!)), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
