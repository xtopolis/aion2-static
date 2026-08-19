# aion2-static

Guides, mechanics, and reference for Aion 2 — a static site built with
[Astro](https://astro.build) and [Starlight](https://starlight.astro.build), using the
[DocKit](https://github.com/themefisher/dockit-astro) theme.

Deployed to GitHub Pages at **https://aion.xtopolis.com**.

## Local development

Requires Node 24 (see `.nvmrc`).

```bash
nvm use
npm install
npm run dev      # dev server at http://localhost:4321
```

Other scripts:

| Command | Description |
|---|---|
| `npm run build` | Build the production site to `dist/` |
| `npm run preview` | Serve the built `dist/` locally |
| `npm run check` | Type-check Astro/TypeScript files |

Note that site search (Pagefind) is generated during `build`, so it works in
`preview` but not in `dev`.

**Before pushing, verify with `npm ci`, not `npm install`.** That is what CI runs, and
the two do not resolve dependencies identically:

```bash
rm -rf node_modules && npm ci && npm run build
```

### Why `@astrojs/markdown-remark` is a direct dependency

It looks redundant — nothing in `src/` imports it — but do not remove it. Both `astro`
and `@astrojs/starlight` declare it as an *optional peer dependency*, so no package
pulls it in as a real dependency. `npm install` auto-installs missing peers and papers
over this; `npm ci` installs only the reachable tree and does not. Meanwhile
`@astrojs/mdx` depends on a different patch version (7.2.2), so npm nests that copy
instead of hoisting it to the root where Starlight can resolve it.

Without the explicit `"@astrojs/markdown-remark": "7.2.0"` entry, Vite substitutes an
empty `__vite-optional-peer-dep` stub and the build fails with
`[MISSING_EXPORT] "isUnifiedProcessor" is not exported by ...` — but only under
`npm ci`, which is why it passes locally and fails in CI.

## Layout

```
astro.config.mjs        Astro + Starlight config, driven by src/config/*.json
src/config/             Site config, sidebar, nav menu, theme colors
src/content/docs/       Documentation pages (Markdown / MDX)
src/components/         Starlight overrides + the theme's custom components
src/assets/             Images referenced by components (see the note below)
src/styles/global.css   Tailwind + theme styles
public/                 Favicons, plus CNAME for the custom domain
design/                 Source artwork kept out of the build
```

Current pages:

```
/                          Aion 2 Guides
/daevanion/boards/         Daevanion Boards
/collectibles/pets/        Pets
/collectibles/titles/      Titles
```

### Configuration

Most site-level settings live in `src/config/`, not in `astro.config.mjs`:

- `config.json` — title, description, `base_url`, logo, and the search/theme-switcher
  toggles.
- `sidebar.json` — sidebar structure. Labels support icon prefixes such as
  `[document]`, `[setting]`, `[pencil]`, or `[seti:vite]`.
- `menu.en.json` — top navigation bar. Currently empty; the topbar is just the logo,
  search, and the theme toggle.
- `theme.json` — colors, fonts, and type scale.

### Adding a page

Create a Markdown or MDX file under `src/content/docs/` with frontmatter:

```markdown
---
title: My Page
description: What this page covers
---

Content goes here.
```

Then add it to `src/config/sidebar.json`, either as an explicit `slug` entry or via an
`autogenerate` directory rule.

A top-level sidebar entry is **either** a link **or** an expandable section, never
both — Starlight renders group labels as `<summary>` elements, which cannot be links:

```jsonc
{ "label": "Home", "link": "/" }                               // clickable
{ "label": "Collectibles", "items": [ /* pages */ ] }          // section header
```

### Images

`src/components/ImageMod.astro` resolves images with a dynamic
`import.meta.glob("src/assets/*")`, so **every file in `src/assets/` is emitted into
the build whether or not a page references it**. Keep that directory to images
actually in use; put source artwork and originals in `design/` instead.

DocKit ships `image.service: noop`, which disables build-time optimization. That has
been **removed** — `sharp` was already a dependency and works, so the default service
runs and images in `src/assets/` are optimized and converted to WebP on build (the logo
drops 9 kB → 4 kB). SVGs pass through untouched rather than being rasterized.

Images under `public/` are served exactly as committed, so anything that goes there must
be sized up front. The Daevanion skill icons are the case in point: 198 sprites arrive at
256×256 (1.49 MB) and are resized to 128×128 WebP (0.62 MB) before being committed,
since they are referenced by path from client script rather than through Astro's asset
pipeline. See `src/data/README.md`.

## Deployment

`.github/workflows/deploy.yml` builds and publishes to GitHub Pages on every push to
`main` (and on manual dispatch). `public/CNAME` carries the custom domain into `dist/`.

One-time setup outside this repo:

1. **Settings → Pages → Source**: set to **GitHub Actions**.
2. **DNS**: add a `CNAME` record for `aion` pointing to `xtopolis.github.io`.
3. **Settings → Pages → Custom domain**: enter `aion.xtopolis.com`, then enable
   **Enforce HTTPS** once the certificate finishes provisioning.

## Theme

The DocKit theme source is vendored into this repo rather than consumed as a package,
which is how Themefisher distributes it. Upstream is tracked as a secondary git remote
for diffing future changes:

```bash
git remote add upstream-theme https://github.com/themefisher/dockit-astro.git
git fetch upstream-theme
```

Local changes to the theme, which will conflict with upstream updates:

- French locale removed (English only); Netlify, Cloudflare Workers and Sitepins CMS
  configs removed; deprecated `assert { type: "json" }` import assertions updated
  to `with`.
- Branding replaced throughout. `SiteTitle` renders the logo image *and* the site
  name, where upstream renders one or the other.
- Demo content and its assets deleted, along with the splash path: `Hero`, `CTA`,
  the `ctaSection` collection, and the hero/CTA background images. No page uses
  `template: splash`; Starlight's stock Hero would handle one if added.
- `Footer` and `SidebarNav` (the secondary section-tab bar) removed, with the
  `+ 110px` offsets they required dropped from `PageFrame` and `TwoColumnContent`.
- `Pagination` overridden with an empty component to disable previous/next links
  site-wide.

DocKit is MIT licensed; see `LICENSE`.

## Design notes

See [`docs/superpowers/specs/`](docs/superpowers/specs/) for the setup design document.
