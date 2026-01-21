# AGENTS.md

WA Defence Industry & Science Capability Directory - a static site built with Astro + PicoCSS.

## Quick Start

```bash
mise run setup   # Install dependencies
mise run dev     # Start dev server (port 4321)
mise run build   # Build static site
mise run lint    # Validate YAML data files
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
2. **Test before commit** - `mise run ci`
3. **One company = one file** - easy to find, easy to edit
4. **Use conventional commits** - `feat:`, `fix:`, `chore:`
5. **Do not push automatically** - always let user review and explicitly request push
6. **Do not reset/revert without asking** - local uncommitted or committed changes may be intentional

## pnpm Notes

- pnpm warns about "ignored build scripts" for esbuild/sharp - this is fine, ignore it
- Do NOT add `pnpm.onlyBuiltDependencies` to package.json - the prebuilt binaries work without running postinstall scripts

## Adding/Editing Companies

1. Edit or create `data/companies/{slug}.yaml`
2. Run `mise run lint` to validate
3. Run `mise run build` to verify
4. Commit the YAML file
