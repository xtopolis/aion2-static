# Aion 2 Static Site — DocKit/Astro Setup

**Date:** 2026-08-17
**Status:** Approved

## Purpose

Stand up a static documentation site for Aion 2 in this repo (`xtopolis/aion2-static`),
using the [DocKit Astro](https://github.com/themefisher/dockit-astro) theme, built and
deployed to GitHub Pages at `https://aion.xtopolis.com`.

The sibling project `tl-mechs-static` (a Throne and Liberty mechanics guide, Astro +
Starlight on GitHub Pages) is the reference for deployment and repo conventions.

## Success Criteria

1. `npm install` succeeds from a clean checkout.
2. `npm run build` exits 0 and emits `dist/`.
3. `npx astro check` reports no errors.
4. `npm run preview` serves a working site: homepage, nested doc pages, sidebar
   navigation, dark/light toggle, and Pagefind search all function.
5. `dist/CNAME` contains `aion.xtopolis.com`.
6. No `/fr/` routes are emitted.
7. A push to `main` triggers the GitHub Pages workflow and publishes.

## Approach

**Vendor the theme as our own source.** Themefisher themes are not npm packages; the
intended workflow is to adopt the repo's `src/`, config, and `package.json` as your
project. The theme is copied in without its git history, and
`themefisher/dockit-astro` is recorded as a secondary git remote (`upstream-theme`) so
future upstream changes can be diffed and cherry-picked.

Alternatives considered and rejected:

- **Plain Starlight + cherry-picked dockit pieces** — leaner, but discards most of the
  reason for choosing the theme and makes later re-integration manual.
- **Git subtree with upstream tracking** — only pays off if upstream is tracked closely.
  DocKit updates rarely, and a subtree makes local edits merge-noisy.

## Stack

Versions are pinned exactly (not carets) for reproducible CI builds, matching what the
theme ships:

| Package | Version |
|---|---|
| astro | 7.0.3 |
| @astrojs/starlight | 0.41.1 |
| @astrojs/starlight-tailwind | 5.0.0 |
| tailwindcss / @tailwindcss/vite | 4.x |
| @pagefind/default-ui | 1.x |
| astro-vtbot | 2.x (view transitions) |
| sharp, marked, astro-font, @astro-community/astro-embed-youtube | theme defaults |

**Package manager: npm.** The theme ships `pnpm-lock.yaml` and `yarn.lock`; both are
deleted and a `package-lock.json` is generated. This matches `tl-mechs-static` and the
`npm ci` step in the deploy workflow. Node is pinned via `.nvmrc` (v24).

## Repo Layout

```
astro.config.mjs        site: https://aion.xtopolis.com; locales reduced to English
src/config/*.json       config.json, sidebar.json, social.json, theme.json, menu.en.json
src/content/docs/       theme demo content, kept as reference; fr/ removed
src/content/sections/   CTA sections; fr/ removed
src/components/         override-components + user-components, unchanged
src/styles/global.css   theme styles + Tailwind
src/lib/, src/assets/, src/tailwind-plugin/
public/CNAME            aion.xtopolis.com
.github/workflows/deploy.yml
.nvmrc  .gitignore  tsconfig.json  README.md
docs/superpowers/specs/ this document
```

## Decisions

### Demo content: kept as reference

The theme's demo docs (`getting-started`, `configurations`, `reference`, `contents`,
plus `about`, `privacy-policy`, `terms-conditions`, `404`) stay in place. They
demonstrate every custom component working and serve as copy-paste patterns. Pages get
deleted as real Aion 2 content replaces them.

### i18n: English only

The theme ships an en/fr multilingual scaffold. French is removed:

- `src/config/locals.json` reduced to the `root` (English) entry only.
- Deleted: `src/config/menu.fr.json`, `src/content/docs/fr/`,
  `src/content/sections/fr/`, `src/content/i18n/fr.json`.
- `translations` keys pruned from `src/config/sidebar.json` and
  `src/config/config.json`.

This is the highest-risk edit — `src/lib/utils/languagePerser.ts` and the header
components read these files. The build and rendered navigation are verified afterward.

### Branding: placeholder

`src/config/config.json` gets title "Aion 2" with a generic guide description and
`base_url` `https://aion.xtopolis.com`. The theme's stock logo and color palette are
retained for now; copy and art are refined later. Themefisher's copyright string in
`params.copyright` is replaced, and the theme's MIT attribution is preserved in the
README.

### Removed from the theme

`netlify.toml`, `wrangler.jsonc`, the `wrangler` devDependency and the two
`*:cf-workers` npm scripts, `.sitepins/`, `.vscode/`, `pnpm-lock.yaml`, `yarn.lock`,
and the upstream `README.md`. The upstream `LICENSE` (MIT) is retained.

## Deployment

`.github/workflows/deploy.yml` is ported from `tl-mechs-static`: on push to `main` and
`workflow_dispatch`; permissions `contents: read`, `pages: write`, `id-token: write`;
`pages` concurrency group; Node 24 with npm cache; `npm ci`; `npm run build`;
`actions/upload-pages-artifact@v3` on `./dist`; `actions/deploy-pages@v4`.

Because the site uses a custom domain, `base` stays `/` and `site` is hardcoded to
`https://aion.xtopolis.com` in `astro.config.mjs`. `public/CNAME` carries the domain
into `dist/`.

**Out-of-repo prerequisites** (documented in the README, not performed by this work):

1. Repo Settings → Pages → Source set to **GitHub Actions**.
2. DNS `CNAME` record: `aion` → `xtopolis.github.io`.
3. Custom domain `aion.xtopolis.com` entered in Settings → Pages, with Enforce HTTPS
   enabled once the certificate provisions.

## Verification Plan

Run in order; each must pass before the next:

1. `npm install` — clean, no unresolved peer conflicts.
2. `npm run build` — exit 0.
3. `npx astro check` — no type errors.
4. `npm run preview` — manually confirm homepage, a nested doc page, sidebar,
   theme toggle, and Pagefind search.
5. `ls dist/CNAME` and `find dist -path '*/fr/*'` (expect the former present, the
   latter empty).

## Known Risks

- **npm peer dependencies.** The theme is developed with pnpm. Astro 7, Starlight 0.41,
  and Vite 8 are all recent; npm may surface peer conflicts. If `--legacy-peer-deps` or
  a version nudge is required, it is reported rather than silently applied.
- **i18n strip breaking components.** Components that assume a populated locale map may
  fail. Verified via build plus rendered navigation.
- **Image service.** The theme sets `image.service` to Astro's `noop`, disabling image
  optimization. Left at the theme default to avoid breaking its components; revisit if
  image-heavy content is added.
