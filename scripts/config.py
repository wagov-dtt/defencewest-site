"""Shared configuration for all Python scripts.

Imports hugo.toml and exports common paths and constants.
"""

import logging
import shutil
import subprocess
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


def html_to_markdown(html: str, *, strip_tables: bool = False) -> str:
    """Convert HTML to clean markdown.

    Args:
        html: HTML string to convert.
        strip_tables: If True, strip table elements (used when tables are layout wrappers).
    """
    from markdownify import markdownify as md_convert

    if not html:
        return ""

    strip_tags = ["script", "style"]
    if strip_tables:
        strip_tags.extend(["table", "tr", "td", "th", "tbody", "thead"])

    return md_convert(html, heading_style="ATX", bullets="-", strip=strip_tags).strip()


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


def optimize_image(
    input_path: Path, output_path: Path, resize: str = "520x120>"
) -> bool:
    """Optimize an image using mogrify, converting to PNG with resize and trim.

    Falls back to renaming the input file if mogrify is unavailable or fails.
    Returns True if the output file exists after processing.

    Args:
        input_path: Source image file (any format mogrify supports).
        output_path: Destination path (must end in .png).
        resize: ImageMagick resize geometry (default for logos, use "72x72>" for icons).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if HAS_MOGRIFY:
        try:
            subprocess.run(
                [
                    "mogrify",
                    "-format",
                    "PNG",
                    "-resize",
                    resize,
                    "-trim",
                    str(input_path),
                ],
                check=True,
                capture_output=True,
            )
            # mogrify -format PNG creates a .PNG file alongside the original
            mogrified = input_path.with_suffix(".PNG")
            if mogrified.exists() and mogrified != output_path:
                mogrified.rename(output_path)
            # Also check lowercase .png (mogrify behavior varies)
            mogrified_lower = input_path.with_suffix(".png")
            if mogrified_lower.exists() and mogrified_lower != output_path:
                mogrified_lower.rename(output_path)
            # Clean up original if different from output
            if input_path.exists() and input_path != output_path:
                input_path.unlink()
            return output_path.exists()
        except Exception as e:
            log.warning(f"Image optimize failed for {output_path}: {e}")

    # No mogrify or mogrify failed: just rename to output
    if input_path.exists() and not output_path.exists():
        input_path.rename(output_path)
    return output_path.exists()


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
    "company_types",
]

# Map rendering settings
# Logical display size 420x240, pixel_ratio=2 generates 840x480 for HiDPI
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


def load_taxonomies(*, raw: bool = False) -> dict:
    """Load taxonomy data from taxonomies.yaml.

    Args:
        raw: If True, return full dict of {taxonomy: {key: display_name}}.
             If False (default), return {taxonomy: [list of valid keys]}.
    """
    taxonomies_path = DATA_DIR / "taxonomies.yaml"
    if not taxonomies_path.exists():
        return {}

    with open(taxonomies_path) as f:
        import yaml

        data = yaml.safe_load(f) or {}

    if raw:
        return data

    # Return dict of taxonomy_name -> list of valid keys
    return {tax: list(data.get(tax, {}).keys()) for tax in TAXONOMIES if tax in data}


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

    # Map name to canonical key by matching display names
    for key, display_name in CANONICAL_CAPABILITY_STREAMS.items():
        if name == display_name or name == display_name.lower():
            return key

    return name


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
