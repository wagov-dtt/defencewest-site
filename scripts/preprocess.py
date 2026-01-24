#!/usr/bin/env python3
"""
Preprocess company data to generate computed values and static map images.

Generates:
  - data/computed.yaml: Pre-calculated values for Hugo templates
  - static/maps/*.png: Static minimap images (when --maps flag used)

Note: Taxonomy counts are now handled by Hugo's native taxonomy system.

Usage:
    uv run python scripts/preprocess.py [--dry-run] [--maps] [--force-maps]
"""

import json
import os
import re
import sys
import tomllib
from pathlib import Path

import yaml

# Fix SSL cert path for pymgl/libcurl
os.environ.setdefault("CURL_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt")
os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")

from pymgl import Map

# Paths
ROOT_DIR = Path(__file__).parent.parent
CONTENT_DIR = ROOT_DIR / "content" / "company"
DATA_DIR = ROOT_DIR / "data"
MAPS_DIR = ROOT_DIR / "static" / "maps"
HUGO_CONFIG = ROOT_DIR / "hugo.toml"

# Load config from hugo.toml
with open(HUGO_CONFIG, "rb") as f:
    config = tomllib.load(f)
    params = config.get("params", {})

MAP_STYLE_URL = params.get(
    "mapStyleUrl", "https://vector.openstreetmap.org/styles/shortbread/colorful.json"
)

# Map rendering settings
MAP_WIDTH = 360
MAP_HEIGHT = 150
MAP_ZOOM = 13  # Neighborhood level - shows good context in small thumbnail
MAP_PITCH = 20  # Subtle tilt for 3D effect
MAP_BEARING = 345  # Slight rotation (360 - 15)


def generate_minimap(slug: str, lat: float, lng: float) -> bool:
    """Generate a static minimap PNG using pymgl."""
    import urllib.request

    # Fetch map style
    with urllib.request.urlopen(MAP_STYLE_URL) as response:
        style = json.loads(response.read().decode())

    # Add marker source and layers
    style["sources"]["marker"] = {
        "type": "geojson",
        "data": {"type": "Point", "coordinates": [lng, lat]},
    }
    style["layers"].extend(
        [
            {
                "id": "marker-border",
                "type": "circle",
                "source": "marker",
                "paint": {"circle-radius": 10, "circle-color": "#ffffff"},
            },
            {
                "id": "marker",
                "type": "circle",
                "source": "marker",
                "paint": {"circle-radius": 6, "circle-color": "#1095c1"},
            },
        ]
    )

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    with Map(json.dumps(style), MAP_WIDTH, MAP_HEIGHT, 2, lng, lat, MAP_ZOOM) as m:
        m.setBearing(MAP_BEARING)
        m.setPitch(MAP_PITCH)
        (MAPS_DIR / f"{slug}.png").write_bytes(m.renderPNG())
    return True


def extract_overview(content: str, max_length: int = 300) -> str:
    """Extract and truncate overview section from markdown content."""
    text = re.sub(r"(?s)^\s*## Overview\s*", "", content)
    text = re.sub(r"(?s)\n##.*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_length:
        text = text[: max_length - 1].rsplit(" ", 1)[0] + "…"
    return text


def generate_filter_data(frontmatter: dict) -> str | None:
    """Generate flat filter string with prefixed values.

    Frontmatter already contains short keys, so we just prefix them.
    Format: "stake:academic|stream:base|domain:armour|ind:welding|region:perth|own:indigenous"
    """
    prefixes = {
        "stakeholders": "stake",
        "capability_streams": "stream",
        "capability_domains": "domain",
        "industrial_capabilities": "ind",
        "regions": "region",
    }
    parts = []
    for field, prefix in prefixes.items():
        for key in frontmatter.get(field, []):
            parts.append(f"{prefix}:{key}")

    # Add ownership flags
    if frontmatter.get("is_indigenous_owned"):
        parts.append("own:indigenous")
    if frontmatter.get("is_veteran_owned"):
        parts.append("own:veteran")

    return "|".join(parts) if parts else None


def process_company(path: Path) -> tuple[str, dict]:
    """Process a single company markdown file."""
    content = path.read_text()
    slug = path.stem

    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return slug, {}

    frontmatter = yaml.safe_load(match.group(1))
    body = match.group(2)
    computed = {}

    overview_short = extract_overview(body)
    if overview_short:
        computed["overview_short"] = overview_short
        name = frontmatter.get("name", "")
        computed["search_text"] = f"{name} {overview_short}".lower().strip()

    filter_data = generate_filter_data(frontmatter)
    if filter_data:
        computed["filter_data"] = filter_data

    return slug, computed


def main():
    dry_run = "--dry-run" in sys.argv
    gen_maps = "--maps" in sys.argv
    force_maps = "--force-maps" in sys.argv

    # Collect company data
    computed = {}
    companies_needing_maps = []

    for path in sorted(CONTENT_DIR.glob("*.md")):
        slug, data = process_company(path)
        if data:
            computed[slug] = data

        # Check if map needed
        if gen_maps or force_maps:
            content = path.read_text()
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                fm = yaml.safe_load(match.group(1))
                lat, lng = fm.get("latitude"), fm.get("longitude")
                if lat and lng:
                    map_path = MAPS_DIR / f"{slug}.png"
                    if force_maps or not map_path.exists():
                        companies_needing_maps.append((slug, lat, lng))

    print(f"Processed {len(computed)} companies")

    if dry_run:
        print("\nWould generate:")
        print(f"  data/computed.yaml ({len(computed)} entries)")
        if companies_needing_maps:
            print(f"  static/maps/*.png ({len(companies_needing_maps)} images)")
        return

    # Write computed YAML
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "computed.yaml", "w") as f:
        yaml.dump(
            computed, f, default_flow_style=False, allow_unicode=True, sort_keys=True
        )
    print("Generated data/computed.yaml")

    # Generate maps if requested
    if companies_needing_maps:
        print(f"Generating {len(companies_needing_maps)} map images...")
        for i, (slug, lat, lng) in enumerate(companies_needing_maps):
            generate_minimap(slug, lat, lng)
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(companies_needing_maps)}...")
        print(f"Generated {len(companies_needing_maps)} map images")


if __name__ == "__main__":
    main()
