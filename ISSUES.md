# Audit Issues

Date: 2026-04-02 UTC  
Git commit: `879e95fb608b` (`main`)  
Codebase summary: Hugo static site with Python preprocessing. `sloc` scan (excluding `public/`, `.venv/`, caches, CI reports, and the temporary Renovate report) found 785 files, 2,857 code LOC, 18,889 documentation LOC, 25,811 total lines. Main code: Python 614 LOC, CSS 715 LOC, HTML templates 1,119 LOC, YAML 228 LOC, TOML 122 LOC, JavaScript 16 LOC.

Assessment basis:
- OWASP ASVS 5.0 (`latest` branch): https://github.com/OWASP/ASVS/tree/latest/5.0/en
- grugbrain.dev: https://grugbrain.dev/
- Local dependency lookup: Renovate dry-run on 2026-04-02 (`0` known vulnerability advisories; notable freshness updates: `python 3.12 -> 3.14.3`, `pa11y-ci ^4.0.0 -> 4.1.0`)

## Prioritized findings

### P1

1. Content validation is still too weak for a public, link-heavy directory.
   - Location: `scripts/validate_hugo_content.py:16-99`, `layouts/company/single.html:56-88`, `content/company/*.md`
   - Category: security, complexity
   - Reference: OWASP ASVS `V2.1.1`, `V2.2.1`, `V2.2.2`, `V3.7.2`, `V12.2.1`
   - Recommendation: Replace filename/logo-only checks with a schema validator for required fields, taxonomy keys, WA coordinate bounds, and URL/email/phone formats. Reject or normalize unsafe external values before build. At minimum, clean up the 9 `http://` company websites currently rendered as-is.
   - Status: open

2. Browser hardening is not defined here, and current inline scripts block a strong CSP.
   - Location: `layouts/_default/baseof.html:36`, `layouts/index.html:97-349`, `layouts/page/map.html:93-328`, `layouts/partials/head.html:17-44`
   - Category: security, complexity
   - Reference: OWASP ASVS `V3.1.1`, `V12.2.1`, `V14.3.2`
   - Recommendation: Move page logic into versioned static JS files, then enforce headers at the frontend/CDN: CSP, HSTS, `Referrer-Policy`, `X-Content-Type-Options: nosniff`, and anti-caching headers where needed.
   - Status: open

3. Public bulk exports widen the privacy and misuse surface without an explicit data-classification gate.
   - Location: `content/contact.md:16-20`, `scripts/preprocess.py:167-218,280-334,379-382`, public `static/companies.csv|xlsx|json`
   - Category: security
   - Reference: OWASP ASVS `V14.1.1`, `V14.2.4`, `V14.2.6`
   - Recommendation: Document which contact fields are intentionally public, strip non-essential fields from public exports, and consider separate public/internal export sets. Today the download links expose bulk email, phone, address, and rendered HTML for all 345 companies.
   - Status: open

4. Build-time outbound fetches trust a configurable URL and follow redirects without an allowlist.
   - Location: `hugo.toml:87`, `scripts/preprocess.py:42-57`
   - Category: security
   - Reference: OWASP ASVS `V13.2.4`, `V13.2.5`, `V15.3.2`
   - Recommendation: Restrict `mapStyleUrl` to an expected HTTPS host, verify the final host after redirects, or disable redirects entirely. Keep the short timeout, but fail closed if the style source changes unexpectedly.
   - Status: open

### P2

5. Core page behavior is still embedded as two large inline scripts.
   - Location: `layouts/index.html:99-349`, `layouts/page/map.html:96-328`
   - Category: complexity
   - Reference: grugbrain.dev, OWASP ASVS `V15.1.5`
   - Recommendation: Extract filter/map state into small static modules, keep templates declarative, and test the logic separately from Hugo rendering.
   - Status: open

