#!/usr/bin/env python3
"""
Scraper for WA Defence Industry and Science Capability Directory.
Extracts company data and saves as Markdown files with YAML frontmatter.
"""

import asyncio
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, quote

import diskcache
import httpx
import html2text
import yaml
from selectolax.parser import HTMLParser

from taxonomy import get_short_key, build_taxonomy_keys
from slugify import slugify

# Check if mogrify (ImageMagick) is available for image optimization
HAS_MOGRIFY = shutil.which("mogrify") is not None

BASE_URL = (
    "https://www.deed.wa.gov.au/wa-defence-industry-and-science-capability-directory"
)
MAP_URL = "https://www.deed.wa.gov.au/defence-map"
DATA_DIR = Path(__file__).parent.parent / "data"
CONTENT_DIR = Path(__file__).parent.parent / "content"
CACHE_DIR = Path(__file__).parent.parent / ".cache"
STATIC_DIR = Path(__file__).parent.parent / "static"
LOGOS_DIR = STATIC_DIR / "logos"
ICONS_DIR = STATIC_DIR / "icons"

# Initialize disk cache (no expiry by default)
cache = diskcache.Cache(CACHE_DIR / "diskcache")

# HTML to markdown converter
H2T = html2text.HTML2Text()
H2T.ignore_links = True
H2T.ignore_images = True
H2T.body_width = 0

# Western Australia bounding box (approximate)
# Lat: -35.5 to -13.5, Lng: 112.5 to 129.0
WA_BOUNDS = {
    "min_lat": -35.5,
    "max_lat": -13.5,
    "min_lng": 112.5,
    "max_lng": 129.0,
}

# HTML to markdown converter
H2T = html2text.HTML2Text()
H2T.ignore_links = True
H2T.ignore_images = True
H2T.body_width = 0

REMOVE_SUFFIXES = [
    # Longer patterns first
    "-pty-ltd",
    "-pty--ltd",
    "-pty-limited",
    "-limited",
    "-pty",
    "-ltd",
    "-inc",
    "-co",
    "-australia",
    "-aus",
    "-group",
    "-services",
    "-engineering",
    "-consulting",
    "-solutions",
    "-technologies",
    "-technology",
    "-and-new-zealand",
]

# Semaphore to limit concurrent requests
MAX_CONCURRENT = 20


def is_in_wa(lat: float, lng: float) -> bool:
    """Check if coordinates are within Western Australia bounds."""
    return (
        WA_BOUNDS["min_lat"] <= lat <= WA_BOUNDS["max_lat"]
        and WA_BOUNDS["min_lng"] <= lng <= WA_BOUNDS["max_lng"]
    )


async def geocode_address(
    client: httpx.AsyncClient,
    address: str,
    semaphore: asyncio.Semaphore,
) -> tuple[float, float] | None:
    """Geocode an address using Nominatim (OpenStreetMap).

    Returns (latitude, longitude) or None if not found.
    """
    if not address:
        return None

    # Check cache first
    cache_key = f"geocode:{address}"
    if cache_key in cache:
        cached = cache[cache_key]
        if cached:
            return tuple(cached)
        return None

    async with semaphore:
        try:
            # Nominatim requires a User-Agent
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": address,
                "format": "json",
                "limit": 1,
                "countrycodes": "au",  # Restrict to Australia
            }
            headers = {
                "User-Agent": "DefenceWestDirectory/1.0 (https://github.com/defencewest)"
            }

            r = await client.get(url, params=params, headers=headers)
            r.raise_for_status()

            # Rate limit: Nominatim requires max 1 request/second
            await asyncio.sleep(1.1)

            results = r.json()
            if results:
                lat = float(results[0]["lat"])
                lng = float(results[0]["lon"])
                cache[cache_key] = [lat, lng]
                return (lat, lng)

            # Cache negative result
            cache[cache_key] = None
            return None

        except Exception as e:
            print(f"    Geocode error for '{address[:50]}...': {e}")
            return None


