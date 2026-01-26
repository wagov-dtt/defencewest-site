#!/usr/bin/env python3
"""
Scraper for WA Defence Industry and Science Capability Directory.
Extracts company data and saves as Markdown files with YAML frontmatter.
"""

import concurrent.futures
import json
import re
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import yaml
from geopy.geocoders import Nominatim
from markdownify import markdownify as md
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from selectolax.parser import HTMLParser
from unidecode import unidecode

from config import (
    params,
    CONTENT_DIR,
    DATA_DIR,
    ICONS_DIR,
    LOGOS_DIR,
    WA_BOUNDS,
    HAS_MOGRIFY,
    cache,
    USER_AGENT,
    TAXONOMIES,
    build_taxonomy_keys,
    clean_slug,
)

# URLs from hugo.toml
BASE_URL = params["scrapeBaseUrl"]

# Initialize Nominatim geolocator for geocoding
geolocator = Nominatim(user_agent=USER_AGENT, timeout=30)


def is_in_wa(lat: float, lng: float) -> bool:
    """Check if coordinates are within Western Australia bounds."""
    return (
        WA_BOUNDS["miny"] <= lat <= WA_BOUNDS["maxy"]
        and WA_BOUNDS["minx"] <= lng <= WA_BOUNDS["maxx"]
    )


def simplify_address(address: str) -> str:
    """Simplify address for better geocoding by removing building names, levels, etc."""
    # Split by comma and filter out parts that are likely building/floor info
    parts = [p.strip() for p in address.split(",")]
    skip_patterns = [
        r"^(Level|Floor|Suite|Unit|Shop|Tower)\s*\d*",  # Level 17, Suite 5, etc.
        r"^(Building|Plaza|Centre|Center|House|Exchange)\b",  # Building names
        r"^PO\s*Box\b",  # PO Boxes
    ]

    filtered = []
    for part in parts:
        # Skip parts matching building/floor patterns
        if any(re.match(p, part, re.IGNORECASE) for p in skip_patterns):
            continue
        # Remove leading unit numbers like "17/123" from street addresses
        part = re.sub(r"^\d+[a-z]?/", "", part)
        filtered.append(part)

    return ", ".join(filtered) if filtered else address


def geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode an address using Nominatim. Returns (lat, lng) or None.

    Tries the full address first, then a simplified version if that fails.
    """
    if not address:
        return None

    cache_key = f"geocode:{address}"
    if cache_key in cache:
        cached = cache[cache_key]
        return tuple(cached) if cached else None

    def try_geocode(addr: str) -> tuple[float, float] | None:
        try:
            location = geolocator.geocode(addr, country_codes="au", exactly_one=True)
            time.sleep(1.1)  # Rate limit: max 1 request/second
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            print(f"    Geocode error for '{addr[:50]}...': {e}")
        return None

    # Try full address first
    if result := try_geocode(address):
        cache[cache_key] = list(result)
        return result

    # Try simplified address (remove building names, levels, etc.)
    simplified = simplify_address(address)
    if simplified != address:
        if result := try_geocode(simplified):
            cache[cache_key] = list(result)
            return result

    cache[cache_key] = None
    return None


def normalize_text(text: str) -> str:
    """Normalize unicode characters to ASCII equivalents."""
    if not text:
        return ""
    # Convert bullets to dash before unidecode (which would make them *)
    text = re.sub(r"[•·→]", "-", text)
    # Normalize unicode to ASCII (smart quotes, dashes, ligatures, etc.)
    return unidecode(text)


def html_to_md(html: str) -> str:
    """Convert HTML to clean markdown."""
    if not html:
        return ""
    text = md(html, heading_style="ATX", bullets="-", strip=["a", "img"])
    text = normalize_text(text)

    # Normalize bullet-like patterns to markdown list items
    text = re.sub(r"^[\-\*]+\s*", "- ", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)  # Collapse multiple newlines
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)  # Trim trailing whitespace
    return text.strip()


def build_full_address(d: dict) -> str:
    """Combine Address, Suburb, State, Postcode into full address string."""
    parts = []
    if addr := d.get("Address", "").strip():
        parts.append(addr)

    suburb = d.get("Suburb", "").strip()
    state = d.get("State", "").strip()
    postcode = d.get("Postcode", "").strip()

    # Skip state if suburb already ends with it (e.g., "Rockingham WA" + "WA")
    if suburb and state and suburb.upper().endswith(state.upper()):
        state = ""

    location = " ".join(filter(None, [suburb, state, postcode]))
    if location:
        parts.append(location)

    return ", ".join(parts)


def resolve_url(url: str) -> str:
    """Follow redirects and return final URL."""
    if not url:
        return ""

    url = url.strip()
    url = re.sub(r"^https?://\s+", "", url)  # Clean malformed URLs

    original_url = url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        with httpx.Client(timeout=3, verify=False, follow_redirects=True) as client:
            r = client.head(url)
            if r.status_code < 400:
                return str(r.url).rstrip("/")
    except Exception:
        pass

    return (
        f"https://{original_url.rstrip('/')}"
        if not original_url.startswith("http")
        else original_url.rstrip("/")
    )


def resolve_all_urls(companies: list[dict]) -> dict[str, str]:
    """Resolve all company URLs concurrently. Returns slug -> resolved_url mapping."""
    to_resolve = [
        (c["_slug"], c.get("website", "")) for c in companies if c.get("website")
    ]
    if not to_resolve:
        return {}

    url_map = {}
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task(
            f"Resolving {len(to_resolve)} URLs...", total=len(to_resolve)
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(resolve_url, url): slug for slug, url in to_resolve
            }
            for future in concurrent.futures.as_completed(futures):
                slug = futures[future]
                try:
                    if resolved := future.result():
                        url_map[slug] = resolved
                except Exception:
                    pass
                progress.update(task, advance=1)

    return url_map


def download_image(
    client: httpx.Client,
    url: str,
    dest_dir: Path,
    filename: str,
    resize: str = "520x120>",
) -> bool:
    """Download and optimize an image.

    Skips if file already exists - to re-download, manually delete the file first.
    Returns True if freshly downloaded.

    Args:
        resize: ImageMagick resize geometry (default for logos, use "72x72>" for icons)
    """
    if not url:
        return False

    output_path = dest_dir / filename
    if output_path.exists():
        return False

    try:
        r = client.get(url, timeout=30)
        r.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(r.content)

        if HAS_MOGRIFY:
            try:
                subprocess.run(
                    [
                        "mogrify",
                        "-format",
                        "PNG",
                        "-resize",
                        resize,
                        "-trim",
                        str(output_path),
                    ],
                    check=True,
                    capture_output=True,
                )
            except Exception:
                pass
        return True
    except Exception:
        return False


def fetch_html(
    client: httpx.Client, url: str, cache_key: str, fresh: bool = False
) -> str:
    """Fetch HTML from URL, using cache unless fresh=True."""
    if not fresh and cache_key in cache:
        print(f"Using cached {cache_key}")
        return cache[cache_key]

    print(f"Fetching {url}...")
    html = client.get(url).text
    cache[cache_key] = html
    return html


def extract_companies(html: str) -> list[dict]:
    """Extract company data from directory HTML."""
    parser = HTMLParser(html)
    companies = []

    for tile in parser.css(".tile"):
        hidden_span = tile.css_first('span[style*="display:none"]')
        if not hidden_span:
            continue

        json_text = hidden_span.text().strip()
        if not json_text:
            continue

        try:
            data = json.loads(json.loads(json_text))
        except json.JSONDecodeError:
            continue

        company = {
            "_slug": hidden_span.attrs.get("id")
            or clean_slug(data.get("CompanyName", "unknown")),
            "name": data.get("CompanyName", ""),
            "overview": data.get("CompanyOverviewRTF", ""),
            "capabilities": data.get("OrganisationUniquenessRTF", ""),
            "discriminators": data.get("DiscriminatorsRTF", ""),
            "short_intro": data.get("CompanyShortIntro", ""),
            "website": data.get("Website", ""),
            "companyLogoUrl": data.get("CompanyLogoUrl", ""),
            "Address": data.get("Address", ""),
            "Suburb": data.get("Suburb", ""),
            "State": data.get("State", ""),
            "Postcode": data.get("Postcode", ""),
            "Phone": data.get("Phone", ""),
            "Email": data.get("Email", ""),
            "ContactName": data.get("ContactName", ""),
            "Position": data.get("Position", ""),
            "Latitude": data.get("Latitude"),
            "Longitude": data.get("Longitude"),
            "stakeholders": [
                s.get("Title", "") for s in data.get("WADefenceKeyStakeholders", [])
            ],
            "capability_streams": [
                s.get("Title", "") for s in data.get("CapabilityStreams", [])
            ],
            "_stream_icons": {
                s.get("Title", ""): s.get("IconUrl", "")
                for s in data.get("CapabilityStreams", [])
                if s.get("Title") and s.get("IconUrl")
            },
            "capability_domains": [
                d.get("Title", "") for d in data.get("CapabilityDomains", [])
            ],
            "industrial_capabilities": [
                i.get("Title", "") for i in data.get("IndustrialCapabilities", [])
            ],
            "regions": [r.get("Title", "") for r in data.get("Regions", [])],
        }

        # Ownership (skip "None")
        if ownerships := data.get("Ownerships", []):
            if (title := ownerships[0].get("Title", "")) and title.lower() != "none":
                company["ownerships"] = [title]
                if icon_url := ownerships[0].get("IconUrl"):
                    company["_ownership_icons"] = {title: icon_url}

        # SME/Prime flags (1=true, 2=false)
        if (sme := tile.css_first(".filter-sme")) and sme.text() == "1":
            company["is_sme"] = True
        if (prime := tile.css_first(".filter-prime")) and prime.text() == "1":
            company["is_prime"] = True

        companies.append(company)

    return companies


def extract_all_taxonomy_values(companies: list[dict]) -> dict[str, set[str]]:
    """Extract all unique taxonomy values from companies."""
    all_values = {tax: set() for tax in TAXONOMIES}

    for c in companies:
        for tax in all_values:
            if values := c.get(tax, []):
                all_values[tax].update(v for v in values if v)

    return all_values


def collect_icons(companies: list[dict]) -> dict[str, dict[str, str]]:
    """Collect all unique icon URLs from companies.

    Returns dict with 'streams' and 'ownerships' keys, each mapping
    display name -> icon URL.
    """
    streams: dict[str, str] = {}
    ownerships: dict[str, str] = {}

    for c in companies:
        if icons := c.get("_stream_icons"):
            streams.update(icons)
        if icons := c.get("_ownership_icons"):
            ownerships.update(icons)

    return {"streams": streams, "ownerships": ownerships}


def download_icons(
    client: httpx.Client,
    icons: dict[str, dict[str, str]],
    name_to_key: dict[str, dict[str, str]],
) -> None:
    """Download taxonomy icons to static/icons/.

    Skips existing files - to re-download, manually delete the icon file first.
    """
    base_url = params["scrapeBaseUrl"].rsplit("/", 1)[0]

    for category, icon_map in icons.items():
        # Map category to taxonomy name for key lookup
        tax_name = "capability_streams" if category == "streams" else "ownerships"
        key_map = name_to_key.get(tax_name, {})

        dest_dir = ICONS_DIR / category
        dest_dir.mkdir(parents=True, exist_ok=True)

        for display_name, url in icon_map.items():
            key = key_map.get(display_name)
            if not key:
                continue

            # Make URL absolute if relative
            if url.startswith("/"):
                url = base_url + url

            download_image(client, url, dest_dir, f"{key}.png", resize="72x72>")


def normalize_company(
    d: dict, client: httpx.Client, name_to_key: dict[str, dict[str, str]]
) -> dict:
    """Normalize raw company data into final format."""
    slug = clean_slug(d.get("name", "")) or d.get("_slug", "unknown")

    company = {
        "_slug": slug,
        "name": normalize_text(d.get("name", "")),
        "date": (date.today() - timedelta(days=365)).isoformat(),
    }

    # Optional fields (normalize text fields for unicode cleanup)
    if v := d.get("short_intro"):
        company["overview"] = normalize_text(v)
    if v := d.get("website"):
        company["website"] = v
    if v := d.get("ContactName"):
        company["contact_name"] = normalize_text(v)
    if v := d.get("Position"):
        company["contact_title"] = normalize_text(v)
    if v := build_full_address(d):
        company["address"] = normalize_text(v)
    if v := d.get("Phone", "").strip():
        company["phone"] = v
    if v := d.get("Email", "").strip():
        company["email"] = v
    if d.get("is_sme"):
        company["is_sme"] = True
    if d.get("is_prime"):
        company["is_prime"] = True

    # Taxonomies (convert display names to keys)
    for tax in [
        "stakeholders",
        "capability_streams",
        "capability_domains",
        "industrial_capabilities",
        "regions",
    ]:
        if values := d.get(tax, []):
            if keys := [
                name_to_key.get(tax, {}).get(v)
                for v in values
                if name_to_key.get(tax, {}).get(v)
            ]:
                company[tax] = keys

    # Ownership
    if ownerships := d.get("ownerships", []):
        if key := name_to_key.get("ownerships", {}).get(ownerships[0]):
            company["ownerships"] = [key]

    # Coordinates
    if (lat := d.get("Latitude")) and (lng := d.get("Longitude")):
        try:
            lat_f, lng_f = float(lat), float(lng)
            if is_in_wa(lat_f, lng_f):
                company["latitude"] = lat_f
                company["longitude"] = lng_f
        except (ValueError, TypeError):
            pass

    # Download logo
    if logo_url := d.get("companyLogoUrl"):
        download_image(client, logo_url, LOGOS_DIR, f"{slug}.png")

    # Content fields for markdown body
    if v := d.get("overview"):
        company["overview_full"] = html_to_md(v)
    if v := d.get("capabilities"):
        company["capabilities"] = html_to_md(v)
    if v := d.get("discriminators"):
        company["discriminators"] = html_to_md(v)

    return company


def geocode_companies(companies: list[dict]) -> dict[str, tuple[float, float]]:
    """Geocode addresses for companies with missing/invalid coordinates."""
    to_geocode = []
    for c in companies:
        lat, lng = c.get("latitude"), c.get("longitude")
        if (not lat or not lng or not is_in_wa(lat, lng)) and (
            addr := c.get("address")
        ):
            to_geocode.append((c["_slug"], addr))

    if not to_geocode:
        print("  No companies need geocoding")
        return {}

    results = {}
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task(
            f"Geocoding {len(to_geocode)} addresses...", total=len(to_geocode)
        )
        for slug, address in to_geocode:
            progress.update(task, description=f"Geocoding {slug[:30]}...")
            if coords := geocode_address(address):
                if is_in_wa(*coords):
                    results[slug] = coords
            progress.update(task, advance=1)

    return results


def save_markdown(data: dict, path: Path):
    """Save company data as Markdown with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(data)
    data.pop("_slug", None)

    # Extract content for markdown body
    overview_full = data.pop("overview_full", "")
    capabilities = data.pop("capabilities", "")
    discriminators = data.pop("discriminators", "")

    frontmatter = yaml.dump(
        data, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000
    )

    body_parts = []
    if overview_full:
        body_parts.append(f"## Overview\n\n{overview_full.strip()}")
    if capabilities:
        body_parts.append(f"\n## Capabilities\n\n{capabilities.strip()}")
    if discriminators:
        body_parts.append(f"\n## Discriminators\n\n{discriminators.strip()}")

    with open(path, "w") as f:
        f.write(f"---\n{frontmatter}---\n\n{''.join(body_parts)}\n")


