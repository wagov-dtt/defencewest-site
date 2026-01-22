# AGENTS.md

WA Defence Industry & Science Capability Directory - a static site built with Astro + PicoCSS.

## Quick Start

```bash
mise run setup   # Install dependencies
mise run dev     # Start dev server (port 4321)
mise run build   # Build static site (includes lint + link check)
mise run lint    # Validate YAML data files only
```

## Project Structure

```
data/companies/*.yaml  # Company data (326 files)
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
- **Do NOT use** `import.meta.env.BASE_URL` - it's no longer needed

## Data Format

Each company is a single YAML file in `data/companies/`:

```yaml
name: Company Name
slug: company-name          # URL path, matches filename
overview: Description text
website: https://example.com
logo_url: /logos/company-name.png

# Contact
address: "123 Street, Perth WA"
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
```

## Development Guidelines

1. **Keep it simple** - static site, no frameworks
2. **Test before commit** - `mise run build`
3. **One company = one file** - easy to find, easy to edit
4. **Use conventional commits** - `feat:`, `fix:`, `chore:`
5. **Do not push automatically** - always let user review and explicitly request push
6. **Do not reset/revert without asking** - local uncommitted or committed changes may be intentional

## CI & Link Checking

The `mise run build` task runs: lint → build → link check (lychee).

- **Lychee** checks all links in the built HTML files
- Broken external links warn but don't fail the build (company websites change frequently)
- Add known-broken URLs to `.lycheeignore` to suppress warnings
- GitHub edit links are excluded (rate limited)

## pnpm Notes

- pnpm warns about "ignored build scripts" for esbuild/sharp - this is fine, ignore it
- Do NOT add `pnpm.onlyBuiltDependencies` to package.json - the prebuilt binaries work without running postinstall scripts

## Adding/Editing Companies

1. Edit or create `data/companies/{slug}.yaml`
2. Run `mise run lint` to validate
3. Run `mise run build` to verify
4. Commit the YAML file
