# AGENTS.md

WA Defence Industry & Science Capability Directory - a static site built with Hugo + PicoCSS.

## Quick Start

```bash
mise run setup   # Install dependencies + generate computed data
mise run dev     # Start dev server (port 1313)
mise run build   # Build static site (includes link check)
```

## Project Structure

```
content/company/*.md   # Company pages (328 files)
data/
  taxonomies.yaml      # Filter categories (key -> display name)
hugo.toml              # All site config (theme, CDN URLs, map settings)
scripts/
  config.py            # Shared config, paths, constants, slug utilities
  preprocess.py        # Generates computed.yaml, maps, exports (CSV/XLSX/JSON)
  scrape.py            # Scrapes data from source website
  import_submission.py # Imports submissions from local JSON files
layouts/               # Hugo templates
layouts/partials/      # Shared components
static/logos/          # Company logos
static/icons/          # Capability stream and ownership icons
static/maps/           # Pre-rendered minimap PNGs (generated)
static/styles.css      # Custom styles (PicoCSS from CDN)
```

## Configuration

All configuration is in `hugo.toml` under `[params]`:

```toml
[params]
  picoTheme = "slate"           # Pico CSS theme
  cdnUrl = "https://cdn.jsdelivr.net/npm"
  mapStyleUrl = "https://tiles.openfreemap.org/styles/liberty"
  mapsUrl = "https://www.google.com/maps"
```

Python scripts read this config via `tomllib` in `scripts/config.py`.

## CDN Usage

All external libraries use **jsdelivr** CDN with **major version pinning**:

- `https://cdn.jsdelivr.net/npm/@picocss/pico@2/...` - CSS framework
- `https://cdn.jsdelivr.net/npm/maplibre-gl@5/...` - Map rendering
- `https://cdn.jsdelivr.net/npm/lucide@latest/...` - Icons (rendered via JS)

The submit page also uses **esm.sh** for ES modules:
- `squire-rte@2` - WYSIWYG editor
- `dompurify@3` - HTML sanitization
- `marked@17` - Markdown parser (for edit mode)

## Relative Links

Hugo is configured with `relativeURLs = true` to generate portable HTML that works from any path (GitHub Pages subfolders, IPFS, USB drives, etc.).

- **In templates**: Use `relURL` function (e.g., `{{ "styles.css" | relURL }}`)
- **At build time**: Paths are automatically converted to relative

## Data Format

Each company is a markdown file in `content/company/` with YAML frontmatter:

```yaml
---
name: Company Name
overview: Description text
website: https://example.com

# Location
address: "123 Street, Perth WA 6000"
phone: "08 1234 5678"
email: info@example.com
latitude: -31.9505
longitude: 115.8605

# Taxonomy lists (keys, not display names)
stakeholders: [defence]
capability_streams: [land, maritime]
capability_domains: [cyber]
industrial_capabilities: [steel]
regions: [perth]
ownerships: [indigenous]

# Flags
is_prime: false
is_sme: true
---
## Overview

Company description in markdown...
```

Taxonomy keys map to display names via `data/taxonomies.yaml`.

## Key Templates

- `layouts/index.html` - Directory page with filterable company cards
- `layouts/page/map.html` - MapLibre GL map (standalone iframe, uses OSM vector tiles)
- `layouts/page/submit.html` - Company submission form (Squire editor, JSON download)
- `layouts/partials/company-card.html` - Shared card component (directory + map)
- `layouts/partials/filters.html` - Shared filter sidebar
- `layouts/company/single.html` - Company detail page
- `layouts/_default/terms.html` - Taxonomy list (e.g., /regions/)
- `layouts/_default/taxonomy.html` - Term page (e.g., /regions/perth/)

## Grid System

Custom 12-column grid system in `styles.css` (uses `.row` to avoid conflict with PicoCSS `.grid`):

```html
<!-- 12-column layout -->
<div class="row">
  <aside class="col-3 col-m-4 col-s-12">Sidebar</aside>
  <main class="col-9 col-m-8 col-s-12">Content</main>
</div>

<!-- Auto-fit card grid -->
<div class="grid-auto">
  <article>Card 1</article>
  <article>Card 2</article>
</div>

<!-- PicoCSS simple grid (equal columns) -->
<div class="grid">
  <div>Column 1</div>
  <div>Column 2</div>
</div>
```

**Classes:**
- `.row` - 12-column container
- `.col-1` to `.col-12` - column spans (default/large 1024px+)
- `.col-m-1` to `.col-m-12` - medium screens (768-1023px)
- `.col-s-1` to `.col-s-12` - small screens (<768px)
- `.grid-auto` - auto-fit card grid with `--grid-min` CSS variable
- `.grid` - PicoCSS native equal-column grid

