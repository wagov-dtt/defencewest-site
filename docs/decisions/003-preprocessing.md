# ADR 003: Build-time Preprocessing

**Status:** Accepted | **Date:** 2026-01-27

Related: [DGOV DTT ADRs](https://adr.dtt.digital.wa.gov.au)

## Context

Directory has 300+ companies with search, filtering, and maps. Runtime computation would be slow and hurt accessibility.

## Decision

Pre-compute derived data in Python before Hugo build:

- **`data/computed.yaml`**: Search text, truncated overviews, filter data
- **`static/maps/*.png`**: Pre-rendered minimap images
- **No runtime computation**: All data ready in HTML

## Consequences

**Positive:**
- Fast page loads, works without JavaScript
- Content indexable by search engines
- Simpler client-side code

**Negative:**
- Extra build step required
- Must rebuild to update computed data