6. The directory ships all companies in the first page load; the built home page is already large.
   - Location: `layouts/index.html:1-349`, `content/company/*.md` (345 files), built `public/index.html` (~547 KB)
   - Category: performance, complexity
   - Reference: grugbrain.dev, OWASP ASVS `V15.1.3`, `V15.2.2`
   - Recommendation: Add pagination, incremental reveal, or a slimmer initial list payload. The current static-first design is simple, but rendering every card up front does not scale gracefully.
   - Status: open

7. Derived fields are computed in multiple places, which invites drift.
   - Location: `scripts/preprocess.py`, `data/generated/companies.json`, `layouts/index.html`, `layouts/term.html`, `layouts/company/single.html`, `layouts/partials/company-card.html`, `docs/decisions/003-preprocessing.md`
   - Category: complexity
   - Reference: grugbrain.dev
   - Recommendation: Keep `search`, `overview_short`, and `logo_url` derived once during preprocessing and consumed by templates/exports.
   - Status: resolved

8. The export path still uses heavyweight table tooling for straightforward row transforms.
   - Location: `scripts/preprocess.py:19-23,229-274`, `pyproject.toml:5-15`
   - Category: complexity, performance
   - Reference: grugbrain.dev
   - Recommendation: Replace `pandas`/`openpyxl` with stdlib `csv` plus a minimal XLSX writer unless a concrete data-transformation need justifies the dependency weight and cold-start cost.
   - Status: open

9. CI reproducibility still has floating selectors and an unlocked JS install path.
   - Location: `.github/workflows/ci.yml:11,65,83-84,117,130`, `.gitignore:7`, `package.json:1-8`
   - Category: security, complexity
   - Reference: OWASP ASVS `V15.1.1`, `V15.2.1`, `V15.2.4`
   - Recommendation: Stop using `pnpm@latest`, commit a lockfile for the a11y job, and consider pinning runner selection where practical. Fold the Renovate freshness updates (`python`, `pa11y-ci`) into routine maintenance.
   - Status: open

### P3

10. `submission.json` is tracked, large, and appears unused by the app.
   - Location: previously repo root; now removed and ignored in `.gitignore`
   - Category: complexity, security
   - Reference: grugbrain.dev, OWASP ASVS `V15.2.3`
   - Recommendation: Keep orphaned submission artifacts out of the tracked tree unless they are documented, sanitised fixtures with a clear consumer.
   - Status: resolved

11. Public JSON export includes rendered HTML, which is unnecessary for many consumers and easy to misuse downstream.
   - Location: `scripts/preprocess.py:217,297`, `content/contact.md:18-20`
   - Category: security, performance
   - Reference: OWASP ASVS `V3.2.2`, `V14.2.6`, `V15.3.1`
   - Recommendation: Remove `content_html` from the public default export or split it into a separate opt-in artifact. Plain structured fields are safer and lighter for downstream reuse.
   - Status: open

## Short resolved / already-good log

- `hugo.toml:47` keeps Goldmark raw HTML disabled (`unsafe = false`).
- CDN assets are pinned and integrity-checked for the shipped third-party browser assets (`layouts/partials/head.html`, `layouts/page/map.html`).
- Map popups now build DOM nodes with `createElement()`/`textContent` and pass them to `setDOMContent()` instead of interpolating HTML (`layouts/page/map.html:133-210,242-244`).
- Map-style fetch now uses a cache plus an explicit timeout (`scripts/preprocess.py:42-57`).
- Runtime map data was slimmed to `static/companies-map.json`; the map no longer downloads the full `companies.json` export.
- CSV/XLSX exports now escape spreadsheet-formula prefixes before writing (`scripts/preprocess.py:221-245`).
- Map asset generation now uses digest-based invalidation plus orphan cleanup (`scripts/preprocess.py:61-126,391-431`).
- Core `mise.toml` tools are version-pinned; the main remaining drift is the CI-only `pnpm@latest` install path.
- Renovate local lookup reported no known dependency vulnerability advisories.
