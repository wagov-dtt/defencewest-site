# ADR 001: PicoCSS for Styling

**Status:** Accepted | **Date:** 2026-01-27

Related: [DGOV DTT ADRs](https://adr.dtt.digital.wa.gov.au)

## Context

Need a CSS approach that styles semantic HTML with minimal custom code, supports dark/light themes, and works without a build step.

## Decision

Use PicoCSS loaded from CDN:

- **Semantic defaults**: Styles `<article>`, `<nav>`, `<button>` directly
- **Theming**: CSS custom properties (`--pico-*`) for overrides
- **No build step**: Load directly from jsdelivr CDN

## Consequences

**Positive:**
- Write semantic HTML, get accessible styling automatically
- Dark mode works via `prefers-color-scheme`
- ~10KB gzipped

**Negative:**
- Must avoid class name conflicts (PicoCSS uses `.grid`)
- Less flexible than utility frameworks
