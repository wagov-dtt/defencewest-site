"""Shared taxonomy utilities."""

from slugify import slugify


def get_short_key(text: str, existing_keys: set[str] | None = None) -> str:
    """Get short key for a taxonomy term.

    Uses first word of slugified text, adding more words if there's a conflict.

    Args:
        text: Display name to convert
        existing_keys: Set of already-used keys to check for conflicts
    """
    slug = slugify(text)
    parts = slug.split("-")
    existing = existing_keys or set()

    # Try progressively longer keys until unique
    for i in range(1, len(parts) + 1):
        key = "-".join(parts[:i])
        if key not in existing:
            return key

    # Fallback: full slug (shouldn't happen)
    return slug


def build_taxonomy_keys(names: list[str]) -> dict[str, str]:
    """Build short key -> display name mapping for a list of taxonomy values.

    Automatically handles conflicts by using longer keys.
    """
    result = {}
    used_keys = set()

    for name in sorted(names):
        key = get_short_key(name, used_keys)
        result[key] = name
        used_keys.add(key)

    return result
