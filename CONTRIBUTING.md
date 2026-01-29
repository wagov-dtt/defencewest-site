# Contributing

Thank you for your interest in contributing to the WA Defence Industry & Science Capability Directory.

## Quick Start

1. Install [mise](https://mise.jdx.dev/) for tool management
2. Clone the repository
3. Run `mise run setup` to install dependencies and generate computed data
4. Run `mise run dev` to start the development server at http://localhost:1313

**Important:** Always use `mise run` tasks - never run `hugo` directly! All tools are managed via mise.

## Adding or Editing Companies

### Option 1: Online Submission Form (External Companies)

1. Visit [/submit/](https://wagov-dtt.github.io/defencewest-site/submit/)
2. Fill out company details and upload logo (optional)
3. Click "Download ZIP"
4. Create a [GitHub issue](https://github.com/wagov-dtt/defencewest-site/issues/new?template=submission.md) and attach the ZIP
5. Done! Admins will process your submission automatically

**What happens next:**
- A GitHub Actions workflow imports your submission
- A pull request is created with your company data
- You'll receive a comment on the issue with the PR link
- After review, the PR is merged and your company appears on the site

### Option 2: Direct File Edit (Technical Contributors)

1. Copy `content/company/_template.md` → `content/company/your-company.md`
2. Fill in frontmatter and content
3. Add logo to `static/logos/` (optional, PNG)
4. Run `mise run build` to validate your changes
5. Submit a pull request

### Company File Format

```yaml
---
name: Company Name
overview: Brief description for cards
website: https://example.com

# Location
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

# Flags
is_prime: false
is_sme: true
---

## Overview

Extended description in Markdown...
```

## Admin Guide: Reviewing Submissions

### Understanding the Submission Workflow

When someone submits a company via the GitHub issue form:

1. **Issue created** - Title: `[Submission] Company Name`
2. **ZIP attached** - Contains `submission.json` (and `logo.png` if provided)
3. **GitHub Actions runs** - The `process-submission.yml` workflow:
   - Downloads and extracts the ZIP
   - Runs `scripts/import_submission.py`
   - Creates a PR with the company file
   - Comments on the issue with the PR link
   - Closes the issue

### Reviewing a Submission PR

When you receive a submission PR, check:

- [ ] **Company name** - Is it accurate? Check spelling, legal entity name
- [ ] **Contact information** - Email, phone, website are valid and working
- [ ] **Address & coordinates** - Does the address match the lat/long?
  - Quick check: Copy lat/long into Google Maps
  - Should be in Western Australia
- [ ] **Taxonomies** - Are the capability streams, domains, and regions correct?
  - Use the [directory page](https://wagov-dtt.github.io/defencewest-site/) with filters to see similar companies
- [ ] **Duplicate check** - Does this company already exist?
  - Search `content/company/` for similar names
  - If updating existing, verify the slug matches
- [ ] **Logo** - Is it the correct company logo?
  - Should be in `static/logos/{slug}.png`
  - Reasonable size, readable

### Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Wrong taxonomy values | Edit `content/company/{slug}.md` frontmatter, use keys from `data/taxonomies.yaml` |
| Address not in WA | If company is WA-based, correct coordinates. If not, reject (directory is WA-only) |
| Duplicate company | If updating existing, rename file to match existing slug. If truly duplicate, close PR |
| Missing logo | Optional - can proceed without. If logo was provided but not attached, ask submitter |
| Invalid website | Test the URL. If broken, ask submitter for correct URL |

### Merging a Submission PR

1. Review all checklist items above
2. Check the PR preview at `/company/{slug}/`
3. If everything looks correct: **Merge the PR**
4. The submission is now live

### Rejecting a Submission

If a submission cannot be fixed:

1. Comment on the PR explaining what needs to change
2. Close the PR without merging
3. The submitter will need to resubmit via the form

## Development Guidelines

### Code Style

- **HTML**: Use semantic elements (`<main>`, `<article>`, `<section>`, `<nav>`)
- **CSS**: Follow PicoCSS conventions, use CSS custom properties (`--pico-*`)
- **JavaScript**: Vanilla JS only, wrap in IIFE for scope isolation

### Testing & Validation

```bash
mise run build        # Full build + HTML check + link check
mise run htmlcheck    # HTML validation only
mise run linkcheck    # Link checking only
```

### Commit Messages

Use [conventional commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code restructuring
- `chore:` - Build/tooling/maintenance

Examples:
```
feat: add dark mode toggle
fix: correct filter count with search
docs: update company template
```

## Accessibility

All interactive features must be keyboard accessible:

- Use semantic HTML and ARIA attributes
- Ensure visible focus indicators
- Test with Tab, Enter, Space, Escape keys

See [ACCESSIBILITY.md](ACCESSIBILITY.md) for details.

### Testing with Lighthouse

1. Open DevTools → Lighthouse tab
2. Select "Accessibility" category
3. Click "Analyze page load"

To share failures with AI agents, copy the failure text and paste when asking for help:

```
Fix this Lighthouse accessibility issue:

[aria-hidden="true"] elements contain focusable descendants
Focusable descendants within an [aria-hidden="true"] element prevent
those interactive elements from being available to users of assistive
technologies like screen readers. Learn how [aria-hidden] affects
focusable descendants. (https://...)

Failing Elements:
div.filters-sidebar > form#filters > div.filters-scroll > section...
```

## Project Structure

```
content/
  company/*.md       # Company pages (one file per company)
data/
  taxonomies.yaml    # Filter categories and display names
  computed.yaml      # Generated: pre-computed values (gitignored)
  counts.yaml        # Generated: taxonomy counts (gitignored)
layouts/
  partials/          # Shared components
static/
  styles.css         # Custom styles (PicoCSS from CDN)
  logos/             # Company logos
  icons/             # Taxonomy icons
  maps/              # Pre-rendered minimap PNGs
scripts/             # Python preprocessing scripts
```

## Questions?

Open an issue on GitHub for questions or suggestions.
