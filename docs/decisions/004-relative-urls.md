# ADR 004: Relative URLs

**Status:** Accepted | **Date:** 2026-01-27

Related: [DGOV DTT ADRs](https://adr.dtt.digital.wa.gov.au)

## Context

Site may deploy to domain root (`username.github.io`) or subdirectory (`username.github.io/repo-name/`). Absolute URLs break in subdirectories.

## Decision

Configure Hugo with `relativeURLs = true`:

- **Templates**: Use `{{ "styles.css" | relURL }}`
- **Output**: Paths like `../../styles.css` instead of `/styles.css`

## Consequences

**Positive:**
- Works at root or in subdirectory without config changes
- Local development works without server

**Negative:**
- Relative paths less readable in source
- Must use `relURL` function consistently
