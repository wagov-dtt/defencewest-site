# WA Defence Industry Directory

Static site for the WA Defence Industry and Science Capability Directory.

## Quick Start

```bash
mise run setup   # Install dependencies
mise run dev     # Dev server at localhost:4321
mise run build   # Build to dist/
mise run lint    # Validate data
```

## Admin Mode

Add `?admin=1` to the URL (or visit `/admin`) to enable admin mode:
- Shows edit buttons on company cards
- Adds "Add Company" button in sidebar

The editor at `/admin/company-slug` lets you:
1. Edit YAML in browser with validation
2. Copy YAML to clipboard
3. Open the file directly on GitHub

**Note:** Changes must be committed to GitHub - the editor is read-only preview.

## Adding a New Company

1. Go to `/admin` and click "Add Company"
2. Fill in the YAML (slug must be unique, lowercase with hyphens)
3. Copy YAML and create file on GitHub at `data/companies/slug.yaml`
4. Add logo to `public/logos/slug.png` (or .jpg)
5. Commit and deploy

## Updating Taxonomies

Taxonomy values in `data/taxonomies.yaml` must exist before companies can use them.

**To add a new capability stream with icon:**
1. Add entry to `capability_streams` in `data/taxonomies.yaml`:
   ```yaml
   capability_streams:
     New Stream Name: /icons/new-stream.jpg
   ```
2. Add the icon file to `public/icons/`
3. Commit and deploy
4. Now companies can use the new stream value

**Why this order matters:** The build validates company YAML against taxonomies. If a company references a taxonomy value that doesn't exist, the build fails. Link checking (`mise run links`) also verifies icon files exist.

## Editing Companies

Each company is a YAML file in `data/companies/`. Example:

```yaml
name: Austal
slug: austal                    # Must match filename
overview: |
  Company description here...
website: www.austal.com
logo_url: /logos/austal.png

# Contact
contact_name: John Smith
phone: +61 8 9410 1111
email: info@austal.com
address: 100 Clarence Beach Road, Henderson WA

# Map location
latitude: -32.1456
longitude: 115.7675

# Type
is_prime: true
is_sme: false

# Categories (values must exist in taxonomies.yaml)
stakeholders:
  - Defence Industry
capability_streams:
  - Maritime and Sub-Sea Forces
capability_domains:
  - Submarines
industrial_capabilities:
  - Steel Fabrication
regions:
  - Perth Metropolitan
```

## Project Structure

```
data/
  companies/        # 326 company YAML files
  taxonomies.yaml   # Valid filter values
src/pages/
  index.astro       # Directory + map view
  company/[slug].astro
  admin/            # Admin editor
public/
  logos/            # Company logos
  icons/            # Capability stream icons
scripts/
  scrape.py         # Data scraper
  lint.py           # YAML validator
```

## Scraping Data

```bash
mise run scrape          # Use cached HTML
mise run scrape --fresh  # Fetch fresh data
```

Scrapes company details, coordinates, logos, and icons from the source site.

## Tech

Astro + PicoCSS + MapLibre GL JS. Data in YAML. Tools: mise, pnpm, uv.
