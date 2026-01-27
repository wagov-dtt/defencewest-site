# WA Defence Industry Directory

[![CI](https://github.com/wagov-dtt/defencewest-site/actions/workflows/ci.yml/badge.svg)](https://github.com/wagov-dtt/defencewest-site/actions/workflows/ci.yml)

Static site for the WA Defence Industry and Science Capability Directory.

## Quick Start

```bash
mise run setup   # Install dependencies + generate computed data
mise run dev     # Dev server at localhost:1313
mise run build   # Build to public/
```

## Adding/Editing Companies

Every company page has an **"Edit this listing"** link. The editor lets you:

- Edit overview and capabilities markdown with live preview
- Modify contact details and taxonomy selections
- Copy the generated markdown or download as `.md` file
- Link directly to edit on GitHub

Submit changes via GitHub PR or email to defencewest@dpc.wa.gov.au.

## Project Structure

```
content/company/*.md   # Company pages (328 markdown files)
data/
  taxonomies.yaml      # Filter categories + icons
  companies/*.yaml     # Original scraped data (reference)
  computed.yaml        # Generated: pre-computed values (gitignored)
  counts.yaml          # Generated: taxonomy counts (gitignored)
hugo.toml              # All site config (theme, CDN URLs, map settings)
static/logos/          # Company logos
static/icons/          # Capability stream icons
static/maps/           # Pre-rendered minimap PNGs
```

## Logo Processing

Logos are automatically processed by the scraper (`scripts/scrape.py`) using ImageMagick `mogrify`:

- Fuzzy trim (5% fuzz to handle near-white backgrounds)
- Resize to max 520x120 (2x retina for card display)
- Convert to PNG and strip metadata

To manually reprocess all logos:

```bash
rm -f static/logos/*.png
uv run python scripts/scrape.py  # Uses cached images, reprocesses with mogrify
```

Requires [ImageMagick](https://imagemagick.org/) (`apt install imagemagick` or `brew install imagemagick`).

## Tech

[Hugo](https://gohugo.io), [PicoCSS](https://picocss.com), [MapLibre GL JS](https://maplibre.org). Tools: [mise](https://mise.jdx.dev), [uv](https://docs.astral.sh/uv/).

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [ACCESSIBILITY.md](ACCESSIBILITY.md) - Accessibility statement and testing approach
- [AGENTS.md](AGENTS.md) - AI agent development guide
- [docs/decisions/](docs/decisions/) - Architecture Decision Records

## Maps

The map implementation uses:

- **[OSM Shortbread Vector Tiles](https://vector.openstreetmap.org/)** - free, public vector tiles from OpenStreetMap
- **[MapLibre GL JS](https://maplibre.org)** - vector map rendering with globe projection
- **Static minimaps** - pre-rendered PNG images for company cards (generated via `pymgl` using the same OSM tiles)

All map configuration (style URL, tile URL) is in `hugo.toml` under `[params]`.

## AI-Assisted Development

This website was developed with assistance from [OpenCode](https://github.com/anomalyco/opencode), in accordance with [ADR 011: AI Tool Governance](https://adr.dtt.digital.wa.gov.au/security/011-ai-governance.html).
