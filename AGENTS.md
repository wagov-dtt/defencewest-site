# AGENTS.md

WA Defence Industry & Science Capability Directory - a static site built with Astro + PicoCSS.

## Quick Start

```bash
mise run setup   # Install dependencies
mise run dev     # Start dev server (port 4321)
mise run build   # Build static site (includes link check)
mise run format  # Format Astro/TS/CSS with Prettier
mise run check   # Type check Astro files
```

## Project Structure

```
data/companies/*.yaml  # Company data (327 files)
data/taxonomies.yaml   # Filter categories
src/pages/             # Astro pages
src/components/        # Astro components
public/logos/          # Company logos
public/styles.css      # Custom styles (PicoCSS from CDN)
```

## Relative Links

The site uses `astro-relative-links` to generate portable HTML that works from any path (GitHub Pages subfolders, IPFS, USB drives, etc.).

- **In source code**: Use absolute paths starting with `/` (e.g., `/company/austal`, `/contact`)
- **At build time**: Paths are automatically converted to relative (e.g., `../../contact`)

## Data Format

Each company is a single YAML file in `data/companies/`:

```yaml
name: Company Name
slug: company-name # URL path, matches filename
overview: Description text
website: https://example.com
logo_url: /logos/company-name.png

# Contact
address: "123 Street, Perth WA 6000"
phone: "08 1234 5678"
email: info@example.com

# Taxonomy lists
stakeholders: [Defence Industry]
capability_streams: [Land Forces, Maritime]
capability_domains: [Cyber Security]
industrial_capabilities: [Steel Fabrication]
regions: [Perth Metropolitan]

# Flags
is_prime: false
is_sme: true
is_indigenous_owned: false
is_veteran_owned: false
```

## Validation

Data validation happens at build time via Astro content collections:

- **Schema validation** - Zod schema in `src/content.config.ts` validates field types and catches unknown fields
- **Taxonomy validation** - `src/pages/companies.csv.ts` validates taxonomy values against `data/taxonomies.yaml`

Build will fail if validation errors are found.

## Development Guidelines

1. **Keep it simple** - static site, minimal dependencies
2. **Test before commit** - run `mise run build`
3. **One company = one file** - easy to find, easy to edit
4. **Use conventional commits** - `feat:`, `fix:`, `chore:`
5. **Wait for user approval** before pushing or reverting changes

## CI & Link Checking

The `mise run build` task runs: build → link check (lychee).

- Lychee checks all links in the built HTML
- Add known-broken URLs to `.lycheeignore` to suppress warnings
- Ignore pnpm warnings about "ignored build scripts" for esbuild/sharp (prebuilt binaries work fine)

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
- Optimizes images with ImageMagick if available
- Cleans up markdown (normalizes lists, removes artifacts)
