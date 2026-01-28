#!/usr/bin/env python3
"""
Import a submission from local JSON file and create company files.

Usage:
    uv run python scripts/import_submission.py path/to/submission.json

Outputs:
    - content/company/{slug}.md (new or updated)
    - static/logos/{slug}.png (if logo included)

Exit codes:
    0: Success
    1: File not found or invalid JSON
    2: Validation failed
"""

import base64
import json
import re
import sys
from pathlib import Path

import yaml
from markdownify import markdownify as md

from config import COMPANY_DIR, LOGOS_DIR, TAXONOMIES, clean_slug, is_in_wa, set_output


def html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown."""
    return md(html, heading_style="ATX", bullets="-", strip=["script", "style"]).strip()


def validate_submission(submission: dict) -> tuple[bool, list[str]]:
    """Validate submission data. Returns (is_valid, warnings)."""
    warnings = []

    company = submission.get("company", {})
    if not company.get("name"):
        return False, ["Company name is required"]

    # Check content
    content = submission.get("content_html", "").strip()
    if not content or content == "<p><br></p>":
        warnings.append("No company description provided")

    # Warnings for recommended fields
    if not company.get("website"):
        warnings.append("No website provided")
    if not company.get("address"):
        warnings.append("No address provided")
    if not company.get("email") and not company.get("phone"):
        warnings.append("No contact information (email or phone)")

    # Check taxonomies
    has_any_taxonomy = any(company.get(t) for t in TAXONOMIES)
    if not has_any_taxonomy:
        warnings.append("No taxonomies selected")

    # Validate coordinates if provided
    lat = company.get("latitude")
    lng = company.get("longitude")
    if lat and lng:
        try:
            if not is_in_wa(float(lat), float(lng)):
                warnings.append(
                    f"Coordinates ({lat}, {lng}) are outside Western Australia"
                )
        except (ValueError, TypeError):
            warnings.append("Invalid coordinate format")

    return True, warnings


def build_markdown_file(submission: dict) -> str:
    """Build complete markdown file with YAML frontmatter."""
    company = submission["company"]

    # Build frontmatter
    frontmatter = {
        "name": company["name"],
        "date": submission.get("submitted_at", "")[:10] or "2025-01-01",
    }

    # Add optional scalar fields
    for field in [
        "website",
        "phone",
        "email",
        "address",
        "latitude",
        "longitude",
        "contact_name",
        "contact_title",
    ]:
        if company.get(field):
            frontmatter[field] = company[field]

    # Add boolean flags (only if true)
    for flag in ["is_sme", "is_prime"]:
        if company.get(flag):
            frontmatter[flag] = True

    # Add taxonomy lists
    for taxonomy in TAXONOMIES:
        if company.get(taxonomy):
            frontmatter[taxonomy] = company[taxonomy]

    # Convert HTML content to markdown
    content_md = html_to_markdown(submission.get("content_html", ""))

    # Build final file
    yaml_str = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
    ).strip()
    return f"---\n{yaml_str}\n---\n\n{content_md}\n"


def import_submission(submission: dict) -> tuple[str, str, bool, list[str]]:
    """
    Import a submission dict and create company files.

    Returns: (slug, company_name, is_new, warnings)
    """
    # Validate
    is_valid, warnings = validate_submission(submission)
    if not is_valid:
        raise ValueError(f"Validation failed: {warnings[0]}")

    company = submission["company"]
    company_name = company["name"]

    # Determine slug
    slug = submission.get("slug") or clean_slug(company_name)
    is_new = not (COMPANY_DIR / f"{slug}.md").exists()

    # Handle slug collision for new submissions
    if is_new:
        base_slug = slug
        counter = 2
        while (COMPANY_DIR / f"{slug}.md").exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

    # Save markdown file
    md_content = build_markdown_file(submission)
    md_path = COMPANY_DIR / f"{slug}.md"
    md_path.write_text(md_content)
    print(f"Saved: {md_path}", file=sys.stderr)

    # Save logo if provided
    if submission.get("logo"):
        logo_data = submission["logo"]
        match = re.match(r"data:image/\w+;base64,(.+)", logo_data)
        if match:
            logo_bytes = base64.b64decode(match.group(1))
            logo_path = LOGOS_DIR / f"{slug}.png"
            logo_path.write_bytes(logo_bytes)
            print(f"Saved: {logo_path}", file=sys.stderr)

    return slug, company_name, is_new, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: import_submission.py <json_file>", file=sys.stderr)
        return 1

    json_path = Path(sys.argv[1])

    if not json_path.exists():
        print(f"File not found: {json_path}", file=sys.stderr)
        return 1

    try:
        submission = json.loads(json_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1

    try:
        slug, company_name, is_new, warnings = import_submission(submission)

        # Set GitHub Actions outputs
        set_output("slug", slug)
        set_output("company_name", company_name)
        set_output("submission_type", "New listing" if is_new else "Update")
        set_output("commit_msg", f"{'feat' if is_new else 'fix'}: {company_name}")
        set_output("pr_title", f"{'Add' if is_new else 'Update'}: {company_name}")
        set_output("source_file", json_path.name)

        if warnings:
            warnings_md = "### Warnings\n" + "\n".join(f"- {w}" for w in warnings)
            set_output("warnings", warnings_md)
        else:
            set_output("warnings", "")

        return 0

    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
