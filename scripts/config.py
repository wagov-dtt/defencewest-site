"""Shared configuration for all Python scripts.

Imports hugo.toml and exports common paths and constants.
"""

import logging
import os
import shutil
import sys
from pathlib import Path
import tomllib

import diskcache
from pathvalidate import sanitize_filename
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from slugify import slugify

# Logging setup
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger("defencewest")

# Paths
ROOT_DIR = Path(__file__).parent.parent
COMPANY_DIR = ROOT_DIR / "content" / "company"
DATA_DIR = ROOT_DIR / "data"
STATIC_DIR = ROOT_DIR / "static"
LOGOS_DIR = STATIC_DIR / "logos"
ICONS_DIR = STATIC_DIR / "icons"
CACHE_DIR = ROOT_DIR / ".cache"
MAPS_DIR = STATIC_DIR / "maps"
TERM_MAPS_DIR = MAPS_DIR / "terms"

# Load hugo.toml configuration
with open(ROOT_DIR / "hugo.toml", "rb") as f:
    hugo_toml = tomllib.load(f)

params = hugo_toml["params"]

# WA bounds from hugo.toml (minx, miny, maxx, maxy format)
WA_BOUNDS = params["waBounds"]


def is_in_wa(lat: float, lng: float) -> bool:
    """Check if coordinates are within Western Australia bounds."""
    return (
        WA_BOUNDS["miny"] <= lat <= WA_BOUNDS["maxy"]
        and WA_BOUNDS["minx"] <= lng <= WA_BOUNDS["maxx"]
    )


def make_progress() -> Progress:
    """Create a standard progress bar."""
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    )


# User agent for HTTP requests
USER_AGENT = f"{params['githubRepo']} (+https://github.com/{params['githubRepo']})"

# Check if mogrify (ImageMagick) is available for image optimization
HAS_MOGRIFY = shutil.which("mogrify") is not None

# Disk cache for HTTP responses
cache = diskcache.Cache(CACHE_DIR / "diskcache")

# Taxonomy names
TAXONOMIES = [
    "stakeholders",
    "capability_streams",
    "capability_domains",
    "industrial_capabilities",
    "regions",
    "ownerships",
]

# Map rendering settings
MAP_WIDTH = 420
MAP_HEIGHT = 240
MAP_MARKER_LAYERS = [
    {
        "id": "markers-border",
        "type": "circle",
        "source": "markers",
        "paint": {"circle-radius": 10, "circle-color": "#ffffff"},
    },
    {
        "id": "markers",
        "type": "circle",
        "source": "markers",
        "paint": {"circle-radius": 6, "circle-color": "#1095c1"},
    },
]

# Content processing
OVERVIEW_MAX_LENGTH = 300


def load_taxonomies() -> dict[str, list[str]]:
    """Load valid taxonomy keys from taxonomies.yaml.

    Returns dict of taxonomy_name -> list of valid keys.
    """
    taxonomies_path = DATA_DIR / "taxonomies.yaml"
    if not taxonomies_path.exists():
        return {}

    with open(taxonomies_path) as f:
        import yaml

        data = yaml.safe_load(f)

    # Return dict of taxonomy_name -> list of valid keys
    return {tax: list(data.get(tax, {}).keys()) for tax in TAXONOMIES if tax in data}


def validate_taxonomies(company: dict, valid_taxonomies: dict) -> list[str]:
    """Validate taxonomy values against allowed keys. Returns list of warnings."""
    warnings = []

    for taxonomy in TAXONOMIES:
        if values := company.get(taxonomy):
            valid_keys = valid_taxonomies.get(taxonomy, [])
            invalid = [v for v in values if v not in valid_keys]
            if invalid:
                warnings.append(f"Invalid {taxonomy}: {', '.join(invalid)}")

    return warnings


# Slug generation - suffixes to remove from company names
SLUG_REMOVE_SUFFIXES = [
    "-pty-ltd",
    "-pty-ltda",
    "-pty",
    "-ltd",
    "-ltda",
    "-limited",
    "-plc",
    "-co",
    "-inc",
    "-incorporated",
    "-corp",
    "-corporation",
    "-australia",
    "-aus",
    "-group",
    "-holdings",
    "-services",
    "-systems",
    "-solutions",
    "-technologies",
    "-technology",
    "-engineering",
    "-consulting",
    "-industries",
    "-enterprises",
    "-international",
    "-global",
    "-and-new-zealand",
]


