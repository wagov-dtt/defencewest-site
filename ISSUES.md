# Audit Issues

Date: 2026-04-02 UTC  
Git commit: `309151582599` (`main`)  
Codebase summary: Hugo static site with Python preprocessing. `sloc` scan (excluding `public/`, caches, `.venv/`) found 780 files, 2,760 code LOC, 18,889 documentation LOC, 25,683 total lines. Main code: Python 568 LOC, CSS 715 LOC, HTML templates 1,017 LOC, YAML 228 LOC, TOML 122 LOC, JavaScript 16 LOC.

Assessment basis:
- OWASP ASVS 5.0 (Bleeding Edge, release `latest`, published 2026-03-17): https://github.com/OWASP/ASVS/tree/latest/5.0/en
- grugbrain.dev: https://grugbrain.dev/
- Local dependency lookup: Renovate dry-run report on 2026-04-02 (`0` known vulnerability advisories; freshness and pinning issues noted below)

## Prioritized findings

### P1


1. Browser hardening headers are not defined here, and current inline JS makes a strict CSP harder.
   - Location: `layouts/partials/head.html`; inline JS in `layouts/index.html:97-349` and `layouts/page/map.html:94-258`
   - Category: security, complexity
   - Reference: OWASP ASVS `V3.1.1`
   - Recommendation: Serve behind a headers-capable frontend/CDN and add CSP, `Referrer-Policy`, `X-Content-Type-Options: nosniff`, and HSTS. Moving inline JS out of templates is the prerequisite for a strong nonce-free CSP.
   - Status: open

2. Build-time validation is too narrow for a public content repo.
   - Location: `scripts/validate_hugo_content.py`; external link rendering in `layouts/company/single.html:56-88`
   - Category: security, complexity
   - Reference: OWASP ASVS `V2.1.1`, `V2.2.1`, `V2.2.2`, `V3.7.2`
   - Recommendation: Extend validation beyond filename/logo checks to enforce a schema and allowlists for `website`, `email`, `phone`, coordinates, required fields, and taxonomy keys. Reject non-HTTP(S) external links before build.
   - Status: open


### P2

3. Page behavior is still embedded as large inline template scripts.
   - Location: `layouts/index.html:97-349`, `layouts/page/map.html:94-258`
   - Category: complexity
   - Reference: grugbrain.dev; OWASP ASVS `V3.1.1`
   - Recommendation: Move JS into versioned static modules, keep templates declarative, and test filter/map logic separately from HTML rendering.
   - Status: open



4. CI and toolchain reproducibility still has floating pieces and update debt.
   - Location: `.github/workflows/ci.yml:8,58,74,109,130`, `package.json`, `mise.toml`
   - Category: security, complexity
   - Reference: OWASP ASVS `V15.1.1`, `V15.2.1`, `V15.2.4`
   - Recommendation: Review Renovate findings (`actions/deploy-pages v4.0.5 -> v5.0.0`, `pa11y-ci 4.0.1 -> 4.1.0` lockfile, `python 3.12 -> 3.14.3`) and pin remaining floating CI selectors such as `pnpm@latest` and `ubuntu-latest` where practical.
   - Status: open

### P3

5. The export path uses heavyweight table tooling for a small, fixed dataset.
   - Location: `scripts/preprocess.py:15-23,164-207`; `pyproject.toml`
   - Category: complexity, performance
   - Reference: grugbrain.dev
   - Recommendation: Replace `pandas`-centric export code with stdlib `csv` plus a minimal XLSX writer unless there is a concrete transformation need that justifies the dependency and startup cost.
   - Status: open

## Short resolved / already-good log

- Map asset generation now uses content-based invalidation plus orphan cleanup; `uv run python scripts/preprocess.py` removed 9 stale company-map files and 1 stale term-map file while rewriting current outputs with `.sha256` sidecars.
- Map popups now build DOM nodes with `createElement()`/`textContent` and pass them to `setDOMContent()` instead of interpolating content into `setHTML()`.

- `hugo.toml:47` keeps Goldmark raw HTML disabled (`unsafe = false`).
- CDN assets are pinned and integrity-checked; `lucide@latest` is gone.
- CSV/XLSX exports now escape spreadsheet-formula prefixes before writing.
- Runtime map data was slimmed to `static/companies-map.json`; the map no longer downloads the full `companies.json` export.
- Map-style fetch now uses a cache plus an explicit timeout.
- Core `mise.toml` tool entries are version-pinned instead of floating `latest`.
- Renovate local lookup reported no known dependency vulnerability advisories.
