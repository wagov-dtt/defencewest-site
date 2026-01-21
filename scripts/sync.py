#!/usr/bin/env python3
"""
Sync script for company data.

Usage:
  - Export: mise run sync --export   # Creates data/companies.json from YAML files
  - Import: mise run sync --import   # Updates YAML files from data/companies.json
"""

import argparse
import json
from pathlib import Path

import yaml


def export_to_json(companies_dir: Path, output_file: Path):
    """Export all YAML files to a single JSON file."""
    companies = []

    for yaml_file in sorted(companies_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            company = yaml.safe_load(f)
            companies.append(company)

    companies.sort(key=lambda c: c.get("name", ""))

    with open(output_file, "w") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(companies)} companies to {output_file}")


def import_from_json(companies_dir: Path, input_file: Path):
    """Import JSON file and update YAML files."""
    with open(input_file) as f:
        companies = json.load(f)

    if not isinstance(companies, list):
        raise ValueError("Expected JSON array of companies")

    # Track existing files
    existing_files = set(companies_dir.glob("*.yaml"))
    updated_files = set()

    for company in companies:
        slug = company.get("slug")
        if not slug:
            print(
                f"Warning: Company missing slug, skipping: {company.get('name', 'unknown')}"
            )
            continue

        yaml_file = companies_dir / f"{slug}.yaml"
        updated_files.add(yaml_file)

        # Check if file exists and has changes
        if yaml_file.exists():
            with open(yaml_file) as f:
                existing = yaml.safe_load(f)
            if existing == company:
                continue  # No changes

        # Write updated YAML
        with open(yaml_file, "w") as f:
            yaml.dump(
                company,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        action = "Updated" if yaml_file.exists() else "Created"
        print(f"{action}: {yaml_file.name}")

    # Report removed files (but don't delete them)
    removed = existing_files - updated_files
    for removed_file in removed:
        print(f"Warning: File not in JSON (not deleted): {removed_file.name}")

    print(f"\nProcessed {len(companies)} companies")


def main():
    parser = argparse.ArgumentParser(
        description="Sync company data between YAML and JSON"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", action="store_true", help="Export YAML to JSON")
    group.add_argument(
        "--import", dest="import_json", action="store_true", help="Import JSON to YAML"
    )

    args = parser.parse_args()

    companies_dir = Path("data/companies")
    json_file = Path("data/companies.json")

    if args.export:
        export_to_json(companies_dir, json_file)
    elif args.import_json:
        if not json_file.exists():
            print(f"Error: {json_file} not found. Export first or create the file.")
            return 1
        import_from_json(companies_dir, json_file)

    return 0


if __name__ == "__main__":
    exit(main())
