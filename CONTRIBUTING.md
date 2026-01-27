# Contributing

Thank you for your interest in contributing to the WA Defence Industry & Science Capability Directory.

## Quick Start

1. Install [mise](https://mise.jdx.dev/) for tool management
2. Clone the repository
3. Run `mise run setup` to install dependencies and generate computed data
4. Run `mise run dev` to start the development server at http://localhost:1313

## Adding or Editing a Company

1. Copy `content/company/_template.md` to `content/company/company-name.md`
2. Fill in the YAML frontmatter fields (see template for guidance)
3. Add company logo to `static/logos/` (optional, PNG format recommended)
4. Run `mise run build` to validate your changes

### Company File Format

```yaml
---
name: Company Name
overview: Brief description (used in cards)
website: https://example.com

# Location
address: "123 Street, Perth WA 6000"
phone: "08 1234 5678"
email: info@example.com
latitude: -31.9505
longitude: 115.8605

# Taxonomy (use keys from data/taxonomies.yaml)
stakeholders: [industry]
capability_streams: [land, maritime]
capability_domains: [cyber]
industrial_capabilities: [fabrication]
regions: [perth]
---

## Overview

Extended description in Markdown...
```

## Development Guidelines

### Code Style

- **HTML**: Use semantic elements (`<main>`, `<article>`, `<section>`, `<nav>`)
- **CSS**: Follow PicoCSS conventions, use CSS custom properties (`--pico-*`)
- **JavaScript**: Vanilla JS only, no frameworks; wrap in IIFE for scope isolation

### Accessibility

All interactive features should be keyboard accessible. When adding new components:

- Ensure focusable elements have visible focus indicators
- Use ARIA attributes where semantic HTML isn't sufficient
- Test with keyboard navigation (Tab, Enter, Space, Escape)
- Consider screen reader announcements for dynamic updates

See [ACCESSIBILITY.md](ACCESSIBILITY.md) for details.

### Running Tests

```bash
mise run build        # Full build with HTML and link validation
mise run htmlcheck    # HTML validation only (superhtml)
mise run linkcheck    # Link checking only (lychee)
```

### Accessibility Testing

For local accessibility testing, use Chrome/Edge DevTools Lighthouse:

1. Open DevTools (F12) → Lighthouse tab
2. Select "Accessibility" category
3. Click "Analyze page load"

To share Lighthouse failures with an AI agent for fixes:

1. Run the audit and expand any failed items
2. Click the "Copy" icon next to the failure, or select the text and copy
3. Paste the failure details when asking for help, e.g.:

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

### Commit Messages

Use [conventional commits](https://www.conventionalcommits.org/):

- `feat:` New feature or capability
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style (formatting, not CSS)
- `refactor:` Code restructuring without behavior change
- `chore:` Build, tooling, or maintenance tasks

Examples:
```
feat: add dark mode toggle to settings
fix: correct filter count when using search
docs: update company template with new fields
```

## Project Structure

```
content/company/*.md   # Company pages (one file per company)
data/
  taxonomies.yaml      # Filter categories and display names
  computed.yaml        # Generated: pre-computed values (gitignored)
layouts/               # Hugo templates
  partials/            # Shared components
static/
  styles.css           # Custom styles (PicoCSS from CDN)
  logos/               # Company logos
  icons/               # Taxonomy icons
scripts/               # Python preprocessing scripts
```

## Questions?

Open an issue on GitHub for questions or suggestions.