def main():
    fresh = "--fresh" in sys.argv

    print(
        "ImageMagick detected - will optimize images"
        if HAS_MOGRIFY
        else "ImageMagick not found - skipping image optimization"
    )

    with httpx.Client(timeout=60) as client:
        html = fetch_html(client, BASE_URL, "directory_html", fresh)
        raw = extract_companies(html)
        print(
            f"Found {len(raw)} companies ({sum(1 for c in raw if c.get('Latitude'))} with coordinates)"
        )

        # Build taxonomies
        print("Building taxonomies...")
        all_values = extract_all_taxonomy_values(raw)
        taxonomies = {
            tax: build_taxonomy_keys(list(all_values[tax])) for tax in all_values
        }

        # Build reverse lookup: {taxonomy: {display_name: key}}
        name_to_key = {
            tax: {name: key for key, name in mapping.items()}
            for tax, mapping in taxonomies.items()
        }

        # Download icons (skips existing files)
        print("Downloading icons...")
        icons = collect_icons(raw)
        download_icons(client, icons, name_to_key)

        # Normalize companies
        print("Processing companies...")
        companies = [normalize_company(c, client, name_to_key) for c in raw]

    # Resolve URLs
    print("Resolving URLs...")
    url_map = resolve_all_urls(companies)
    updated = 0
    for c in companies:
        if (resolved := url_map.get(c["_slug"])) and resolved != c.get("website"):
            print(f"  {c['_slug']}: {c.get('website', '')} -> {resolved}")
            c["website"] = resolved
            updated += 1
    print(f"  Updated {updated} URLs")

    # Geocode missing coordinates
    print("Geocoding addresses...")
    company_by_slug = {c["_slug"]: c for c in companies}
    for slug, (lat, lng) in geocode_companies(companies).items():
        if slug in company_by_slug:
            company_by_slug[slug]["latitude"] = lat
            company_by_slug[slug]["longitude"] = lng

    # Check for duplicates
    slugs = [c["_slug"] for c in companies]
    if dupes := [s for s in set(slugs) if slugs.count(s) > 1]:
        print(f"WARNING: Duplicate slugs: {dupes}")

    # Save files
    for c in companies:
        save_markdown(c, CONTENT_DIR / "company" / f"{c['_slug']}.md")
    print(f"Saved {len(companies)} companies to content/company/")

    yaml_path = DATA_DIR / "taxonomies.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, "w") as f:
        yaml.dump(
            taxonomies,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        )
    print("Saved taxonomies.yaml")


if __name__ == "__main__":
    main()
