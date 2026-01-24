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
  taxonomies.yaml      # Filter categories + icons
  companies/*.yaml     # Original scraped data (reference)
  computed.yaml        # Generated: pre-computed values (gitignored)
  counts.yaml          # Generated: taxonomy counts (gitignored)
hugo.toml              # All site config (theme, CDN URLs, map settings)
scripts/
  preprocess.py        # Generates computed.yaml + static map images
  scrape.py            # Scrapes data from source website
  export.py            # Exports to CSV/XLSX
  taxonomy.py          # Taxonomy key/name utilities
layouts/               # Hugo templates
layouts/partials/      # Shared components
static/logos/          # Company logos
static/icons/          # Capability stream icons
static/maps/           # Pre-rendered minimap PNGs (generated)
static/styles.css      # Custom styles (PicoCSS from CDN)
```

## Configuration

All configuration is in `hugo.toml` under `[params]`:

```toml
[params]
  picoTheme = "slate"           # Pico CSS theme
  cdnUrl = "https://cdn.jsdelivr.net/npm"
  mapStyleUrl = "https://vector.openstreetmap.org/styles/shortbread/colorful.json"
  mapTilesUrl = "https://vector.openstreetmap.org/shortbread_v1/{z}/{x}/{y}.mvt"
  mapsUrl = "https://www.google.com/maps"
```

Python scripts read this config via `tomllib`.

## CDN Usage

All external libraries use **jsdelivr** CDN with **major version pinning**:

- `https://cdn.jsdelivr.net/npm/@picocss/pico@2/...` - CSS framework
- `https://cdn.jsdelivr.net/npm/maplibre-gl@5/...` - Map rendering

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
stakeholders: [industry]
capability_streams: [land, maritime]
capability_domains: [cyber]
industrial_capabilities: [fabrication]
regions: [perth]

# Flags
is_prime: false
is_sme: true
is_indigenous_owned: false
is_veteran_owned: false
---
## Overview

Company description in markdown...
```

Taxonomy keys map to display names via `data/taxonomies.yaml`.

## Key Templates

- `layouts/index.html` - Directory page with filterable company cards
- `layouts/page/map.html` - MapLibre GL map (standalone iframe, uses OSM vector tiles)
- `layouts/partials/company-card.html` - Shared card component (directory + map)
- `layouts/partials/filters.html` - Shared filter sidebar
- `layouts/company/single.html` - Company detail page

## Filtering

Both directory and map pages use the same filtering approach:

- **Boolean filters** (Prime, SME, Indigenous, Veteran) - multi-select
- **Multi-select filters** (Regions, Domains, etc.) - JavaScript with AND logic
- **Search** - substring matching on company name + overview
- **Filter options** - filters the taxonomy dropdowns themselves
- **URL sync** - filter state persists in URL params via `<form method="get">`

## Development Guidelines

1. **Keep it simple** - static site, minimal dependencies
2. **Use mise for everything** - all tools managed via `mise.toml` (hugo, lychee, uv, python)
3. **Test before commit** - run `mise run build`
4. **One company = one file** - easy to find, easy to edit
5. **Use conventional commits** - `feat:`, `fix:`, `chore:`
6. **Wait for user approval** before pushing or reverting changes

### Mise Usage

This project uses [mise](https://mise.jdx.dev/) to manage all tooling. Always use `mise run <task>` or `mise x -- <tool>` rather than calling tools directly:

```bash
mise run dev           # NOT: hugo server
mise run build         # NOT: hugo --minify
mise run maps-force    # Regenerate all minimap images
```

## CI & Link Checking

The `mise run build` task runs: preprocess → export → hugo build → link check (lychee).

- Lychee checks all links in the built HTML
- Add known-broken URLs to `.lycheeignore` to suppress warnings

## Preprocessing

The `scripts/preprocess.py` script generates computed values and static map images. Run automatically during build or manually:

```bash
mise run preprocess              # Update computed data
mise run maps-force              # Regenerate all minimap images
uv run python scripts/preprocess.py --dry-run  # Preview changes
```

Pre-computed fields (stored in `data/computed.yaml`, not in source markdown):

- `overview_short` - First 300 chars for card display
- `search_text` - Lowercase name + overview for filtering
- `filter_data` - Pre-slugified taxonomy values

Static minimaps (`static/maps/*.png`) are generated using `pymgl` with OSM Shortbread vector tiles from the CDN (no local tile server needed).

Also generates `data/counts.yaml` with taxonomy value counts.

## Adding/Editing Companies

See [README.md](README.md#addingediting-companies) for details.

## Scraping

To re-scrape company data from the source directory:

```bash
uv run python scripts/scrape.py           # Process cached data, resolve URLs
uv run python scripts/scrape.py --fresh   # Re-fetch from source website
```

The scraper:

- Caches HTML and images in `data/cache/diskcache/` for faster re-runs
- Resolves website URLs (follows redirects)
- Optimizes logos/icons with ImageMagick `mogrify` (fuzzy trim, resize, convert to PNG, strip metadata)
- Cleans up markdown (normalizes lists, removes artifacts)
