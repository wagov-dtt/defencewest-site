# WA Defence Industry Directory

[![CI](https://github.com/wagov-dtt/defencewest-site/actions/workflows/ci.yml/badge.svg)](https://github.com/wagov-dtt/defencewest-site/actions/workflows/ci.yml)

Static site for the WA Defence Industry and Science Capability Directory.

## Quick Start

```bash
mise run setup   # Install dependencies
mise run dev     # Dev server at localhost:4321
mise run build   # Build to dist/
```

## Adding/Editing Companies

Every company page has an **"Edit this listing"** link. Use [/edit/new](https://wagov-dtt.github.io/defencewest-site/edit/new) to add a new company.

The editor validates your YAML and shows valid taxonomy options. Submit changes via GitHub or email to defencewest@dpc.wa.gov.au.

## Project Structure

```
data/companies/*.yaml   # Company data
data/taxonomies.yaml    # Filter categories
public/logos/           # Company logos
public/icons/           # Capability stream icons
```

## Logo Processing

To batch-process logos and icons (trim whitespace, resize, strip metadata):

```bash
mogrify -trim -fuzz 1% -resize 400x400\> -strip public/logos/*.png
mogrify -trim -fuzz 1% -resize 400x400\> -strip public/logos/*.jpg
mogrify -colorspace sRGB -strip public/icons/*.jpg
```

Icon colors are adjusted via CSS filters in `public/styles.css`.

Requires [ImageMagick](https://imagemagick.org/) (`apt install imagemagick` or `brew install imagemagick`).

## Tech

[Astro](https://astro.build), [PicoCSS](https://picocss.com), [MapLibre GL JS](https://maplibre.org), [uFuzzy](https://github.com/leeoniya/uFuzzy). Tools: [mise](https://mise.jdx.dev), [pnpm](https://pnpm.io), [uv](https://docs.astral.sh/uv/).

~1,750 lines of code: TypeScript 434, Python 588, CSS 330, Markdown 91. Estimated ~$49k / 4 months ([scc](https://github.com/boyter/scc)).

## AI-Assisted Development

This website was developed with assistance from [OpenCode](https://github.com/wagov-dtt/tutorials-and-workshops/blob/main/README.md#opencode-ai-agent), in accordance with [ADR 011: AI Tool Governance](https://adr.dtt.digital.wa.gov.au/security/011-ai-governance.html).