def clean_slug(slug: str) -> str:
    """Clean up a slug to be shorter and URL-friendly."""
    # Remove periods and normalize
    cleaned = slug.lower()
    cleaned = re.sub(r"[.\s]+", "-", cleaned)  # periods/spaces to hyphens
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)  # remove other special chars
    cleaned = re.sub(r"-+", "-", cleaned)  # collapse multiple hyphens
    cleaned = cleaned.strip("-")

    # Remove common suffixes (keep removing until none match)
    changed = True
    while changed:
        changed = False
        for suffix in REMOVE_SUFFIXES:
            if cleaned.endswith(suffix):
                remaining = cleaned[: -len(suffix)]
                # Only remove if we have at least 2 chars left
                if len(remaining) >= 2:
                    cleaned = remaining.rstrip("-")
                    changed = True
                    break

    # Truncate very long slugs
    if len(cleaned) > 30:
        parts = cleaned.split("-")
        if len(parts) > 3:
            cleaned = "-".join(parts[:3])

    return cleaned


def html_to_md(html: str) -> str:
    """Convert HTML to clean markdown."""
    if not html:
        return ""
    text = H2T.handle(html).strip()
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Fix arrow bullets (-> or –>) to proper markdown lists
    text = re.sub(r"^[\-–]>\s*", "- ", text, flags=re.MULTILINE)
    # Fix inconsistent list markers (* to -)
    text = re.sub(r"^\*\s+", "- ", text, flags=re.MULTILINE)
    # Remove trailing backslashes (HTML line break artifacts)
    text = re.sub(r"\\\s*$", "", text, flags=re.MULTILINE)
    # Clean up excessive trailing whitespace on lines
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    # Remove horizontal rules (---, ***, ___) that appear in content
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Demote headers (h1->h3, h2->h4, etc) - content shouldn't have top-level headers
    text = re.sub(r"^(#{1,2})\s", r"###", text, flags=re.MULTILINE)
    # Clean up resulting multiple newlines again
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_full_address(d: dict) -> str:
    """Combine Address, Suburb, State, Postcode into a full address string."""
    parts = []

    address = d.get("Address", "").strip()
    if address:
        parts.append(address)

    suburb = d.get("Suburb", "").strip()
    state = d.get("State", "").strip()
    postcode = d.get("Postcode", "").strip()

    # Some suburbs already include state (e.g., "Rockingham WA"), so avoid duplication
    if suburb:
        # Remove state from suburb if it's already there
        if state and suburb.endswith(f" {state}"):
            suburb = suburb[: -len(f" {state}")]

        location_parts = [suburb]
        if state:
            location_parts.append(state)
        if postcode:
            location_parts.append(postcode)

        parts.append(" ".join(location_parts))

    return ", ".join(parts)


def optimize_image(filepath: Path, resize: str = "520x120>", trim: bool = True) -> Path:
    """Optimize image with mogrify if available. Returns final path (may change extension).

    Args:
        filepath: Path to image file
        resize: ImageMagick resize geometry (default: 520x120> for logos)
        trim: Whether to trim whitespace (default: True for logos, False for icons)
    """
    if not HAS_MOGRIFY or not filepath.exists():
        return filepath

    new_path = filepath.with_suffix(".png")
    try:
        # Build mogrify command - convert to PNG, optionally trim, resize, strip metadata
        # No color adjustments to preserve original colors
        cmd = ["mogrify", "-format", "png"]
        if trim:
            cmd += ["-fuzz", "5%", "-trim", "+repage"]
        cmd += ["-resize", resize, "-strip", str(filepath)]

        subprocess.run(cmd, check=True, capture_output=True)
        # If original wasn't PNG, mogrify creates new file and keeps old one
        if filepath.suffix.lower() != ".png" and new_path.exists():
            filepath.unlink()  # Remove original
            filepath = new_path
    except subprocess.CalledProcessError as e:
        print(
            f"  Warning: mogrify failed for {filepath.name}: {e.stderr.decode()[:100]}"
        )
    return filepath


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


