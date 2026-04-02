"""Shared configuration for Python scripts."""

from pathlib import Path
import tomllib

import diskcache
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

ROOT_DIR = Path(__file__).parent.parent
COMPANY_DIR = ROOT_DIR / "content" / "company"
DATA_DIR = ROOT_DIR / "data"
STATIC_DIR = ROOT_DIR / "static"
LOGOS_DIR = STATIC_DIR / "logos"
CACHE_DIR = ROOT_DIR / ".cache"
MAPS_DIR = STATIC_DIR / "maps"
TERM_MAPS_DIR = MAPS_DIR / "terms"

with open(ROOT_DIR / "hugo.toml", "rb") as f:
    hugo_toml = tomllib.load(f)

params = hugo_toml["params"]


def make_progress() -> Progress:
    """Create a standard progress bar."""
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    )


cache = diskcache.Cache(CACHE_DIR / "diskcache")

TAXONOMIES = [
    "stakeholders",
    "capability_streams",
    "capability_domains",
    "industrial_capabilities",
    "regions",
    "ownerships",
    "company_types",
]

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
    """Load taxonomy data from data/taxonomies.yaml."""
    taxonomies_path = DATA_DIR / "taxonomies.yaml"
    if not taxonomies_path.exists():
        return {}

    with open(taxonomies_path) as f:
        import yaml

        data = yaml.safe_load(f) or {}

    if raw:
        return data

    return {tax: list(data.get(tax, {}).keys()) for tax in TAXONOMIES if tax in data}
