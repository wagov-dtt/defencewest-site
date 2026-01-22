#!/usr/bin/env python3
"""
Scraper for WA Defence Industry and Science Capability Directory.
Extracts company data and saves as YAML files.
"""

import asyncio
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import diskcache
import httpx
import html2text
import yaml
from selectolax.parser import HTMLParser

# Check if mogrify (ImageMagick) is available for image optimization
HAS_MOGRIFY = shutil.which("mogrify") is not None

BASE_URL = (
    "https://www.deed.wa.gov.au/wa-defence-industry-and-science-capability-directory"
)
MAP_URL = "https://www.deed.wa.gov.au/defence-map"
DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR = DATA_DIR / "cache"
LOGOS_DIR = Path(__file__).parent.parent / "public" / "logos"
ICONS_DIR = Path(__file__).parent.parent / "public" / "icons"

# Initialize disk cache (no expiry by default)
cache = diskcache.Cache(CACHE_DIR / "diskcache")

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


def optimize_image(filepath: Path) -> Path:
    """Optimize image with mogrify if available. Returns final path (may change extension)."""
    if not HAS_MOGRIFY or not filepath.exists():
        return filepath

    try:
        # Convert to PNG and optimize (strip metadata, reasonable quality)
        # This handles various input formats and normalizes to PNG
        new_path = filepath.with_suffix(".png")
        subprocess.run(
            [
                "mogrify",
                "-format",
                "png",
                "-strip",  # Remove metadata
                "-resize",
                "400x400>",  # Resize if larger than 400x400, keep aspect
                str(filepath),
            ],
            check=True,
            capture_output=True,
        )
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
    client: httpx.Client, url: str, dest_dir: Path, filename: str
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
    filepath = optimize_image(filepath)

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


def extract_stream_icons(companies: list[dict], client: httpx.Client) -> dict[str, str]:
    """Extract and download capability stream icons, return title->icon_url mapping."""
    stream_icons = {}

    for raw in companies:
        for stream in raw.get("details", {}).get("CapabilityStreams", []):
            title = stream.get("Title")
            icon_url = stream.get("IconUrl")
            if title and icon_url and title not in stream_icons:
                # Create slug from title for filename
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                local_path, downloaded = download_image(
                    client, icon_url, ICONS_DIR, slug
                )
                if local_path:
                    stream_icons[title] = local_path
                    if downloaded:
                        print(f"  Downloaded icon: {title}")

    return stream_icons


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
) -> dict:
    """Normalize company data into clean YAML structure."""
    d = raw.get("details", {})
    slug = clean_slug(raw.get("slug", ""))
    name = d.get("CompanyName", raw.get("name", "")).strip()
    website = d.get("Website", "")

    company = {
        "name": name,
        "slug": slug,
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
        "stakeholders": [
            s["Title"] for s in d.get("WADefenceKeyStakeholders", []) if s.get("Title")
        ],
        "capability_streams": [
            s["Title"] for s in d.get("CapabilityStreams", []) if s.get("Title")
        ],
        "capability_domains": [
            s["Title"] for s in d.get("CapabilityDomains", []) if s.get("Title")
        ],
        "industrial_capabilities": [
            s["Title"] for s in d.get("IndustrialCapabilities", []) if s.get("Title")
        ],
        "regions": [s["Title"] for s in d.get("Regions", []) if s.get("Title")],
    }

    # Add coordinates if available
    if name in coords:
        lat, lng = coords[name]
        company["latitude"] = lat
        company["longitude"] = lng

    # Logo
    if d.get("CompanyLogoUrl"):
        logo, _ = download_image(client, d["CompanyLogoUrl"], LOGOS_DIR, slug)
        if logo:
            company["logo_url"] = logo

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
            slug = c["slug"]
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

        # Extract and download stream icons
        print("Downloading capability stream icons...")
        stream_icons = extract_stream_icons(raw, client)
        cache["stream_icons"] = stream_icons

        # Normalize companies
        print("Processing companies...")
        companies = [normalize_company(c, client, coords) for c in raw]
        cache["companies_normalized"] = companies

    # Resolve URLs asynchronously
    print("Resolving URLs...")
    url_map = await resolve_all_urls(companies)

    # Update companies with resolved URLs
    updated = 0
    for c in companies:
        slug = c["slug"]
        if slug in url_map:
            resolved = url_map[slug]
            if resolved and resolved != c.get("website"):
                print(f"  {slug}: {c.get('website', '')} -> {resolved}")
                c["website"] = resolved
                updated += 1

    print(f"  Updated {updated} URLs")

    # Check for slug conflicts
    slugs = [c["slug"] for c in companies]
    dupes = [s for s in set(slugs) if slugs.count(s) > 1]
    if dupes:
        print(f"WARNING: Duplicate slugs: {dupes}")

    # Save companies
    for c in companies:
        save_yaml(c, DATA_DIR / "companies" / f"{c['slug']}.yaml")
    print(f"Saved {len(companies)} companies")

    # Save taxonomies with stream icons
    taxonomies = {
        "stakeholders": sorted(
            {v for c in companies for v in c.get("stakeholders", [])}
        ),
        "capability_streams": {
            title: stream_icons.get(title, "")
            for title in sorted(
                {v for c in companies for v in c.get("capability_streams", [])}
            )
        },
        "capability_domains": sorted(
            {v for c in companies for v in c.get("capability_domains", [])}
        ),
        "industrial_capabilities": sorted(
            {v for c in companies for v in c.get("industrial_capabilities", [])}
        ),
        "regions": sorted({v for c in companies for v in c.get("regions", [])}),
    }
    save_yaml(taxonomies, DATA_DIR / "taxonomies.yaml")
    print("Saved taxonomies.yaml")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