async def resolve_url(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> str:
    """Follow redirects and return the final URL, ignoring SSL errors."""
    if not url:
        return ""

    # Clean up malformed URLs (e.g., "https:// https://example.com")
    url = url.strip()
    url = re.sub(r"^https?://\s+", "", url)  # Remove leading "http:// " or "https:// "

    # Ensure URL has a scheme
    original_url = url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    async with semaphore:
        try:
            r = await client.head(url, follow_redirects=True)
            if r.status_code < 400:
                return str(r.url).rstrip("/")
        except Exception:
            pass

        # Return original with https if nothing worked
        if not original_url.startswith("http"):
            return f"https://{original_url.rstrip('/')}"
        return original_url.rstrip("/")


def download_image(
    client: httpx.Client,
    url: str,
    dest_dir: Path,
    filename: str,
    resize: str = "520x120>",
    trim: bool = True,
) -> tuple[str | None, bool]:
    """Download an image, optimize it, and return (local_path, was_downloaded).

    Returns tuple of (path, downloaded) where downloaded is True if freshly downloaded.
    """
    if not url:
        return None, False
    if url.startswith("/"):
        url = f"https://deed.wa.gov.au{url}"

    # Determine extension from URL
    path = urlparse(url).path.lower()
    ext = ".png"
    for e in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
        if e in path:
            ext = ".jpg" if e == ".jpeg" else e
            break

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Check if optimized PNG already exists (mogrify converts to PNG)
    png_path = dest_dir / f"{filename}.png"
    if png_path.exists():
        return f"/{dest_dir.name}/{png_path.name}", False

    # Check if file with original extension exists
    filepath = dest_dir / f"{filename}{ext}"
    if filepath.exists():
        return f"/{dest_dir.name}/{filepath.name}", False

    # Check cache for image bytes
    cache_key = f"image:{url}"
    if cache_key in cache:
        image_bytes = cache[cache_key]
    else:
        try:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
            image_bytes = r.content
            cache[cache_key] = image_bytes
        except httpx.HTTPError as e:
            print(f"  Warning: download failed for {filename}: {e}")
            return None, False

    filepath.write_bytes(image_bytes)

    # Optimize with mogrify if available (may change extension to .png)
    filepath = optimize_image(filepath, resize=resize, trim=trim)

    return f"/{dest_dir.name}/{filepath.name}", True


def extract_companies(html: str) -> list[dict]:
    """Extract company data from the embedded JSON spans."""
    tree = HTMLParser(html)
    companies = []

    for tile in tree.css("div[data-jplist-item].tile-wrapper"):
        data = {}

        name = tile.css_first(".company-name.name")
        if name:
            data["name"] = name.text(strip=True)

        json_span = tile.css_first("span[id]")
        if json_span and json_span.attributes.get("id"):
            data["slug"] = json_span.attributes["id"]
            try:
                parsed = json.loads(json_span.text())
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                data["details"] = parsed
            except json.JSONDecodeError:
                pass

        for flag, cls in [
            ("is_prime", ".filter-prime"),
            ("is_sme", ".filter-sme"),
            ("is_featured", ".filter-featured"),
        ]:
            elem = tile.css_first(cls)
            if elem:
                data[flag] = elem.text(strip=True) == "1"

        if data.get("slug"):
            companies.append(data)

    return companies


def extract_all_taxonomy_values(raw_companies: list[dict]) -> dict[str, set[str]]:
    """Extract all unique taxonomy values from raw company data.

    Returns dict of taxonomy_name -> set of display names.
    """
    values = {
        "stakeholders": set(),
        "capability_streams": set(),
        "capability_domains": set(),
        "industrial_capabilities": set(),
        "regions": set(),
    }

    for raw in raw_companies:
        d = raw.get("details", {})
        for s in d.get("WADefenceKeyStakeholders", []):
            if s.get("Title"):
                values["stakeholders"].add(s["Title"])
        for s in d.get("CapabilityStreams", []):
            if s.get("Title"):
                values["capability_streams"].add(s["Title"])
        for s in d.get("CapabilityDomains", []):
            if s.get("Title"):
                values["capability_domains"].add(s["Title"])
        for s in d.get("IndustrialCapabilities", []):
            if s.get("Title"):
                values["industrial_capabilities"].add(s["Title"])
        for s in d.get("Regions", []):
            if s.get("Title"):
                values["regions"].add(s["Title"])

    return values


def extract_stream_icons(companies: list[dict], client: httpx.Client) -> dict[str, str]:
    """Extract and download capability stream icons to /icons/streams/{key}.png.

    Returns dict of title -> key for streams that have icons.
    """
    streams_dir = ICONS_DIR / "streams"

    # Collect all stream titles with icons
    streams_with_icons = {}
    for raw in companies:
        for stream in raw.get("details", {}).get("CapabilityStreams", []):
            title = stream.get("Title")
            icon_url = stream.get("IconUrl")
            if title and icon_url and title not in streams_with_icons:
                streams_with_icons[title] = icon_url

    # Build key mapping with conflict resolution
    key_mapping = build_taxonomy_keys(list(streams_with_icons.keys()))
    # Invert: title -> key
    title_to_key = {name: key for key, name in key_mapping.items()}

    # Download icons using the resolved keys
    for title, icon_url in streams_with_icons.items():
        key = title_to_key[title]
        local_path, downloaded = download_image(
            client, icon_url, streams_dir, key, resize="72x72>", trim=False
        )
        if downloaded:
            print(f"  Downloaded stream icon: {key}")

    return title_to_key


def extract_ownership_icons(
    companies: list[dict], client: httpx.Client
) -> dict[str, str]:
    """Extract and download ownership icons to /icons/ownerships/{key}.png.

    Returns dict of title -> key for ownerships that have icons.
    """
    ownerships_dir = ICONS_DIR / "ownerships"

    # Collect all ownership titles with icons
    ownerships_with_icons = {}
    for raw in companies:
        for ownership in raw.get("details", {}).get("Ownerships", []):
            title = ownership.get("Title")
            icon_url = ownership.get("IconUrl")
            # Skip "None" ownership type
            if (
                title
                and title != "None"
                and icon_url
                and title not in ownerships_with_icons
            ):
                ownerships_with_icons[title] = icon_url

    # Build key mapping with conflict resolution
    key_mapping = build_taxonomy_keys(list(ownerships_with_icons.keys()))
    # Invert: title -> key
    title_to_key = {name: key for key, name in key_mapping.items()}

    # Download icons using the resolved keys
    for title, icon_url in ownerships_with_icons.items():
        key = title_to_key[title]
        local_path, downloaded = download_image(
            client, icon_url, ownerships_dir, key, resize="72x72>", trim=False
        )
        if downloaded:
            print(f"  Downloaded ownership icon: {key}")

    return title_to_key


def extract_coordinates(html: str) -> dict[str, tuple[float, float]]:
    """Extract company coordinates from the defence-map HTML.

    Returns dict mapping company name -> (latitude, longitude)
    """
    # Extract the jsonAddresses JSON from the page
    match = re.search(r'var jsonAddresses = JSON\.parse\("(.*?)"\);', html, re.DOTALL)
    if not match:
        print("Warning: Could not find jsonAddresses in map page")
        return {}

    try:
        # Unescape the JavaScript string
        json_str = match.group(1).encode().decode("unicode_escape")
        data = json.loads(json_str)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Warning: Failed to parse map coordinates: {e}")
        return {}

    coords = {}
    for company in data:
        name = company.get("CompanyName", "").strip()
        lat = company.get("Latitude")
        lng = company.get("Longitude")
        if name and lat and lng:
            try:
                coords[name] = (float(lat), float(lng))
            except (ValueError, TypeError):
                pass

    return coords


def normalize_company(
    raw: dict,
    client: httpx.Client,
    coords: dict[str, tuple[float, float]],
    name_to_key: dict[str, dict[str, str]],
) -> dict:
    """Normalize company data into clean YAML structure.

    Args:
        raw: Raw company data from HTML extraction
        client: HTTP client for downloading images
        coords: Company name -> (lat, lng) mapping
        name_to_key: Taxonomy name -> {display_name: short_key} mappings

    Note: slug and logo_url are NOT stored in frontmatter - they are derived:
    - slug: from the markdown filename
    - logo_url: from /logos/{slug}.png (if file exists)

    The slug is still returned in the dict for file naming purposes,
    but is removed before writing frontmatter in save_markdown().
    """
    d = raw.get("details", {})
    slug = clean_slug(raw.get("slug", ""))
    name = d.get("CompanyName", raw.get("name", "")).strip()
    website = d.get("Website", "")

    # Helper to convert display names to keys
    def to_keys(values: list[str], tax_name: str) -> list[str]:
        mapping = name_to_key.get(tax_name, {})
        return [mapping.get(v, v) for v in values if v in mapping]

    company = {
        "name": name,
        "_slug": slug,  # Internal use only, removed before saving frontmatter
        "date": "2024-01-01",  # Default date for RSS, can be updated when content changes
        "overview": html_to_md(d.get("CompanyOverviewRTF", "")),
        "website": website,
        "contact_name": d.get("ContactName", ""),
        "contact_title": d.get("Position", ""),
        "address": build_full_address(d),
        "phone": d.get("Phone", ""),
        "email": d.get("Email", ""),
        "is_prime": raw.get("is_prime", False),
        "is_sme": raw.get("is_sme", False),
        "is_featured": raw.get("is_featured", False),
        "is_indigenous_owned": any(
            o.get("Title") == "Indigenous Owned" for o in d.get("Ownerships", [])
        ),
        "is_veteran_owned": any(
            o.get("Title") == "Veteran Owned" for o in d.get("Ownerships", [])
        ),
        # Store short keys, not display names
        "stakeholders": to_keys(
            [
                s["Title"]
                for s in d.get("WADefenceKeyStakeholders", [])
                if s.get("Title")
            ],
            "stakeholders",
        ),
        "capability_streams": to_keys(
            [s["Title"] for s in d.get("CapabilityStreams", []) if s.get("Title")],
            "capability_streams",
        ),
        "capability_domains": to_keys(
            [s["Title"] for s in d.get("CapabilityDomains", []) if s.get("Title")],
            "capability_domains",
        ),
        "industrial_capabilities": to_keys(
            [s["Title"] for s in d.get("IndustrialCapabilities", []) if s.get("Title")],
            "industrial_capabilities",
        ),
        "regions": to_keys(
            [s["Title"] for s in d.get("Regions", []) if s.get("Title")],
            "regions",
        ),
    }

    # Add coordinates if available
    if name in coords:
        lat, lng = coords[name]
        company["latitude"] = lat
        company["longitude"] = lng

    # Download logo (but don't store path in frontmatter - derived from slug)
    if d.get("CompanyLogoUrl"):
        download_image(client, d["CompanyLogoUrl"], LOGOS_DIR, slug)

    # Optional markdown fields
    for field, key in [
        ("capabilities", "OrganisationUniquenessRTF"),
        ("discriminators", "DiscriminatorsRTF"),
    ]:
        val = html_to_md(d.get(key, ""))
        if val:
            company[field] = val

    # Social links
    for field, key in [
        ("linkedin", "LinkedIn"),
        ("facebook", "Facebook"),
        ("twitter", "Twitter"),
        ("youtube", "YouTube"),
    ]:
        if d.get(key):
            company[field] = d[key]

    return {k: v for k, v in company.items() if v not in (None, "", [], False)}


async def resolve_all_urls(companies: list[dict]) -> dict[str, str]:
    """Resolve all company URLs concurrently.

    Returns dict mapping slug -> resolved_url
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        verify=False,  # Ignore SSL certificate errors
    ) as client:
        tasks = []
        slugs = []

        for c in companies:
            slug = c["_slug"]
            website = c.get("website", "")

            if website:
                tasks.append(resolve_url(client, website, semaphore))
                slugs.append(slug)

        print(f"  Resolving {len(tasks)} URLs concurrently...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        url_map = {}
        for slug, result in zip(slugs, results):
            if isinstance(result, Exception):
                print(f"    {slug}: Error - {result}")
            else:
                url_map[slug] = result

        return url_map


async def geocode_companies(companies: list[dict]) -> dict[str, tuple[float, float]]:
    """Geocode addresses for companies with missing or out-of-WA coordinates.

    Returns dict mapping slug -> (latitude, longitude)
    """
    # Use a lower concurrency limit for Nominatim (rate limited)
    semaphore = asyncio.Semaphore(1)  # 1 request at a time due to rate limit

    async with httpx.AsyncClient(timeout=30) as client:
        to_geocode = []

        for c in companies:
            slug = c["_slug"]
            address = c.get("address", "")
            lat = c.get("latitude")
            lng = c.get("longitude")

            needs_geocode = False
            reason = ""

            if not lat or not lng:
                needs_geocode = True
                reason = "missing coordinates"
            elif not is_in_wa(lat, lng):
                needs_geocode = True
                reason = f"outside WA ({lat:.2f}, {lng:.2f})"

            if needs_geocode and address:
                to_geocode.append((slug, address, reason))

        if not to_geocode:
            print("  No companies need geocoding")
            return {}

        print(
            f"  Geocoding {len(to_geocode)} addresses (this may take a while due to rate limits)..."
        )

        results = {}
        for slug, address, reason in to_geocode:
            print(f"    {slug}: {reason}")
            coords = await geocode_address(client, address, semaphore)
            if coords:
                lat, lng = coords
                if is_in_wa(lat, lng):
                    results[slug] = coords
                    print(f"      -> ({lat:.4f}, {lng:.4f})")
                else:
                    print(
                        f"      -> ({lat:.4f}, {lng:.4f}) - still outside WA, skipping"
                    )
            else:
                print(f"      -> not found")

        return results


def save_yaml(data: dict, path: Path):
    """Save data as YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        )


