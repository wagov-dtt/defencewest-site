#!/usr/bin/env python3
"""
Import a submission from local JSON file and create company files.

Usage:
    uv run python scripts/import_submission.py path/to/submission.json

Outputs:
    - content/company/{slug}.md (new or updated)
    - static/logos/{slug}.png (if logo provided)

GitHub Actions outputs:
    - slug: Company slug for URL
    - commit_msg: Git commit message

Exit codes:
    0: Success
    1: File not found or invalid JSON
    2: Validation failed
"""

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

import validators
import yaml
from markdownify import markdownify as md

from config import (
    COMPANY_DIR,
    LOGOS_DIR,
    TAXONOMIES,
    clean_slug,
    is_in_wa,
    set_output,
    HAS_MOGRIFY,
    load_taxonomies,
    validate_taxonomies,
)


def html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown."""
    return md(html, heading_style="ATX", bullets="-", strip=["script", "style"]).strip()


def save_logo_from_base64(slug: str, base64_data: str | None) -> bool:
    """Extract and save logo from base64 data, with mogrify optimization.

    Returns True if logo was saved successfully.
    """
    if not base64_data:
        return False

    try:
        # Handle data URI format (data:image/png;base64,...)
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]

        # Decode base64
        image_data = base64.b64decode(base64_data)

        # Determine file extension from data
        if image_data[:8] == b"\x89PNG\r\n\x1a\n":
            ext = "png"
        elif image_data[:2] == b"\xff\xd8":
            ext = "jpg"
        elif image_data[:4] == b"GIF8":
            ext = "gif"
        else:
            ext = "png"  # Default to PNG

        # Save to temporary file first
        temp_path = LOGOS_DIR / f"{slug}_temp.{ext}"
        LOGOS_DIR.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(image_data)

        # Apply mogrify optimization (same as scrape.py)
        if HAS_MOGRIFY:
            try:
                subprocess.run(
                    [
                        "mogrify",
                        "-format",
                        "PNG",
                        "-resize",
                        "520x120>",  # Max 520x120, only shrink
                        "-trim",
                        str(temp_path),
                    ],
                    check=True,
                    capture_output=True,
                )
                # mogrify creates {slug}_temp.png
                optimized_path = LOGOS_DIR / f"{slug}_temp.png"
                if optimized_path.exists():
                    # Rename to final name
                    final_path = LOGOS_DIR / f"{slug}.png"
                    optimized_path.rename(final_path)
                    print(f"Saved logo: {final_path}", file=sys.stderr)
                    return True
            except Exception as e:
                print(f"Warning: Image optimization failed: {e}", file=sys.stderr)
                # Fall back to unoptimized
                final_path = LOGOS_DIR / f"{slug}.png"
                temp_path.rename(final_path)
                print(f"Saved logo (unoptimized): {final_path}", file=sys.stderr)
                return True
        else:
            # No mogrify, just rename
            final_path = LOGOS_DIR / f"{slug}.png"
            temp_path.rename(final_path)
            print(f"Saved logo: {final_path}", file=sys.stderr)
            return True

    except Exception as e:
        print(f"Error saving logo: {e}", file=sys.stderr)
        return False

    return False

    try:
        # Handle data URI format (data:image/png;base64,...)
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]

        # Decode base64
        image_data = base64.b64decode(base64_data)

        # Determine file extension from data
        if image_data[:8] == b"\x89PNG\r\n\x1a\n":
            ext = "png"
        elif image_data[:2] == b"\xff\xd8":
            ext = "jpg"
        elif image_data[:4] == b"GIF8":
            ext = "gif"
        else:
            ext = "png"  # Default to PNG

        # Save to temporary file first
        temp_path = LOGOS_DIR / f"{slug}_temp.{ext}"
        LOGOS_DIR.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(image_data)

        # Apply mogrify optimization (same as scrape.py)
        if HAS_MOGRIFY:
            try:
                subprocess.run(
                    [
                        "mogrify",
                        "-format",
                        "PNG",
                        "-resize",
                        "520x120>",  # Max 520x120, only shrink
                        "-trim",
                        str(temp_path),
                    ],
                    check=True,
                    capture_output=True,
                )
                # mogrify creates {slug}_temp.png
                optimized_path = LOGOS_DIR / f"{slug}_temp.png"
                if optimized_path.exists():
                    # Rename to final name
                    final_path = LOGOS_DIR / f"{slug}.png"
                    optimized_path.rename(final_path)
                    print(f"Saved logo: {final_path}", file=sys.stderr)
                    return True
            except Exception as e:
                print(f"Warning: Image optimization failed: {e}", file=sys.stderr)
                # Fall back to unoptimized
                final_path = LOGOS_DIR / f"{slug}.png"
                temp_path.rename(final_path)
                print(f"Saved logo (unoptimized): {final_path}", file=sys.stderr)
                return True
        else:
            # No mogrify, just rename
            final_path = LOGOS_DIR / f"{slug}.png"
            temp_path.rename(final_path)
            print(f"Saved logo: {final_path}", file=sys.stderr)
            return True

    except Exception as e:
        print(f"Error saving logo: {e}", file=sys.stderr)
        return False


def find_duplicate_companies(
    company_name: str, exclude_slug: str | None = None
) -> list[str]:
    """Find existing companies with similar names. Returns list of matching slugs."""
    duplicates = []
    name_lower = company_name.lower()

    for md_file in COMPANY_DIR.glob("*.md"):
        if exclude_slug and md_file.stem == exclude_slug:
            continue

        try:
            content = md_file.read_text()
            # Extract name from frontmatter
            if match := re.search(r"^name:\s*(.+)$", content, re.MULTILINE):
                existing_name = match.group(1).strip()
                existing_lower = existing_name.lower()

                # Check for exact match or high similarity
                if existing_lower == name_lower:
                    duplicates.append(
                        f"{md_file.stem} (exact match: '{existing_name}')"
                    )
                elif name_lower in existing_lower or existing_lower in name_lower:
                    duplicates.append(f"{md_file.stem} (similar: '{existing_name}')")
        except Exception:
            continue

    return duplicates


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
    elif website := company.get("website"):
        # Validate URL format (validators returns True on success, ValidationError on failure)
        if validators.url(website) is not True:
            warnings.append(f"Invalid website URL format: {website}")

    if not company.get("address"):
        warnings.append("No address provided")

    if not company.get("email") and not company.get("phone"):
        warnings.append("No contact information (email or phone)")
    elif email := company.get("email"):
        # Validate email format (validators returns True on success, ValidationError on failure)
        if validators.email(email) is not True:
            warnings.append(f"Invalid email format: {email}")

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


def sanitize_for_git(text: str) -> str:
    """Sanitize text for use in git commit messages and PR titles.

    Removes special characters that could cause issues.
    """
    # Remove newlines and control characters
    text = re.sub(r"[\r\n\x00-\x1f\x7f]", "", text)
    # Remove backticks and quotes that could break shell commands
    text = text.replace("`", "").replace('"', "").replace("'", "")
    # Limit length
    return text[:100]


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

    # Determine slug - only preserve existing slug for updates, otherwise use clean_slug
    is_update = submission.get("type") == "update" and submission.get("slug")
    slug = submission["slug"] if is_update else clean_slug(company_name)
    is_new = not (COMPANY_DIR / f"{slug}.md").exists()

    # Handle slug collision for new submissions
    if is_new:
        base_slug = slug
        counter = 2
        while (COMPANY_DIR / f"{slug}.md").exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

    # Load and validate taxonomies
    valid_taxonomies = load_taxonomies()
    taxonomy_warnings = validate_taxonomies(company, valid_taxonomies)
    warnings.extend(taxonomy_warnings)

    # Check for duplicate companies
    existing_slug = None if is_new else slug
    duplicates = find_duplicate_companies(company_name, exclude_slug=existing_slug)
    if duplicates:
        warnings.append(f"Potential duplicates found: {', '.join(duplicates)}")

    # Save logo if provided
    if logo_data := submission.get("logo"):
        if not save_logo_from_base64(slug, logo_data):
            warnings.append("Failed to save logo")

    # Save markdown file
    md_content = build_markdown_file(submission)
    md_path = COMPANY_DIR / f"{slug}.md"
    md_path.write_text(md_content)
    print(f"Saved: {md_path}", file=sys.stderr)

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

        # Set GitHub Actions outputs (sanitized for security)
        safe_name = sanitize_for_git(company_name)
        set_output("slug", slug)
        set_output("commit_msg", f"{'feat' if is_new else 'fix'}: {safe_name}")

        # Log warnings to stderr (not needed in PR body anymore)
        if warnings:
            for w in warnings:
                print(f"Warning: {w}", file=sys.stderr)

        return 0

    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
