#!/usr/bin/env python3
"""
Preprocess company data for the directory site.

Generates:
  - data/computed.yaml: Pre-calculated values for Hugo templates
  - static/maps/*.png: Static minimap images for companies
  - static/maps/terms/*.png: Static map images for taxonomy terms
  - static/companies.csv, .xlsx, .json: Export files

Usage:
    uv run python scripts/preprocess.py
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import frontmatter
import pandas as pd
import yaml
from openpyxl.utils import get_column_letter
from pymgl import Map
from shapely import MultiPoint, Point
from shapely.geometry import mapping

from config import (
    params,
    COMPANY_DIR,
    DATA_DIR,
    MAPS_DIR,
    STATIC_DIR,
    TERM_MAPS_DIR,
    TAXONOMIES,
    MAP_WIDTH,
    MAP_HEIGHT,
    MAP_MARKER_LAYERS,
    OVERVIEW_MAX_LENGTH,
    make_progress,
)


# --- Map rendering ---


def setup_map(
    width: int = MAP_WIDTH, height: int = MAP_HEIGHT, zoom: float = 13
) -> Map:
    """Create a Map instance with marker layers."""
    response = httpx.get(params["mapStyleUrl"])
    response.raise_for_status()
    style = response.json()
    style["sources"]["markers"] = {
        "type": "geojson",
        "data": {"type": "FeatureCollection", "features": []},
    }
    style["layers"].extend(MAP_MARKER_LAYERS)
    return Map(json.dumps(style), width, height, 2, 115.86, -31.95, zoom)


def render_map(
    m: Map,
    locations: list[tuple[float, float]],
    output: Path,
    max_zoom: float = 13,
    zoom_out: float = 0.2,
    wait: float = 0.1,
    max_age_days: float = 1,
) -> bool:
    """Render map with markers. Returns True if rendered, False if cached."""
    if output.exists():
        mtime = datetime.fromtimestamp(output.stat().st_mtime)
        if datetime.now() - mtime < timedelta(days=max_age_days):
            return False

    points = [Point(lng, lat) for lat, lng in locations]
    geom = MultiPoint(points) if len(points) > 1 else points[0]
    geojson = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": mapping(geom)}],
    }

    m.setGeoJSON("markers", json.dumps(geojson))
    m.setBounds(*geom.bounds)
    m.setZoom(min(max_zoom, m.zoom - zoom_out))
    m.load()
    time.sleep(wait)
    output.write_bytes(m.renderPNG())
    return True


# --- Hugo computed data ---


def truncate_overview(text: str, max_length: int = OVERVIEW_MAX_LENGTH) -> str:
    """Truncate text to max length at word boundary."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - 1]
    return (
        truncated.rsplit(" ", 1)[0] + "..." if " " in truncated else truncated + "..."
    )


def generate_filter_data(fm: dict) -> str | None:
    """Generate filter string with taxonomy:key values."""
    parts = [f"{field}:{key}" for field in TAXONOMIES for key in fm.get(field, [])]
    return "|".join(parts) if parts else None


# --- Export functions ---


def load_taxonomies() -> dict:
    """Load taxonomy definitions."""
    tax_file = DATA_DIR / "taxonomies.yaml"
    if not tax_file.exists():
        return {}
    with open(tax_file) as f:
        return yaml.safe_load(f) or {}


def _build_export_rows(companies: list[dict], taxonomies: dict) -> list[dict]:
    """Build export rows with display names for taxonomies."""

    def keys_to_names(keys: list | None, tax: str) -> str:
        mapping = taxonomies.get(tax, {})
        return "; ".join(mapping.get(k, k) for k in (keys or []))

    return [
        {
            "name": c.get("name", ""),
            "website": c.get("website", ""),
            "regions": keys_to_names(c.get("regions"), "regions"),
            "address": c.get("address", ""),
            "capability_streams": keys_to_names(
                c.get("capability_streams"), "capability_streams"
            ),
            "capability_domains": keys_to_names(
                c.get("capability_domains"), "capability_domains"
            ),
            "industrial_capabilities": keys_to_names(
                c.get("industrial_capabilities"), "industrial_capabilities"
            ),
            "stakeholders": keys_to_names(c.get("stakeholders"), "stakeholders"),
            "is_sme": c.get("is_sme", False),
            "is_prime": c.get("is_prime", False),
            "phone": c.get("phone", ""),
            "email": c.get("email", ""),
            "latitude": c.get("latitude"),
            "longitude": c.get("longitude"),
            "markdown": c.get("_content", "").strip(),
            "slug": c.get("slug", ""),
        }
        for c in companies
    ]


def export_csv(companies: list[dict], taxonomies: dict, output: Path) -> None:
    """Export to CSV with display names."""
    rows = _build_export_rows(companies, taxonomies)
    df = pd.DataFrame(rows).sort_values("name", ignore_index=True)
    df.to_csv(output, index=False)


