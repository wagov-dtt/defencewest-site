#!/usr/bin/env python3
"""Fail fast on company/content naming mismatches that break Hugo links/assets."""

from __future__ import annotations

from collections import defaultdict
import re
import sys
from pathlib import Path

import frontmatter
from slugify import slugify

from config import COMPANY_DIR, LOGOS_DIR, ROOT_DIR

KEBAB_STEM_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def rel(path: Path) -> str:
    """Return a stable repo-relative path for diagnostics."""
    return path.relative_to(ROOT_DIR).as_posix()


def iter_company_files() -> list[Path]:
    """Return company markdown files that participate in Hugo page generation."""
    return sorted(
        path
        for path in COMPANY_DIR.glob("*.md")
        if path.is_file() and not path.name.startswith("_")
    )


def load_company_name(path: Path) -> str:
    """Best-effort company name for friendlier diagnostics."""
    try:
        post = frontmatter.load(str(path))
    except Exception:
        return path.stem

    return str(post.metadata.get("name") or path.stem).strip() or path.stem


def build_logo_index() -> dict[str, list[Path]]:
    """Group logo files by normalized stem so case/spacing mistakes are detectable."""
    index: dict[str, list[Path]] = defaultdict(list)

    if not LOGOS_DIR.exists():
        return index

    for path in sorted(LOGOS_DIR.iterdir()):
        if not path.is_file():
            continue
        index[slugify(path.stem)].append(path)

    return index


def validate() -> list[str]:
    """Return validation errors for slug/logo mismatches Hugo will not resolve."""
    errors: list[str] = []
    logo_index = build_logo_index()
    seen_normalized_stems: dict[str, Path] = {}

    for path in iter_company_files():
        company_name = load_company_name(path)
        actual_stem = path.stem
        normalized_stem = slugify(actual_stem)

        if not KEBAB_STEM_RE.fullmatch(actual_stem):
            errors.append(
                f"{rel(path)} must use a lowercase kebab-case filename stem like "
                f"{normalized_stem!r}; current stem {actual_stem!r} breaks Hugo-generated internal links"
            )

        previous = seen_normalized_stems.get(normalized_stem)
        if previous and previous != path:
            errors.append(
                f"{rel(path)} and {rel(previous)} normalize to the same slug {normalized_stem!r}; "
                "keep only one canonical filename"
            )
        else:
            seen_normalized_stems[normalized_stem] = path

        expected_logo = LOGOS_DIR / f"{actual_stem}.png"
        if expected_logo.exists():
            continue

        alt_logos = [
            candidate
            for candidate in logo_index.get(actual_stem, [])
            if candidate.name != expected_logo.name
        ]
        if alt_logos:
            errors.append(
                f"logo for {company_name!r} must be named {rel(expected_logo)}; found "
                + ", ".join(rel(candidate) for candidate in alt_logos)
            )

    return errors


def main() -> int:
    errors = validate()
    if not errors:
        print("Hugo content validation passed.")
        return 0

    print("Hugo content validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
