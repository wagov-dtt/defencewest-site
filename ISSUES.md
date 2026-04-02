# Audit Issues

Date: 2026-04-02 UTC  
Git commit: `309151582599` (`main`)  
Codebase summary: Hugo static site with Python preprocessing/scraping. `sloc` scan (excluding `public/`, caches, `.venv/`) found 781 files, 3,287 code LOC, 19,043 documentation LOC, 26,618 total lines. Main code: Python 1,093 LOC, CSS 715 LOC, HTML templates 1,013 LOC, YAML 228 LOC, TOML 128 LOC, JavaScript 16 LOC.

Assessment basis:
- OWASP ASVS 5.0: https://github.com/OWASP/ASVS/releases/tag/latest
- grugbrain.dev: https://grugbrain.dev/
- Local dependency lookup: Renovate dry-run report on 2026-04-02 (`0` known vulnerability advisories; freshness/reproducibility issues noted below)

## Prioritized findings

### P1

1. Raw HTML is enabled site-wide without current evidence it is needed.
   - Location: `hugo.toml:47`; content scan found no raw HTML/script tags under `content/`
   - Category: security, complexity
   - Reference: OWASP ASVS `V1.3.5`, `V3.2.2`
   - Recommendation: Set `markup.goldmark.renderer.unsafe = false` by default. If a page truly needs raw HTML, isolate it behind a shortcode/partial or CI validation rather than enabling it globally.
   - Status: resolved 2026-04-02 — `markup.goldmark.renderer.unsafe` set to `false` in `hugo.toml`; content scan still shows no raw HTML/script tags under `content/`.

2. Map popups build HTML with string interpolation and inject it with `setHTML()`.
   - Location: `layouts/page/map.html:114-124,168`
   - Category: security
   - Reference: OWASP ASVS `V1.2.1`, `V1.2.3`, `V3.2.2`
   - Recommendation: Build popup DOM with `createElement()`/`textContent` and validate URLs before assignment. Avoid `setHTML()` for content fields such as `name`, `overview`, `slug`, and `logo_url`.
   - Status: open

3. Browser hardening headers are absent, and current inline JS makes a strong CSP harder.
   - Location: `layouts/partials/head.html`; repo search found no `Content-Security-Policy`, `Referrer-Policy`, `X-Content-Type-Options`, or similar header handling
   - Category: security
   - Reference: OWASP ASVS `V3.1.1`, `V3.4.3`
   - Recommendation: Serve behind a headers-capable front end and add CSP, `Referrer-Policy`, and `X-Content-Type-Options: nosniff`. Moving inline JS out of templates will simplify this.
   - Status: open

4. Third-party web assets are not fully pinned or integrity-checked; one is floating on `latest`.
   - Location: `layouts/partials/head.html:17`, `layouts/page/map.html:15-16`, `hugo.toml:84-87`, `CONTRIBUTING.md`
   - Category: security
   - Reference: OWASP ASVS `V15.2.4`
   - Recommendation: Stop using `lucide@latest`; pin exact versions for all CDN assets and add SRI where practical, or vendor the assets locally.
   - Status: resolved 2026-04-02 — kept CDN delivery (no vendoring), added SRI + `crossorigin` for pinned fixed-version assets in `layouts/partials/head.html` and `layouts/page/map.html`, and updated `CONTRIBUTING.md`.

5. CSV/XLSX exports do not defend against spreadsheet formula injection.
   - Location: `scripts/preprocess.py:151-180`
   - Category: security
   - Reference: OWASP ASVS `V1.2.10`
   - Recommendation: Escape cells beginning with `=`, `+`, `-`, `@`, tab, or null using a leading quote before writing CSV/XLSX.
   - Status: resolved 2026-04-02 — CSV/XLSX exports now escape string cells beginning with spreadsheet-formula prefixes before writing.