# Capability stream acronym prefixes to remove (e.g., "AASL - Air and Sea Lift" -> "Air and Sea Lift")
CAPABILITY_STREAM_ACRONYMS = [
    "AASL - ",
    "ISCW - ",
    "KEYN - ",
    "LCAW - ",
    "MASW - ",
    "SAAC - ",
]


# Canonical capability streams from source HTML (filter dropdown values and display names)
# These are the 10 valid streams as defined in the source DOM
CANONICAL_CAPABILITY_STREAMS = {
    "aerial": "Aerial; Strike and Air Combat",
    "base": "Base Support",
    "education": "Education and Training",
    "electronic": "Electronic Warfare and Cyber",
    "intelligence": "Intelligence; Surveillance and Reconnaissance",
    "land": "Land Forces",
    "logistics": "Logistics and Supply Chain",
    "maritime": "Maritime and Sub-Sea Forces",
    "research": "Research and Technology Development",
    "space": "Space",
}


def clean_capability_stream(name: str) -> str:
    """Map old capability stream names to canonical taxonomy keys from source DOM.

    Returns canonical key for capability stream.
    """
    # Mapping from old prefixed stream names to canonical keys
    old_to_canonical_mapping = {
        "AASL - Air and Sea Lift": "logistics",
        "ISCW - Intelligence, Surveillance, Reconnaissance, Space, Electronic Warfare and Cyber": "electronic",
        "KEYN - Key Enablers": "research",
        "LCAW - Land Combat and Amphibious Warfare": "land",
        "MASW - Maritime and Anti-Submarine Warfare": "maritime",
        "SAAC - Strike and Air Combat": "aerial",
    }

    # Check for exact match with old prefixed names
    if name in old_to_canonical_mapping:
        return old_to_canonical_mapping[name]

    # Check for prefix match (handles variations)
    for old_name, canonical_key in old_to_canonical_mapping.items():
        if name.startswith(old_name):
            return canonical_key

    # For new streams, normalize to canonical key
    # Remove acronyms if present (shouldn't be needed for new streams)
    cleaned = name
    for old_name in old_to_canonical_mapping.keys():
        if cleaned.startswith(old_name):
            cleaned = cleaned[len(old_name) :]

    # Map cleaned name to canonical key by matching display names
    for key, display_name in CANONICAL_CAPABILITY_STREAMS.items():
        if cleaned == display_name or cleaned == display_name.lower():
            return key

    return cleaned


# Slug/key generation functions


def _get_short_key(text: str, existing_keys: set[str]) -> str:
    """Get short key for a taxonomy term (internal helper)."""
    slug = slugify(text)
    parts = slug.split("-")

    # Try progressively longer keys until unique
    for i in range(1, len(parts) + 1):
        key = "-".join(parts[:i])
        if key not in existing_keys:
            return key

    return slug


def build_taxonomy_keys(names: list[str]) -> dict[str, str]:
    """Build short key -> display name mapping for a list of taxonomy values."""
    result = {}
    used_keys: set[str] = set()

    for name in sorted(names):
        key = _get_short_key(name, used_keys)
        result[key] = name
        used_keys.add(key)

    return result


def clean_slug(name: str) -> str:
    """Generate a clean slug for company names.

    Removes common suffixes like 'Pty Ltd', 'Australia', etc.
    Uses pathvalidate for robust path traversal protection.
    """
    # Generate base slug
    slug = slugify(name)

    # Use pathvalidate to sanitize the slug for safe filename usage
    # This handles path traversal attacks, reserved names, and invalid chars
    slug = sanitize_filename(slug, replacement_text="-")

    # Remove common suffixes (keep removing until none match)
    changed = True
    while changed:
        changed = False
        for suffix in SLUG_REMOVE_SUFFIXES:
            if slug.endswith(suffix):
                remaining = slug[: -len(suffix)]
                if len(remaining) >= 2:
                    slug = remaining.rstrip("-")
                    changed = True
                    break

    # Truncate very long slugs
    if len(slug) > 30:
        parts = slug.split("-")
        if len(parts) > 3:
            slug = "-".join(parts[:3])

    # Final safety check: ensure slug is valid
    if not slug or slug in [".", "..", "-"]:
        slug = "invalid-name"

    return slug


def set_output(name: str, value: str):
    """Set GitHub Actions output variable."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            if "\n" in value:
                f.write(f"{name}<<EOF\n{value}\nEOF\n")
            else:
                f.write(f"{name}={value}\n")
    print(f"{name}: {value}", file=sys.stderr)
