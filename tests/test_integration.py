#!/usr/bin/env python3
"""Integration tests for scripts - verify they run without errors."""

import subprocess
import sys
from pathlib import Path


def test_scrape_runs():
    """Verify scrape.py runs without errors (uses cached data)."""
    print("Testing scrape.py...")

    result = subprocess.run(
        ["uv", "run", "python", "scripts/scrape.py"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        timeout=120,
    )

    if result.returncode != 0:
        print(f"✗ Scrape failed with return code {result.returncode}")
        print(f"  stderr: {result.stderr.decode()}")
        return False

    if result.stderr:
        print(f"✗ Scrape produced stderr: {result.stderr.decode()}")
        return False

    print("✓ Scrape runs successfully")
    return True


def test_export_runs():
    """Verify export.py runs without errors."""
    print("Testing export.py...")

    result = subprocess.run(
        ["uv", "run", "python", "scripts/export.py"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        timeout=60,
    )

    if result.returncode != 0:
        print(f"✗ Export failed with return code {result.returncode}")
        print(f"  stderr: {result.stderr.decode()}")
        return False

    if result.stderr:
        print(f"✗ Export produced stderr: {result.stderr.decode()}")
        return False

    print("✓ Export runs successfully")
    return True


def test_preprocess_runs():
    """Verify preprocess.py runs without errors."""
    print("Testing preprocess.py...")

    result = subprocess.run(
        ["uv", "run", "python", "scripts/preprocess.py"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        timeout=60,
    )

    if result.returncode != 0:
        print(f"✗ Preprocess failed with return code {result.returncode}")
        print(f"  stderr: {result.stderr.decode()}")
        return False

    if result.stderr:
        print(f"✗ Preprocess produced stderr: {result.stderr.decode()}")
        return False

    print("✓ Preprocess runs successfully")
    return True


if __name__ == "__main__":
    print("Running integration tests...\n")

    passed = []
    passed.append(test_preprocess_runs())
    passed.append(test_scrape_runs())
    passed.append(test_export_runs())

    if all(passed):
        print("\n✓ All tests passed")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
