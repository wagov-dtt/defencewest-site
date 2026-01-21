#!/usr/bin/env python3
"""
Scraper for WA Defence Industry and Science Capability Directory.
Extracts company data and saves as YAML files.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
import html2text
import yaml
from selectolax.parser import HTMLParser

BASE_URL = (
    "https://www.deed.wa.gov.au/wa-defence-industry-and-science-capability-directory"
)
MAP_URL = "https://www.deed.wa.gov.au/defence-map"
DATA_DIR = Path(__file__).parent.parent / "data"
LOGOS_DIR = Path(__file__).parent.parent / "public" / "logos"
ICONS_DIR = Path(__file__).parent.parent / "public" / "icons"

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
    return re.sub(r"\n{3,}", "\n\n", text)


def resolve_url(url: str) -> str:
    """Follow redirects and return the final URL, ignoring SSL errors."""
    if not url:
        return ""

    # Ensure URL has a scheme
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        # Use a separate client with SSL verification disabled
        with httpx.Client(
            timeout=10,
            follow_redirects=True,
            verify=False,  # Ignore SSL certificate errors
        ) as client:
            r = client.head(url, follow_redirects=True)
            final_url = str(r.url)
            # Remove trailing slashes for consistency
            return final_url.rstrip("/")
    except Exception:
        # If we can't resolve, return the original with https
        return url.rstrip("/")


def download_image(
    client: httpx.Client, url: str, dest_dir: Path, filename: str
) -> str | None:
    """Download an image and return the local path."""
    if not url:
        return None
    if url.startswith("/"):
        url = f"https://deed.wa.gov.au{url}"

    try:
        r = client.get(url, follow_redirects=True)
        r.raise_for_status()

        path = urlparse(url).path.lower()
        ext = ".png"
        for e in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
            if e in path:
                ext = ".jpg" if e == ".jpeg" else e
                break

        dest_dir.mkdir(parents=True, exist_ok=True)
        filepath = dest_dir / f"{filename}{ext}"
        filepath.write_bytes(r.content)
        return f"/{dest_dir.name}/{filename}{ext}"
    except httpx.HTTPError as e:
        print(f"  Warning: download failed for {filename}: {e}")
        return None


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
                local_path = download_image(client, icon_url, ICONS_DIR, slug)
                if local_path:
                    stream_icons[title] = local_path
                    print(f"  Downloaded icon: {title}")

    return stream_icons


def fetch_coordinates(
    client: httpx.Client, fresh: bool = False
) -> dict[str, tuple[float, float]]:
    """Fetch company coordinates from the defence-map page.

    Returns dict mapping company name -> (latitude, longitude)
    """
    cache_file = DATA_DIR / "cache" / "map.html"

    if cache_file.exists() and not fresh:
        print(f"Using cached map HTML from {cache_file}")
        html = cache_file.read_text()
    else:
        print(f"Fetching {MAP_URL}...")
        html = client.get(MAP_URL).text
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(html)

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

    print(f"Found coordinates for {len(coords)} companies")
    return coords


def normalize_company(
    raw: dict,
    client: httpx.Client,
    coords: dict[str, tuple[float, float]],
    resolve_urls: bool = False,
) -> dict:
    """Normalize company data into clean YAML structure."""
    d = raw.get("details", {})
    slug = clean_slug(raw.get("slug", ""))
    name = d.get("CompanyName", raw.get("name", "")).strip()

    # Optionally resolve website URL to follow redirects
    website = d.get("Website", "")
    if website and resolve_urls:
        resolved = resolve_url(website)
        if resolved != website:
            print(f"  {slug}: {website} -> {resolved}")
        website = resolved

    company = {
        "name": name,
        "slug": slug,
        "overview": html_to_md(d.get("CompanyOverviewRTF", "")),
        "website": website,
        "contact_name": d.get("ContactName", ""),
        "contact_title": d.get("Position", ""),
        "address": d.get("Address", ""),
        "phone": d.get("Phone", ""),
        "email": d.get("Email", ""),
        "is_prime": raw.get("is_prime", False),
        "is_sme": raw.get("is_sme", False),
        "is_featured": raw.get("is_featured", False),
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
        logo = download_image(client, d["CompanyLogoUrl"], LOGOS_DIR, slug)
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


def main():
    fresh = "--fresh" in sys.argv
    resolve_urls = "--resolve-urls" in sys.argv
    cache_file = DATA_DIR / "cache" / "directory.html"

    with httpx.Client(timeout=60) as client:
        if cache_file.exists() and not fresh:
            print(f"Using cached HTML from {cache_file}")
            html = cache_file.read_text()
        else:
            print(f"Fetching {BASE_URL}...")
            html = client.get(BASE_URL).text
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(html)

        raw = extract_companies(html)
        print(f"Found {len(raw)} companies")

        # Fetch coordinates from the map page
        coords = fetch_coordinates(client, fresh)

        # Extract and download stream icons
        print("Downloading capability stream icons...")
        stream_icons = extract_stream_icons(raw, client)

        # Normalize companies
        if resolve_urls:
            print("Processing companies (resolving URLs - this may take a while)...")
        else:
            print("Processing companies...")
        companies = [normalize_company(c, client, coords, resolve_urls) for c in raw]

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


if __name__ == "__main__":
    main()
