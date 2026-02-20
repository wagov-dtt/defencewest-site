#!/usr/bin/env python3
"""
Preprocess company data for directory site.

Generates:
  - static/maps/*.png: Static minimap images for companies
  - static/maps/terms/*.png: Static map images for taxonomy terms
  - static/companies.csv, .xlsx, .json: Export files

Usage:
    uv run python scripts/preprocess.py
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import frontmatter
import pandas as pd
import markdown_it
from openpyxl.utils import get_column_letter
from mlnative import Map, from_latlng

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
    load_taxonomies,
    make_progress,
)

# Initialize markdown-it for HTML conversion
md = markdown_it.MarkdownIt()

# --- Map rendering ---


def setup_map(width: int = MAP_WIDTH, height: int = MAP_HEIGHT) -> tuple[Map, dict]:
    """Create a Map instance and load style with marker layers."""
    response = httpx.get(params["mapStyleUrl"])
    response.raise_for_status()
    style = response.json()
    style["sources"]["markers"] = {
        "type": "geojson",
        "data": {"type": "FeatureCollection", "features": []},
    }
    style["layers"].extend(MAP_MARKER_LAYERS)
    return Map(width, height, pixel_ratio=2), style


def render_map(
    m: Map,
    style: dict,
    locations: list[tuple[float, float]],
    output: Path,
    max_zoom: float = 13,
    zoom_out: float = 0.2,
    max_age_days: float = 1,
) -> bool:
    """Render map with markers. Returns True if rendered, False if cached."""
    if output.exists():
        mtime = datetime.fromtimestamp(output.stat().st_mtime)
        if datetime.now() - mtime < timedelta(days=max_age_days):
            return False

    geom = from_latlng(locations)

    # Calculate bounds from locations (lat, lng order)
    lats = [lat for lat, _lng in locations]
    lngs = [lng for _lat, lng in locations]
    bounds = (min(lngs), min(lats), max(lngs), max(lats))

    m.load_style(style)
    m.set_geojson("markers", geom)
    center, zoom = m.fit_bounds(bounds, max_zoom=max_zoom)
    png = m.render(center=center, zoom=zoom - zoom_out)
    output.write_bytes(png)
    return True


# --- Export functions ---


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
            "content_html": md.render(c.get("_content", "").strip()),
            "slug": c.get("slug", ""),
        }
        for c in companies
    ]


def export_csv(df: pd.DataFrame, output: Path) -> None:
    """Export DataFrame to CSV."""
    df.to_csv(output, index=False)


def export_xlsx(df: pd.DataFrame, output: Path) -> None:
    """Export DataFrame to XLSX with formatting."""

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
    """Export to JSON - all frontmatter fields plus computed fields for map."""
    data = []
    for c in companies:
        entry = {k: v for k, v in c.items() if not k.startswith("_")}

        # Convert is_sme/is_prime to company_types taxonomy
        company_types = list(entry.get("company_types", []))
        if entry.get("is_sme") and "sme" not in company_types:
            company_types.append("sme")
        if entry.get("is_prime") and "prime" not in company_types:
            company_types.append("prime")
        if company_types:
            entry["company_types"] = company_types

        # Add search text (lowercase name + overview)
        search_text = (
            entry.get("name", "") + " " + (entry.get("overview") or "")
        ).lower()
        entry["search"] = search_text.strip()

        # Add logo URL
        slug = entry.get("slug", "")
        logo_path = STATIC_DIR / "logos" / f"{slug}.png"
        entry["logo_url"] = f"/logos/{slug}.png" if logo_path.exists() else ""

        # Add truncated overview (150 chars)
        overview = entry.get("overview") or ""
        entry["overview_short"] = overview[:150] + (
            "..." if len(overview) > 150 else ""
        )

        # Add HTML content if present
        if c.get("_content"):
            entry["content_html"] = md.render(c["_content"].strip())

        data.append(entry)
    data.sort(key=lambda x: (x.get("name") or "").lower())
    output.write_text(json.dumps(data, indent=2))


# --- Main ---


def main():
    companies = []
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

    # Export files
    taxonomies = load_taxonomies(raw=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    rows = _build_export_rows(companies, taxonomies)
    df = pd.DataFrame(rows).sort_values("name", ignore_index=True)
    export_csv(df, STATIC_DIR / "companies.csv")
    export_xlsx(df, STATIC_DIR / "companies.xlsx")
    export_json(companies, STATIC_DIR / "companies.json")
    print("Exported to CSV, XLSX, JSON")

    # Generate maps
    if not company_locations:
        print("No coordinates, skipping maps")
        return

    print("Setting up map renderer...")
    m, style = setup_map()
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    TERM_MAPS_DIR.mkdir(parents=True, exist_ok=True)

    with m:
        # Company maps
        count = 0
        with make_progress() as progress:
            task = progress.add_task("Company maps...", total=len(company_locations))
            for slug, lat, lng in company_locations:
                if render_map(m, style, [(lat, lng)], MAPS_DIR / f"{slug}.png"):
                    count += 1
                progress.update(task, advance=1)
        print(
            f"Generated {count} company maps ({len(company_locations) - count} cached)"
        )

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
                if render_map(m, style, locs, TERM_MAPS_DIR / f"{key}.png"):
                    count += 1
                progress.update(task, advance=1)
        print(f"Generated {count} term maps ({len(term_maps) - count} cached)")


if __name__ == "__main__":
    main()
