# Contributing

## Quick Start

1. Install [mise](https://mise.jdx.dev/)
2. Clone the repo
3. `mise run setup` - install dependencies
4. `mise run dev` - start dev server at localhost:1313

## Adding Companies

### Option 1: Submission Form

1. Visit [/submit/](https://wagov-dtt.github.io/defencewest-site/submit/)
2. Fill out details and upload logo
3. Download JSON and email to defencewest@dpc.wa.gov.au

### Option 2: Direct Edit

1. Copy `content/company/_template.md` to `content/company/your-company.md`
2. Edit frontmatter and content
3. Add logo to `static/logos/your-company.png` (optional)
4. `mise run build` to validate
5. Submit PR

## Company File Format

```yaml
---
name: Company Name
website: https://example.com
address: "123 Street, Perth WA 6000"
phone: "08 1234 5678"
email: info@example.com
latitude: -31.9505
longitude: 115.8605

# Taxonomies (use keys from data/taxonomies.yaml)
capability_streams: [land, maritime]
capability_domains: [cyber]
industrial_capabilities: [steel]
regions: [perth]
ownerships: [indigenous]
stakeholders: [defence]

is_sme: true
is_prime: false
---

## Overview

Company description in Markdown...
```

## Development

### Commands

- `mise run dev` - dev server
- `mise run build` - full build with validation
- `mise run preprocess` - regenerate computed data

### Commits

Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`

## Accessibility

See [ACCESSIBILITY.md](ACCESSIBILITY.md).
