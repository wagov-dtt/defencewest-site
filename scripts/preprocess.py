#!/usr/bin/env python3
"""
Preprocess company data to generate computed values and static map images.

Generates:
  - data/computed.yaml: Pre-calculated values for Hugo templates
  - static/maps/*.png: Static minimap images for companies (when --maps flag used)
  - static/maps/terms/*.png: Static map images for taxonomy terms (when --maps flag used)
  - static/map-assets/: Map style and assets from OSM (when --refresh-style flag used)

Note: Taxonomy counts are now handled by Hugo's native taxonomy system.

Usage:
    uv run python scripts/preprocess.py [--dry-run] [--maps] [--force-maps] [--refresh-style]
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

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
TERM_MAPS_DIR = MAPS_DIR / "terms"
MAP_ASSETS_DIR = ROOT_DIR / "static" / "map-assets"

MAP_STYLE_URL = "https://vector.openstreetmap.org/styles/shortbread/colorful.json"

# Map rendering settings
MAP_WIDTH = 360
MAP_HEIGHT = 150
MAP_ZOOM = 13
MAP_PITCH = 20
MAP_BEARING = 345
MAP_PADDING = 30  # pixels padding around bounds for multi-marker maps

# Cached base style
_base_style_json = None


def fetch_url(url: str, timeout: int = 30) -> bytes:
    """Fetch a URL and return bytes."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def refresh_map_style() -> None:
    """Download OSM map style and all referenced assets to static/map-assets/."""
    print(f"Fetching style from {MAP_STYLE_URL}...")
    style_json = fetch_url(MAP_STYLE_URL).decode()
    style = json.loads(style_json)

    MAP_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Download sprites (sprites.json, sprites.png, sprites@2x.json, sprites@2x.png)
    sprite = style.get("sprite")
    if sprite:
        sprite_base = sprite if isinstance(sprite, str) else sprite[0].get("url", "")
        if sprite_base:
            sprite_url = urljoin(MAP_STYLE_URL, sprite_base)
            sprites_dir = MAP_ASSETS_DIR / "sprites"
            sprites_dir.mkdir(parents=True, exist_ok=True)
            for ext in [".json", ".png", "@2x.json", "@2x.png"]:
                url = sprite_url + ext
                local_path = sprites_dir / f"sprites{ext}"
                try:
                    print(f"  Fetching sprites{ext}...")
                    local_path.write_bytes(fetch_url(url))
                except Exception as e:
                    print(f"  Warning: Failed to fetch {url}: {e}")

    # Download font glyphs
    glyphs = style.get("glyphs")
    if glyphs:
        # Get font names from style layers
        fonts = set()
        for layer in style.get("layers", []):
            layout = layer.get("layout", {})
            text_font = layout.get("text-font", [])
            if isinstance(text_font, list):
                fonts.update(text_font)

        # Common Unicode ranges for Latin/Western text
        ranges = ["0-255", "256-511", "512-767", "768-1023", "8192-8447"]

        for font in fonts:
            font_dir = MAP_ASSETS_DIR / "fonts" / font
            font_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Fetching font {font}...")
            for r in ranges:
                glyph_url = urljoin(
                    MAP_STYLE_URL,
                    glyphs.replace("{fontstack}", font).replace("{range}", r),
                )
                local_path = font_dir / f"{r}.pbf"
                try:
                    local_path.write_bytes(fetch_url(glyph_url))
                except Exception as e:
                    print(f"    Warning: Failed to fetch {r}.pbf: {e}")

    # Rewrite style with relative paths for local serving
    local_style = style.copy()
    local_style["sprite"] = "sprites/sprites"
    local_style["glyphs"] = "fonts/{fontstack}/{range}.pbf"

    style_path = MAP_ASSETS_DIR / "style.json"
    style_path.write_text(json.dumps(local_style, indent=2))
    print(f"Saved {style_path}")


def get_base_style_json() -> str:
    """Fetch and cache the base map style."""
    global _base_style_json
    if _base_style_json is None:
        with urllib.request.urlopen(MAP_STYLE_URL) as response:
            _base_style_json = response.read().decode()
    return _base_style_json


def get_base_style() -> dict:
    """Return a fresh copy of the base style dict."""
    return json.loads(get_base_style_json())


def add_marker_layers(style: dict, source_name: str = "marker") -> None:
    """Add circle marker layers to a style."""
    style["layers"].extend(
        [
            {
                "id": f"{source_name}-border",
                "type": "circle",
                "source": source_name,
                "paint": {"circle-radius": 10, "circle-color": "#ffffff"},
            },
            {
                "id": source_name,
                "type": "circle",
                "source": source_name,
                "paint": {"circle-radius": 6, "circle-color": "#1095c1"},
            },
        ]
    )


def generate_minimap(slug: str, lat: float, lng: float) -> bool:
    """Generate a static minimap PNG for a single company location."""
    style = get_base_style()

    # Add marker source
    style["sources"]["marker"] = {
        "type": "geojson",
        "data": {"type": "Point", "coordinates": [lng, lat]},
    }
    add_marker_layers(style, "marker")

    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    with Map(json.dumps(style), MAP_WIDTH, MAP_HEIGHT, 2, lng, lat, MAP_ZOOM) as m:
        m.setBearing(MAP_BEARING)
        m.setPitch(MAP_PITCH)
        m.load()  # Wait for tiles to load
        (MAPS_DIR / f"{slug}.png").write_bytes(m.renderPNG())
    return True


