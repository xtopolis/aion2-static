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

## Layout

```
astro.config.mjs        Astro + Starlight config, driven by src/config/*.json
src/config/             Site config, sidebar, nav menu, social links, theme colors
src/content/docs/       Documentation pages (Markdown / MDX)
src/content/sections/   Reusable page sections (call-to-action)
src/components/         Starlight overrides + DocKit's custom components
src/styles/global.css   Tailwind + theme styles
public/                 Static assets, plus CNAME for the custom domain
```

### Configuration

Most site-level settings live in `src/config/`, not in `astro.config.mjs`:

- `config.json` — title, description, `base_url`, logo, search/theme-switcher toggles,
  footer copyright, header call-to-action button.
- `sidebar.json` — sidebar structure. Labels support icon prefixes such as
  `[document]`, `[setting]`, `[pencil]`, or `[seti:vite]`.
- `menu.en.json` — top navigation bar and footer link columns.
- `social.json` — social icons in the header.
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

Local changes to the theme so far: French locale removed (English only), Netlify and
Cloudflare Workers configs removed, Sitepins CMS markers removed, branding replaced,
and deprecated `assert { type: "json" }` import assertions updated to `with`.

DocKit is MIT licensed; see `LICENSE`.

## Design notes

See [`docs/superpowers/specs/`](docs/superpowers/specs/) for the setup design document.
