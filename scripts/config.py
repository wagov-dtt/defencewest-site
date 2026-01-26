"""Shared configuration for all Python scripts.

Imports hugo.toml and exports common paths and constants.
"""

import logging
import shutil
from pathlib import Path
import tomllib

import diskcache
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

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


# Slug/key generation functions
from slugify import slugify


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
    """
    slug = slugify(name)

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

    return slug