def save_markdown(data: dict, path: Path):
    """Save company data as Markdown with YAML frontmatter.

    Extracts overview, capabilities, and discriminators into the markdown body.
    All other fields go into the YAML frontmatter.

    Note: _slug is removed before saving (it's only used for file naming).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Make a copy to avoid modifying the original
    data = dict(data)

    # Remove internal slug field (derived from filename)
    data.pop("_slug", None)

    # Extract content fields for the markdown body
    overview = data.pop("overview", "")
    capabilities = data.pop("capabilities", "")
    discriminators = data.pop("discriminators", "")

    # Build YAML frontmatter from remaining structured data
    frontmatter = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    )

    # Build markdown body
    body_parts = []
    if overview:
        body_parts.append(f"## Overview\n\n{overview.strip()}")
    if capabilities:
        body_parts.append(f"\n## Capabilities\n\n{capabilities.strip()}")
    if discriminators:
        body_parts.append(f"\n## Discriminators\n\n{discriminators.strip()}")

    body = "\n".join(body_parts)

    # Write complete markdown file
    with open(path, "w") as f:
        f.write(f"---\n{frontmatter}---\n\n{body}\n")


async def main_async():
    fresh = "--fresh" in sys.argv

    if HAS_MOGRIFY:
        print("ImageMagick detected - will optimize images")
    else:
        print("ImageMagick not found - skipping image optimization")

    with httpx.Client(timeout=60) as client:
        # Fetch directory and map HTML (cached)
        directory_html = fetch_html(client, BASE_URL, "directory_html", fresh)
        map_html = fetch_html(client, MAP_URL, "map_html", fresh)

        # Extract raw company data
        raw = extract_companies(directory_html)
        print(f"Found {len(raw)} companies")

        # Cache raw data for reprocessing
        cache["companies_raw"] = raw

        # Extract coordinates
        coords = extract_coordinates(map_html)
        print(f"Found coordinates for {len(coords)} companies")
        cache["coordinates"] = {k: list(v) for k, v in coords.items()}

        # Extract all taxonomy values first
        print("Building taxonomies...")
        all_values = extract_all_taxonomy_values(raw)

        # Build key mappings for non-icon taxonomies
        taxonomies = {
            "stakeholders": build_taxonomy_keys(list(all_values["stakeholders"])),
            "capability_domains": build_taxonomy_keys(
                list(all_values["capability_domains"])
            ),
            "industrial_capabilities": build_taxonomy_keys(
                list(all_values["industrial_capabilities"])
            ),
            "regions": build_taxonomy_keys(list(all_values["regions"])),
        }

        # Extract and download stream icons (builds keys internally)
        print("Downloading capability stream icons...")
        stream_icons = extract_stream_icons(raw, client)
        taxonomies["capability_streams"] = {
            key: name for name, key in stream_icons.items()
        }
        cache["stream_icons"] = stream_icons

        # Extract and download ownership icons (builds keys internally)
        print("Downloading ownership icons...")
        ownership_icons = extract_ownership_icons(raw, client)
        taxonomies["ownerships"] = {key: name for name, key in ownership_icons.items()}
        cache["ownership_icons"] = ownership_icons

        # Build reverse lookup: taxonomy_name -> {display_name: key}
        name_to_key = {}
        for tax_name, mapping in taxonomies.items():
            name_to_key[tax_name] = {name: key for key, name in mapping.items()}

        # Normalize companies (now with key conversion)
        print("Processing companies...")
        companies = [normalize_company(c, client, coords, name_to_key) for c in raw]
        cache["companies_normalized"] = companies

    # Resolve URLs asynchronously
    print("Resolving URLs...")
    url_map = await resolve_all_urls(companies)

    # Update companies with resolved URLs
    updated = 0
    for c in companies:
        slug = c["_slug"]
        if slug in url_map:
            resolved = url_map[slug]
            if resolved and resolved != c.get("website"):
                print(f"  {slug}: {c.get('website', '')} -> {resolved}")
                c["website"] = resolved
                updated += 1

    print(f"  Updated {updated} URLs")

    # Geocode addresses for companies with missing or out-of-WA coordinates
    print("Geocoding addresses...")
    geocoded = await geocode_companies(companies)

    # Update companies with geocoded coordinates
    geocode_updated = 0
    for c in companies:
        slug = c["_slug"]
        if slug in geocoded:
            lat, lng = geocoded[slug]
            c["latitude"] = lat
            c["longitude"] = lng
            geocode_updated += 1

    if geocode_updated:
        print(f"  Updated {geocode_updated} coordinates via geocoding")

    # Check for slug conflicts
    slugs = [c["_slug"] for c in companies]
    dupes = [s for s in set(slugs) if slugs.count(s) > 1]
    if dupes:
        print(f"WARNING: Duplicate slugs: {dupes}")

    # Save companies as markdown files
    for c in companies:
        save_markdown(c, CONTENT_DIR / "company" / f"{c['_slug']}.md")
    print(f"Saved {len(companies)} companies to content/company/")

    # Save taxonomies (already built earlier)
    save_yaml(taxonomies, DATA_DIR / "taxonomies.yaml")
    print("Saved taxonomies.yaml")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