Breakpoints align with PicoCSS: 768px, 1024px (Pico also uses 576px, 1280px, 1536px for font scaling).

## Filtering

Both directory and map pages use the same filtering approach:

- **Icon filters** (Capability Streams, Ownership) - clickable icon toggles
- **Checkbox filters** (Regions, Domains, etc.) - multi-select with AND logic
- **Search** - substring matching on company name + overview
- **Filter options** - search box to filter the taxonomy lists themselves
- **URL sync** - filter state persists in URL params via `<form method="get">`

## Development Guidelines

1. **Keep it simple** - static site, minimal dependencies
2. **Use mise for everything** - all tools managed via `mise.toml` (hugo, lychee, uv, python)
3. **Test before commit** - run `mise run build`
4. **One company = one file** - easy to find, easy to edit
5. **Use conventional commits** - `feat:`, `fix:`, `chore:`
6. **Wait for user approval** before pushing or reverting changes
7. **Avoid emojis and unicode** - use ASCII only in docs and code for maximum compatibility

### Mise Usage

This project uses [mise](https://mise.jdx.dev/) to manage all tooling. **NEVER run hugo directly** - always use `mise run <task>` or `mise x -- <tool>`:

```bash
# Correct - use mise tasks
mise run dev           # Start dev server
mise run build         # Build static site
mise run preprocess    # Generate computed data
mise run maps-force    # Regenerate all minimap images
mise run htmlcheck     # Validate HTML with superhtml

# Correct - run tools via mise
mise x -- hugo version
mise x -- lychee --version

# WRONG - never run hugo directly
hugo server            # NO!
hugo --minify          # NO!
```

Tools managed by mise:
- `hugo` - Static site generator
- `lychee` - Link checker
- `superhtml` - HTML validator
- `uv` - Python package manager (for scripts)
- `python` - Python interpreter

## CI & Link Checking

The `mise run build` task runs: preprocess → hugo build → HTML check (superhtml) → link check (lychee).

- Superhtml validates HTML structure
- Lychee checks all links in the built HTML
- Add known-broken URLs to `.lycheeignore` to suppress warnings

## Scripts

### preprocess.py

Generates computed values, maps, and exports. Run automatically during build or manually:

```bash
mise run preprocess              # Update computed data
mise run maps-force              # Regenerate all minimap images
uv run python scripts/preprocess.py --dry-run  # Preview changes
```

**Generates:**
- `static/maps/*.png` - Static minimap images for companies
- `static/maps/terms/*.png` - Static map images for taxonomy terms
- `static/companies.json` - All company data for submit page
- `static/companies.csv`, `.xlsx` - Export files

Static minimaps are generated using `pymgl` with OSM Shortbread vector tiles.

### scrape.py

Re-scrapes company data from the source directory:

```bash
uv run python scripts/scrape.py           # Process cached data, resolve URLs
uv run python scripts/scrape.py --fresh   # Re-fetch from source website
```

**Features:**
- Caches HTML and images in `.cache/diskcache/` for faster re-runs
- Resolves website URLs (follows redirects)
- Geocodes addresses using ArcGIS World Geocoder
- Optimizes logos/icons with ImageMagick `mogrify`
- Cleans up markdown (normalizes lists, removes artifacts)
- Regenerates `data/taxonomies.yaml` from scraped data

### import_submission.py

Imports company submissions from local JSON files:

```bash
uv run python scripts/import_submission.py path/to/submission.json
```

**Creates/updates:**
- `content/company/{slug}.md` - Company markdown file
- `static/logos/{slug}.png` - Logo image (if included in submission)

**Features:**
- Extracts base64-encoded logo from submission JSON and saves with ImageMagick optimization
- Validates taxonomy values against `data/taxonomies.yaml`
- Detects potential duplicate companies by name similarity
- Sanitizes user input for git commit messages
- Prevents path traversal attacks using `pathvalidate` library
- Validates URLs and emails using `validators` library

### config.py

Shared configuration used by all scripts:
- Paths (COMPANY_DIR, DATA_DIR, STATIC_DIR, etc.)
- Hugo config loading from `hugo.toml`
- Taxonomy list and constants
- Slug generation utilities (`clean_slug`, `build_taxonomy_keys`) - uses `pathvalidate` for security
- Progress bar helper
- Taxonomy validation functions

**Security libraries used:**
- `pathvalidate` - Cross-platform filename/path sanitization (prevents path traversal)
- `validators` - URL and email validation
- `python-slugify` - Unicode-aware slug generation

## Submission Flow

1. User fills form at `/submit/` (or `/submit/?edit=company-slug` for edits)
2. User downloads JSON and emails to defencewest@dpc.wa.gov.au
3. Admin runs `uv run python scripts/import_submission.py submission.json`

GitHub issues with `approved` label also trigger automatic import via CI.

## Adding/Editing Companies

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
