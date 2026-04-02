# ADR 003: Build-time Preprocessing

**Status:** Accepted | **Date:** 2026-01-27

Related: [DGOV DTT ADRs](https://adr.dtt.digital.wa.gov.au)

## Context

Directory has 300+ companies with search, filtering, and maps. Pre-rendering maps avoids runtime computation.

## Decision

Pre-generate static assets in Python before Hugo build:

- **`static/maps/*.png`**: Pre-rendered minimap images
- **`static/maps/*.sha256`**: Digests used for content-based map regeneration
- **`static/maps/terms/*.png`**: Pre-rendered term map images
- **`static/maps/terms/*.sha256`**: Digests used for term-map regeneration
- **`static/companies.json`**: Full export file for data access
- **`static/companies-map.json`**: Slim runtime payload for the interactive map
- **No runtime computation**: All data ready in HTML

Note: Search text, truncated overviews, and logo URLs are computed once during preprocessing and reused by Hugo templates and public exports.

## Consequences

**Positive:**
- Fast page loads, works without JavaScript
- Content indexable by search engines
- Simpler client-side code

**Negative:**
- Extra build step required for maps
- Must rebuild to update map images, though unchanged map inputs now stay cached and stale map outputs are cleaned up automatically
