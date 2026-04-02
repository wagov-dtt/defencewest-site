# Contributing

This guide covers both human contributors and AI assistants working on the WA Defence Industry & Science Capability Directory.

## Quick Start

1. Install [mise](https://mise.jdx.dev/)
2. Clone the repo
3. Run `mise run setup` to install dependencies and generate computed data
4. Run `mise run dev` to start the dev server on `localhost:1313`
5. Run `mise run build` before submitting changes

```bash
mise run setup
mise run dev
mise run build
```

## Project Overview

This is a static site built with Hugo + PicoCSS.

### Project Structure

```text
content/company/*.md   Company pages
content/company/_template.md

data/
  taxonomies.yaml      Filter categories (key -> display name)

hugo.toml              Site config, CDN URLs, map settings

scripts/
  config.py            Shared config, paths, constants, slug utilities
  preprocess.py        Generates maps and export files
  scrape.py            Scrapes data from the source website

layouts/               Hugo templates
layouts/partials/      Shared components
static/logos/          Company logos
static/icons/          Capability stream and ownership icons
static/maps/           Pre-rendered minimap PNGs (generated)
static/styles.css      Custom styles
```

## Configuration

All site configuration lives in `hugo.toml` under `[params]`.

```toml
[params]
  picoTheme = "slate"
  cdnUrl = "https://cdn.jsdelivr.net/npm"
  mapStyleUrl = "https://tiles.openfreemap.org/styles/liberty"
  mapsUrl = "https://www.google.com/maps"
```

Python scripts read this via `tomllib` in `scripts/config.py`.

## CDN Usage

External libraries use jsDelivr with exact version pinning. Fixed assets should use SRI.

- PicoCSS: `@picocss/pico@2.1.1`
- MapLibre GL JS: `maplibre-gl@5.21.1`
- Lucide: `lucide@1.7.0`

## Relative Links

Hugo is configured with `relativeURLs = true` so the built site works from subfolders and other non-root paths.

- In templates, use `relURL`
- Build output paths are converted to relative links automatically

## Adding and Editing Companies

### Direct Edit

1. Copy `content/company/_template.md` to `content/company/your-company.md`
2. Edit frontmatter and content
3. Add a logo to `static/logos/your-company.png` if needed
4. Run `mise run build`
5. Submit a PR

### Company File Format

Each company is a markdown file in `content/company/` with YAML frontmatter.

```yaml
---
name: Company Name
overview: Short summary for directory cards (max 500 chars)
website: https://example.com

address: "123 Street, Perth WA 6000"
phone: "08 1234 5678"
email: info@example.com
latitude: -31.9505
longitude: 115.8605

# Taxonomies (use keys from data/taxonomies.yaml)
stakeholders: [defence]
capability_streams: [land, maritime]
capability_domains: [cyber]
industrial_capabilities: [steel]
regions: [perth]
ownerships: [indigenous]
company_types: [sme]
---

## Overview

Company description in Markdown...
```

Taxonomy keys map to display names via `data/taxonomies.yaml`.

## Templates and Pages

Key templates:

- `layouts/index.html` - directory page with filterable company cards
- `layouts/page/map.html` - standalone map iframe using MapLibre GL
- `layouts/partials/company-card.html` - shared company card component
- `layouts/partials/filters.html` - shared filter sidebar
- `layouts/company/single.html` - company detail page
- `layouts/_default/terms.html` - taxonomy list pages
- `layouts/_default/taxonomy.html` - taxonomy term pages

## Layout and Filtering

### Grid System

The site uses a custom PicoCSS build with 12-column grid support.

```html
<div class="grid">
  <aside class="col-3 col-md-4">Sidebar</aside>
  <main class="col-9 col-md-8">Content</main>
</div>
```

Classes:

- `.grid` - grid container
- `.col-1` to `.col-12` - default column spans
- `.col-md-1` to `.col-md-12` - medium-screen spans

### Filtering

Directory and map pages share the same filtering model:

- icon filters for capability streams and ownership
- checkbox filters for regions, domains, and other taxonomies
- substring search on company name and overview
- filter-option search within taxonomy lists
- URL-synced filter state via `GET` params

## Development Workflow

### Commands

- `mise run dev` - start dev server
- `mise run build` - full build with validation
- `mise run preprocess` - regenerate maps and export files
- `mise run htmlcheck` - validate generated HTML

### Conventions

- Keep it simple
- One company = one file
- Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`
- Test before commit with `mise run build`
- Wait for user approval before pushing or reverting changes
- Avoid emojis and non-ASCII characters in docs and code

## AI Agents

AI assistants should follow the same development workflow as human contributors and should prefer small, maintainable changes grounded in the existing repo structure and tooling.

## Tooling

### Mise Usage

Use mise for project tools. Do not run Hugo directly.

```bash
# Correct
mise run dev
mise run build
mise run preprocess
mise run htmlcheck
mise x -- hugo version
mise x -- lychee --version

# Wrong
hugo server
hugo --minify
```

Tools managed by mise:

- `hugo`
- `lychee`
- `superhtml`
- `uv`
- `python`

### Python Scripts with uv

Use `uv run` for Python scripts.

```bash
# Correct
uv run python scripts/preprocess.py
uv run python scripts/scrape.py
uv run python scripts/import_submission.py path/to/submission.json

# Wrong
python scripts/preprocess.py
python3 scripts/scrape.py
```

`uv` manages the virtual environment and dependencies defined in `pyproject.toml`.

### System Dependencies

Map rendering via [`mlnative`](https://pypi.org/project/mlnative/) requires system packages. CI installs these automatically via `mise run setup-ci`.

Linux (Ubuntu/Debian):

```bash
sudo apt-get install -y \
  mesa-vulkan-drivers \
  libcurl4 \
  libglfw3 \
  libuv1 \
  zlib1g
```

macOS:

```bash
brew install molten-vk curl glfw libuv zlib
```

Requirements:

- Vulkan graphics support
- `libcurl`
- `glfw`
- `libuv`
- `zlib`
- network access to `tiles.openfreemap.org`

## CI and Validation

`mise run build` runs preprocess -> Hugo build -> HTML validation -> link check.

- `superhtml` validates HTML structure
- `lychee` checks links in built output
- add known broken URLs to `.lycheeignore` when needed

## Scripts

### preprocess.py

Generates maps and export files.

```bash
mise run preprocess
```

Outputs include:

- `static/maps/*.png`
- `static/maps/terms/*.png`
- `static/companies.json`
- `static/companies-map.json`
- `static/*.csv`
- `static/*.xlsx`

### scrape.py

Re-scrapes company data from the source directory.

```bash
uv run python scripts/scrape.py
uv run python scripts/scrape.py --fresh
```

Features:

- caches HTML and images in `.cache/diskcache/`
- resolves website URLs
- geocodes addresses
- optimizes logos and icons
- cleans markdown
- regenerates `data/taxonomies.yaml`

### config.py

Shared configuration for scripts, including:

- project paths
- Hugo config loading
- taxonomy constants
- slug generation utilities
- progress helpers
- taxonomy validation helpers

Security-related libraries used here include `pathvalidate`, `validators`, and `python-slugify`.

## Accessibility

See [ACCESSIBILITY.md](ACCESSIBILITY.md).
