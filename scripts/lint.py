#!/usr/bin/env python3
"""
Lint and validate company YAML files.

Checks for:
- Valid YAML syntax
- Required fields (name, slug)
- Slug matches filename
- Valid taxonomy values (stakeholders, streams, domains, regions)
- No unknown fields (catches typos)

Outputs clear error messages for CI/CD.
"""

import sys
from pathlib import Path
import yaml

DATA_DIR = Path(__file__).parent.parent / "data"
COMPANIES_DIR = DATA_DIR / "companies"
TAXONOMIES_FILE = DATA_DIR / "taxonomies.yaml"

# Required fields for every company
REQUIRED_FIELDS = ["name", "slug"]

# All known fields - anything else is probably a typo
KNOWN_FIELDS = {
    # Required
    "name",
    "slug",
    # Basic info
    "overview",
    "website",
    "logo_url",
    # Contact
    "contact_name",
    "contact_title",
    "address",
    "phone",
    "email",
    # Location
    "latitude",
    "longitude",
    # Social
    "linkedin",
    "facebook",
    "twitter",
    "youtube",
    # Flags
    "is_prime",
    "is_sme",
    "is_featured",
    # Classifications (lists)
    "stakeholders",
    "capability_streams",
    "capability_domains",
    "industrial_capabilities",
    "regions",
    # Optional extras
    "capabilities",
    "discriminators",
}


def load_taxonomies() -> dict:
    """Load valid taxonomy values."""
    if not TAXONOMIES_FILE.exists():
        return {}
    with open(TAXONOMIES_FILE) as f:
        return yaml.safe_load(f) or {}


def lint_company(filepath: Path, taxonomies: dict) -> list[str]:
    """Lint a single company file. Returns list of errors."""
    errors = []
    filename = filepath.stem  # filename without .yaml

    # Try to parse YAML
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"Invalid YAML syntax: {e}"]

    if not data:
        return ["File is empty"]

    if not isinstance(data, dict):
        return ["File must contain a YAML mapping (key: value pairs)"]

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif not data[field]:
            errors.append(f"Required field is empty: {field}")

    # Check slug matches filename
    if "slug" in data and data["slug"] != filename:
        errors.append(f"Slug '{data['slug']}' doesn't match filename '{filename}'")

    # Check for unknown fields (likely typos)
    for field in data.keys():
        if field not in KNOWN_FIELDS:
            errors.append(f"Unknown field: '{field}' (typo?)")

    # Validate taxonomy values
    taxonomy_fields = {
        "stakeholders": "stakeholders",
        "capability_streams": "capability_streams",
        "capability_domains": "capability_domains",
        "industrial_capabilities": "industrial_capabilities",
        "regions": "regions",
    }

    for field, taxonomy_key in taxonomy_fields.items():
        if field in data and data[field]:
            valid_values = set(taxonomies.get(taxonomy_key, []))
            if valid_values:  # Only validate if we have taxonomy data
                for value in data[field]:
                    if value not in valid_values:
                        errors.append(f"Invalid {field} value: '{value}'")

    # Type checks
    bool_fields = ["is_prime", "is_sme", "is_featured"]
    for field in bool_fields:
        if field in data and not isinstance(data[field], bool):
            errors.append(
                f"Field '{field}' should be true/false, got: {type(data[field]).__name__}"
            )

    list_fields = [
        "stakeholders",
        "capability_streams",
        "capability_domains",
        "industrial_capabilities",
        "regions",
    ]
    for field in list_fields:
        if field in data and not isinstance(data[field], list):
            errors.append(
                f"Field '{field}' should be a list, got: {type(data[field]).__name__}"
            )

    return errors


def main() -> int:
    """Main entry point. Returns exit code."""
    if not COMPANIES_DIR.exists():
        print("ERROR: No data/companies directory found")
        print("  Run 'just scrape' first, or create company files manually")
        return 1

    yaml_files = sorted(COMPANIES_DIR.glob("*.yaml"))
    if not yaml_files:
        print("ERROR: No YAML files found in data/companies/")
        return 1

    taxonomies = load_taxonomies()

    total_errors = 0
    files_with_errors = 0

    for filepath in yaml_files:
        errors = lint_company(filepath, taxonomies)
        if errors:
            files_with_errors += 1
            total_errors += len(errors)
            print(f"\n{filepath.name}:")
            for error in errors:
                print(f"  - {error}")

    print(f"\n{'=' * 50}")
    print(f"Checked {len(yaml_files)} files")

    if total_errors == 0:
        print("All files OK")
        return 0
    else:
        print(f"Found {total_errors} error(s) in {files_with_errors} file(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