6. The scraper disables TLS certificate verification while following redirects on arbitrary company URLs.
   - Location: `scripts/scrape.py:172-195`
   - Category: security
   - Reference: OWASP ASVS `V1.3.6`, `V15.3.2`
   - Recommendation: Keep TLS verification on. If broken certificates must be tolerated, hide insecure fallback behind an explicit flag/allowlist and log it as degraded behavior.
   - Status: resolved 2026-04-02 — URL resolution now uses default TLS verification in `scripts/scrape.py`.

### P2

7. The public map payload is oversized and includes unused HTML.
   - Location: `scripts/preprocess.py:183-211`, `layouts/page/map.html:104`; generated `static/companies.json` is 1,323,567 bytes
   - Category: performance
   - Reference: grugbrain.dev (complexity and over-generalization warning)
   - Recommendation: Generate a slim map dataset containing only fields the map uses (`slug`, `name`, `overview_short`, `logo_url`, coordinates, taxonomies). Drop `content_html` from the runtime payload unless a consumer actually needs it.
   - Status: resolved 2026-04-02 — map runtime now loads slim `static/companies-map.json`; full `static/companies.json` remains available as the broader export.

8. Page logic is embedded as large inline scripts inside templates.
   - Location: `layouts/index.html:97-349`, `layouts/page/map.html:90-254`
   - Category: complexity
   - Reference: grugbrain.dev; OWASP ASVS `V3.4.3`
   - Recommendation: Move JS into versioned static files/modules. Keep templates declarative and make client logic testable and easier to secure.
   - Status: open

9. `scripts/scrape.py` is a 757-line multi-purpose script with too many responsibilities.
   - Location: `scripts/scrape.py`
   - Category: complexity
   - Reference: grugbrain.dev
   - Recommendation: Split fetch/parse/normalize/geocode/persist concerns into smaller modules and add tests for slugging, taxonomy mapping, and URL resolution.
   - Status: open

10. Build tooling uses floating `latest` versions, which reduces reproducibility and makes Renovate blind to normal updates.
   - Location: `mise.toml:3-7`; Renovate reported `skipReason: invalid-value` for these entries
   - Category: complexity, security
   - Reference: OWASP ASVS `V15.2.4`; grugbrain.dev
   - Recommendation: Pin exact versions for `uv`, `hugo`, `lychee`, `superhtml`, and `scc`, then let Renovate manage upgrades.
   - Status: resolved 2026-04-02 — pinned exact `uv`, `hugo`, `lychee`, `superhtml`, and `scc` versions in `mise.toml` using current release tags compatible with `mise`.

### P3

11. Dependency freshness is drifting even where versions are pinned.
   - Location: `.github/workflows/ci.yml:130`, `package.json`, `pnpm-lock.yaml`, `mise.toml:2`
   - Category: security, complexity
   - Reference: OWASP ASVS `V15.2.4`; local Renovate lookup `2026-04-02`
   - Recommendation: Review `actions/deploy-pages` `v4.0.5 -> v5.0.0` (major), `pa11y-ci` `4.0.1 -> 4.1.0` (lockfile/minor), and Python toolchain `3.12 -> 3.14.3`. No advisory-backed vulnerabilities were reported, but update debt exists.
   - Status: open

12. Build-time map style fetch has no explicit timeout, cache, or fallback.
   - Location: `scripts/preprocess.py:46-54`
   - Category: performance
   - Reference: OWASP ASVS `V13.1.3`
   - Recommendation: Add a short timeout, cache the style locally, and use retry/backoff or a checked-in fallback to reduce flaky builds.
   - Status: resolved 2026-04-02 — map style fetch in `scripts/preprocess.py` now uses a 10s timeout and disk cache via `scripts/config.py` cache.

## Short resolved / already-good log

- No prior `ISSUES.md` existed, so there is no carry-forward resolved list yet.
- GitHub Actions are commit-SHA pinned in `.github/workflows/ci.yml`.
- Local Renovate lookup reported no known dependency vulnerability advisories.
- Current `content/` files do not contain raw HTML/script tags; the risk is the global `unsafe = true` setting, not a presently observed content exploit.
