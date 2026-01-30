# ADR 003: Build-time Preprocessing

**Status:** Accepted | **Date:** 2026-01-27

Related: [DGOV DTT ADRs](https://adr.dtt.digital.wa.gov.au)

## Context

Directory has 300+ companies with search, filtering, and maps. Pre-rendering maps avoids runtime computation.

## Decision

Pre-generate static assets in Python before Hugo build:

- **`static/maps/*.png`**: Pre-rendered minimap images
- **`static/companies.json`**: Export file for submit page edit mode
- **No runtime computation**: All data ready in HTML

Note: Search text and truncated overviews are now computed inline by Hugo templates using built-in `lower` and `truncate` functions.

## Consequences

**Positive:**
- Fast page loads, works without JavaScript
- Content indexable by search engines
- Simpler client-side code

**Negative:**
- Extra build step required for maps
- Must rebuild to update map images
