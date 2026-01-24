#!/usr/bin/env python3
"""
Export company data to CSV and XLSX formats.
Reads markdown files from content/company/ and validates against taxonomies.
"""

import sys
from pathlib import Path

import frontmatter
import pandas as pd
import yaml

# Paths
ROOT = Path(__file__).parent.parent
CONTENT_DIR = ROOT / "content" / "company"
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"


def load_taxonomies() -> dict:
    """Load taxonomy definitions from data/taxonomies.yaml"""
    tax_file = DATA_DIR / "taxonomies.yaml"
    if not tax_file.exists():
        print(f"Warning: {tax_file} not found", file=sys.stderr)
        return {}

    with open(tax_file) as f:
        return yaml.safe_load(f) or {}


def load_companies() -> list[dict]:
    """Load all company markdown files."""
    companies = []

    for md_file in sorted(CONTENT_DIR.glob("*.md")):
        # Skip index files
        if md_file.name.startswith("_"):
            continue

        try:
            post = frontmatter.load(str(md_file))
            company = dict(post.metadata)
            company["_content"] = post.content
            company["_file"] = md_file.name
            # Derive slug from filename (Hugo convention)
            company["slug"] = md_file.stem
            companies.append(company)
        except Exception as e:
            print(f"Error loading {md_file.name}: {e}", file=sys.stderr)

    return companies


def validate_company(company: dict, taxonomies: dict) -> list[str]:
    """Validate a company against taxonomy values. Returns list of errors."""
    errors = []
    filename = company.get("_file", "unknown")

    # Required fields
    if not company.get("name"):
        errors.append(f"{filename}: missing required field 'name'")

    # Validate taxonomy values (frontmatter contains keys, not display names)
    # Taxonomy format: { short_key: "Full Name" }
    def get_valid_keys(tax_dict):
        """Extract valid keys from taxonomy dict."""
        if not tax_dict:
            return []
        return list(tax_dict.keys())

    taxonomy_fields = [
        ("stakeholders", get_valid_keys(taxonomies.get("stakeholders", {}))),
        (
            "capability_streams",
            get_valid_keys(taxonomies.get("capability_streams", {})),
        ),
        (
            "capability_domains",
            get_valid_keys(taxonomies.get("capability_domains", {})),
        ),
        (
            "industrial_capabilities",
            get_valid_keys(taxonomies.get("industrial_capabilities", {})),
        ),
        ("regions", get_valid_keys(taxonomies.get("regions", {}))),
    ]

    for field, valid_keys in taxonomy_fields:
        company_values = company.get(field, []) or []
        for val in company_values:
            if val not in valid_keys:
                errors.append(f"{filename}: invalid {field} key '{val}'")

    return errors


def companies_to_dataframe(companies: list[dict], taxonomies: dict) -> pd.DataFrame:
    """Convert companies to a pandas DataFrame.

    Converts taxonomy keys to display names for human-readable output.
    """

    # Helper to convert keys to display names
    def keys_to_names(keys: list[str], tax_name: str) -> list[str]:
        mapping = taxonomies.get(tax_name, {})
        return [mapping.get(k, k) for k in keys]

    rows = []
    for c in companies:
        row = {
            "name": c.get("name", ""),
            "slug": c.get("slug", ""),
            "website": c.get("website", ""),
            "phone": c.get("phone", ""),
            "email": c.get("email", ""),
            "address": c.get("address", ""),
            "latitude": c.get("latitude"),
            "longitude": c.get("longitude"),
            "is_sme": c.get("is_sme", False),
            "is_prime": c.get("is_prime", False),
            "is_indigenous_owned": c.get("is_indigenous_owned", False),
            "is_veteran_owned": c.get("is_veteran_owned", False),
            # Join lists with semicolons, converting keys to display names
            "stakeholders": "; ".join(
                keys_to_names(c.get("stakeholders") or [], "stakeholders")
            ),
            "capability_streams": "; ".join(
                keys_to_names(c.get("capability_streams") or [], "capability_streams")
            ),
            "capability_domains": "; ".join(
                keys_to_names(c.get("capability_domains") or [], "capability_domains")
            ),
            "industrial_capabilities": "; ".join(
                keys_to_names(
                    c.get("industrial_capabilities") or [], "industrial_capabilities"
                )
            ),
            "regions": "; ".join(keys_to_names(c.get("regions") or [], "regions")),
            # Include overview (first part of content)
            "overview": (c.get("_content") or "").split("##")[0].strip()[:500],
        }
        rows.append(row)

    return pd.DataFrame(rows)


def export_csv(df: pd.DataFrame, output_path: Path) -> None:
    """Export DataFrame to CSV."""
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} companies to {output_path}")


def export_xlsx(df: pd.DataFrame, output_path: Path) -> None:
    """Export DataFrame to XLSX with formatting."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Companies")

        # Auto-adjust column widths
        worksheet = writer.sheets["Companies"]
        for idx, col in enumerate(df.columns):
            # Handle NaN values properly
            col_data = df[col].fillna("").astype(str)
            max_length = max(col_data.map(len).max(), len(col))
            # Cap at 50 chars, columns go A-Z then AA, AB, etc.
            col_letter = (
                chr(65 + idx)
                if idx < 26
                else f"{chr(64 + idx // 26)}{chr(65 + idx % 26)}"
            )
            worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)

    print(f"Exported {len(df)} companies to {output_path}")


def main():
    """Main export function."""
    print("Loading taxonomies...")
    taxonomies = load_taxonomies()

    print(f"Loading companies from {CONTENT_DIR}...")
    companies = load_companies()
    print(f"Found {len(companies)} companies")

    # Validate
    print("Validating companies...")
    all_errors = []
    for company in companies:
        errors = validate_company(company, taxonomies)
        all_errors.extend(errors)

    if all_errors:
        print(f"\nValidation errors ({len(all_errors)}):", file=sys.stderr)
        for error in all_errors[:20]:  # Show first 20
            print(f"  - {error}", file=sys.stderr)
        if len(all_errors) > 20:
            print(f"  ... and {len(all_errors) - 20} more", file=sys.stderr)
        print("\nExport will continue but data may be incomplete.", file=sys.stderr)

    # Convert to DataFrame
    df = companies_to_dataframe(companies, taxonomies)

    # Sort by name
    df = df.sort_values("name", ignore_index=True)

    # Export
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    export_csv(df, STATIC_DIR / "companies.csv")
    export_xlsx(df, STATIC_DIR / "companies.xlsx")

    print("\nExport complete!")
    return 0  # Always succeed - validation is informational


if __name__ == "__main__":
    sys.exit(main())
