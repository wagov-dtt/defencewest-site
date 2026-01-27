# ADR 002: mise for Tool Management

**Status:** Accepted | **Date:** 2026-01-27

Related: [DGOV DTT ADRs](https://adr.dtt.digital.wa.gov.au)

## Context

Project requires Hugo, Python, lychee, and superhtml. Need consistent tool versions across developers and CI.

## Decision

Use mise for version management and task orchestration:

- **Single config**: `mise.toml` defines tools and tasks
- **Polyglot**: Manages Hugo, Python, and GitHub releases natively
- **Task runner**: `mise run build`, `mise run dev`

## Consequences

**Positive:**
- One install gives access to all project tools
- CI uses same versions as local development
- Tasks documented in code

**Negative:**
- Developers must install mise
- Less familiar than Make or npm scripts