def export_xlsx(companies: list[dict], taxonomies: dict, output: Path) -> None:
    """Export to XLSX with formatting."""
    rows = _build_export_rows(companies, taxonomies)
    df = pd.DataFrame(rows).sort_values("name", ignore_index=True)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Companies")
        ws = writer.sheets["Companies"]

        # Hyperlinks for website column
        website_col = list(df.columns).index("website") + 1
        for row_idx, url in enumerate(df["website"], start=2):
            if url and isinstance(url, str) and url.startswith("http"):
                cell = ws.cell(row=row_idx, column=website_col)
                cell.hyperlink = url
                cell.style = "Hyperlink"

        # Auto-width columns
        for idx, col in enumerate(df.columns):
            col_data = df[col].fillna("").astype(str)
            width = min(
                max(col_data.map(len).max(), len(col)) + 2,
                80 if col == "markdown" else 50,
            )
            ws.column_dimensions[get_column_letter(idx + 1)].width = width

        ws.freeze_panes = "A2"


def export_json(companies: list[dict], output: Path) -> None:
    """Export to JSON with taxonomy keys."""
    data = sorted(
        [
            {
                "slug": c.get("slug", ""),
                "name": c.get("name", ""),
                "website": c.get("website", ""),
                "address": c.get("address", ""),
                "phone": c.get("phone", ""),
                "email": c.get("email", ""),
                "latitude": c.get("latitude"),
                "longitude": c.get("longitude"),
                "markdown": c.get("_content", "").strip(),
                "regions": c.get("regions") or [],
                "stakeholders": c.get("stakeholders") or [],
                "capability_streams": c.get("capability_streams") or [],
                "capability_domains": c.get("capability_domains") or [],
                "industrial_capabilities": c.get("industrial_capabilities") or [],
                "is_sme": c.get("is_sme", False),
                "is_prime": c.get("is_prime", False),
            }
            for c in companies
        ],
        key=lambda x: x["name"].lower(),
    )

    output.write_text(json.dumps(data, indent=2))


# --- Main ---


def main():
    companies = []
    computed = {}
    company_locations: list[tuple[str, float, float]] = []
    term_locations: dict[str, dict[str, list[tuple[float, float]]]] = {
        tax: {} for tax in TAXONOMIES
    }

    # Load all companies
    for path in sorted(COMPANY_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue

        post = frontmatter.load(str(path))
        slug = path.stem
        fm = post.metadata

        # Store for export
        company = dict(fm)
        company["slug"] = slug
        company["_content"] = post.content
        companies.append(company)

        # Computed data for Hugo
        name = fm.get("name", "")
        overview = str(fm.get("overview", ""))
        data = {"search_text": f"{name} {overview}".lower().strip()}
        if overview_short := truncate_overview(overview):
            data["overview_short"] = overview_short
        if filter_data := generate_filter_data(fm):
            data["filter_data"] = filter_data
        computed[slug] = data

        # Map locations
        lat, lng = fm.get("latitude"), fm.get("longitude")
        if lat and lng:
            company_locations.append((slug, float(lat), float(lng)))
            for taxonomy in TAXONOMIES:
                for term_key in fm.get(taxonomy, []):
                    term_locations[taxonomy].setdefault(term_key, []).append(
                        (float(lat), float(lng))
                    )

    print(f"Processed {len(companies)} companies")

    # Write computed YAML
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "computed.yaml", "w") as f:
        yaml.dump(
            computed, f, default_flow_style=False, allow_unicode=True, sort_keys=True
        )
    print("Generated data/computed.yaml")

    # Export files
    taxonomies = load_taxonomies()
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    export_csv(companies, taxonomies, STATIC_DIR / "companies.csv")
    export_xlsx(companies, taxonomies, STATIC_DIR / "companies.xlsx")
    export_json(companies, STATIC_DIR / "companies.json")
    print(f"Exported to CSV, XLSX, JSON")

    # Generate maps
    if not company_locations:
        print("No coordinates, skipping maps")
        return

    print("Setting up map renderer...")
    m = setup_map()
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    TERM_MAPS_DIR.mkdir(parents=True, exist_ok=True)

    # Company maps
    count = 0
    with make_progress() as progress:
        task = progress.add_task("Company maps...", total=len(company_locations))
        for slug, lat, lng in company_locations:
            if render_map(m, [(lat, lng)], MAPS_DIR / f"{slug}.png"):
                count += 1
            progress.update(task, advance=1)
    print(f"Generated {count} company maps ({len(company_locations) - count} cached)")

    # Term maps
    term_maps = [
        (f"{tax}-{key}", locs)
        for tax, terms in term_locations.items()
        for key, locs in terms.items()
        if locs
    ]
    count = 0
    with make_progress() as progress:
        task = progress.add_task("Term maps...", total=len(term_maps))
        for key, locs in term_maps:
            if render_map(m, locs, TERM_MAPS_DIR / f"{key}.png"):
                count += 1
            progress.update(task, advance=1)
    print(f"Generated {count} term maps ({len(term_maps) - count} cached)")


if __name__ == "__main__":
    main()