def generate_term_map(term_key: str, locations: list[tuple[float, float]]) -> bool:
    """Generate a static map PNG showing all company locations for a taxonomy term."""
    if not locations:
        return False

    style = get_base_style()

    # Calculate bounds
    lats = [loc[0] for loc in locations]
    lngs = [loc[1] for loc in locations]
    min_lng, max_lng = min(lngs), max(lngs)
    min_lat, max_lat = min(lats), max(lats)

    # Add small padding to bounds if all points are at same location
    if min_lng == max_lng:
        min_lng -= 0.01
        max_lng += 0.01
    if min_lat == max_lat:
        min_lat -= 0.01
        max_lat += 0.01

    # Center point for initial map creation
    center_lng = (min_lng + max_lng) / 2
    center_lat = (min_lat + max_lat) / 2

    # Add markers as GeoJSON FeatureCollection
    features = [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lng, lat]}}
        for lat, lng in locations
    ]
    style["sources"]["markers"] = {
        "type": "geojson",
        "data": {"type": "FeatureCollection", "features": features},
    }
    add_marker_layers(style, "markers")

    TERM_MAPS_DIR.mkdir(parents=True, exist_ok=True)

    # Create map, fit to bounds, then render (same size as company minimaps)
    with Map(
        json.dumps(style), MAP_WIDTH, MAP_HEIGHT, 2, center_lng, center_lat, 4
    ) as m:
        # setBounds(xmin, ymin, xmax, ymax, padding) - note: x=lng, y=lat
        m.setBounds(min_lng, min_lat, max_lng, max_lat, MAP_PADDING)
        m.load()  # Wait for tiles to load
        (TERM_MAPS_DIR / f"{term_key}.png").write_bytes(m.renderPNG())
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
    """Generate flat filter string with prefixed values."""
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
    refresh_style = "--refresh-style" in sys.argv

    # Refresh map style and assets if requested
    if refresh_style:
        refresh_map_style()
        if not gen_maps and not force_maps:
            return

    # Collect company data
    computed = {}
    companies_needing_maps = []

    # Collect taxonomy term locations for term maps
    term_locations: dict[str, dict[str, list[tuple[float, float]]]] = {
        "stakeholders": {},
        "capability_streams": {},
        "capability_domains": {},
        "industrial_capabilities": {},
        "regions": {},
    }

    for path in sorted(CONTENT_DIR.glob("*.md")):
        slug, data = process_company(path)
        if data:
            computed[slug] = data

        # Parse frontmatter for map generation
        content = path.read_text()
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if match:
            fm = yaml.safe_load(match.group(1))
            lat, lng = fm.get("latitude"), fm.get("longitude")

            # Collect company minimap needs
            if gen_maps or force_maps:
                if lat and lng:
                    map_path = MAPS_DIR / f"{slug}.png"
                    if force_maps or not map_path.exists():
                        companies_needing_maps.append((slug, lat, lng))

            # Collect term locations
            if lat and lng:
                for taxonomy in term_locations:
                    for term_key in fm.get(taxonomy, []):
                        if term_key not in term_locations[taxonomy]:
                            term_locations[taxonomy][term_key] = []
                        term_locations[taxonomy][term_key].append((lat, lng))

    print(f"Processed {len(computed)} companies")

    # Determine which term maps need generation
    terms_needing_maps = []
    if gen_maps or force_maps:
        for taxonomy, terms in term_locations.items():
            for term_key, locations in terms.items():
                if locations:
                    map_path = TERM_MAPS_DIR / f"{taxonomy}-{term_key}.png"
                    if force_maps or not map_path.exists():
                        terms_needing_maps.append((f"{taxonomy}-{term_key}", locations))

    if dry_run:
        print("\nWould generate:")
        print(f"  data/computed.yaml ({len(computed)} entries)")
        if companies_needing_maps:
            print(f"  static/maps/*.png ({len(companies_needing_maps)} company images)")
        if terms_needing_maps:
            print(f"  static/maps/terms/*.png ({len(terms_needing_maps)} term images)")
        return

    # Write computed YAML
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "computed.yaml", "w") as f:
        yaml.dump(
            computed, f, default_flow_style=False, allow_unicode=True, sort_keys=True
        )
    print("Generated data/computed.yaml")

    # Pre-fetch base style
    if companies_needing_maps or terms_needing_maps:
        print("Fetching map style...")
        get_base_style_json()

    # Generate company maps (sequential - OpenGL context can't be shared)
    if companies_needing_maps:
        MAPS_DIR.mkdir(parents=True, exist_ok=True)
        total = len(companies_needing_maps)
        print(f"Generating {total} company map images...")
        for i, (slug, lat, lng) in enumerate(companies_needing_maps):
            generate_minimap(slug, lat, lng)
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{total}...")
        print(f"Generated {total} company map images")

    # Generate term maps (sequential)
    if terms_needing_maps:
        TERM_MAPS_DIR.mkdir(parents=True, exist_ok=True)
        total = len(terms_needing_maps)
        print(f"Generating {total} term map images...")
        for i, (term_key, locations) in enumerate(terms_needing_maps):
            generate_term_map(term_key, locations)
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{total}...")
        print(f"Generated {total} term map images")


if __name__ == "__main__":
    main()
