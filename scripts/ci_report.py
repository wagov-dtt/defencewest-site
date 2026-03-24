#!/usr/bin/env python3
"""Generate clearer GitHub Actions annotations, summaries, and CI artifacts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / ".ci-reports"
BUILD_LOG = ROOT / "build.log"
LINKCHECK_JSON = REPORTS_DIR / "linkcheck" / "lychee-report.json"
A11Y_JSON = REPORTS_DIR / "a11y" / "pa11y-report.json"
A11Y_LOG = REPORTS_DIR / "a11y" / "a11y.log"


def ensure_reports_dir() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def append_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def gh_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def annotate(level: str, message: str, *, file: str | None = None) -> None:
    prefix = f"::{level}"
    if file:
        prefix += f" file={gh_escape(file)}"
    prefix += f"::{gh_escape(message)}"
    print(prefix)


def group(title: str) -> None:
    print(f"::group::{title}")


def endgroup() -> None:
    print("::endgroup::")


def read_log_tail(path: Path, *, limit: int = 20) -> list[str]:
    if not path.exists():
        return []
    lines = [line.rstrip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
    lines = [line for line in lines if line]
    return lines[-limit:]


def parse_build_log(path: Path) -> dict[str, object]:
    data: dict[str, object] = {
        "warnings": [],
        "errors": [],
    }
    if not path.exists():
        return data

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.rstrip()
        if line.startswith("WARN"):
            cast = data["warnings"]
            assert isinstance(cast, list)
            cast.append(line)
        elif line.startswith("ERROR"):
            cast = data["errors"]
            assert isinstance(cast, list)
            cast.append(line)

    return data


def summarize_build() -> int:
    build_outcome = os.environ.get("BUILD_OUTCOME", "unknown")
    parsed = parse_build_log(BUILD_LOG)
    warnings = parsed["warnings"]
    errors = parsed["errors"]
    assert isinstance(warnings, list)
    assert isinstance(errors, list)

    group("CI diagnostics: build")
    if warnings:
        print(f"Found {len(warnings)} build warnings")
        for line in warnings[:20]:
            annotate("warning", line)
        if len(warnings) > 20:
            annotate("notice", f"Suppressed {len(warnings) - 20} additional build warnings; see build.log artifact")
    else:
        print("No build warnings found")

    if errors:
        print(f"Found {len(errors)} build errors")
        for line in errors[:20]:
            annotate("error", line)
        if len(errors) > 20:
            annotate("notice", f"Suppressed {len(errors) - 20} additional build errors; see build.log artifact")
    else:
        print("No build errors found")
    if build_outcome in {"failure", "cancelled"}:
        annotate("error", "Build step failed. See the build log tail below and download the ci-diagnostics-build artifact for full logs.")
        tail_lines = read_log_tail(BUILD_LOG)
        if tail_lines:
            group("CI diagnostics: build log tail")
            for line in tail_lines:
                print(line)
            endgroup()
    endgroup()

    summary_lines = [
        "## Build diagnostics",
        "",
        f"- Build outcome: {build_outcome}",
        f"- Build warnings: {len(warnings)}",
        f"- Build errors: {len(errors)}",
    ]
    append_summary(summary_lines)
    return len(errors)


def _status_code_text(status: dict[str, object]) -> str:
    code = status.get("code")
    text = str(status.get("text") or "Error")
    return f"{code} {text}" if code is not None else text


def summarize_linkcheck() -> int:
    if not LINKCHECK_JSON.exists():
        append_summary([
            "## Link check",
            "",
            "- Link check report not found.",
        ])
        return 0

    report = json.loads(LINKCHECK_JSON.read_text(encoding="utf-8"))
    error_map = report.get("error_map") or {}
    errors = int(report.get("errors") or 0)
    total = int(report.get("total") or 0)

    group("CI diagnostics: link check")
    if errors:
        print(f"Link checker reported {errors} errors across {len(error_map)} files")
    else:
        print("Link checker reported no errors")

    top_entries = sorted(error_map.items(), key=lambda item: (-len(item[1]), item[0]))[:20]
    for input_path, issues in top_entries:
        if not issues:
            continue
        first = issues[0]
        status = _status_code_text(first.get("status") or {})
        url = first.get("url") or "unknown URL"
        extra = ""
        if len(issues) > 1:
            extra = f" (+{len(issues) - 1} more)"
        annotate("warning", f"{input_path}: {status}: {url}{extra}")

    remaining = max(len(error_map) - len(top_entries), 0)
    if remaining:
        annotate("notice", f"Suppressed link diagnostics for {remaining} additional files; see lychee-report.json artifact")
    endgroup()

    summary_lines = [
        "## Link check",
        "",
        f"- Total links checked: {total}",
        f"- Broken/external errors: {errors}",
        "- Full report artifact: `ci-diagnostics-build`",
    ]
    if error_map:
        summary_lines.extend([
            "",
            "Top failing files:",
            "",
            "| File | First failing URL | Status |",
            "|---|---|---|",
        ])
        for input_path, issues in top_entries[:10]:
            if not issues:
                continue
            first = issues[0]
            url = str(first.get("url") or "unknown URL")
            status = _status_code_text(first.get("status") or {})
            summary_lines.append(f"| `{input_path}` | `{url}` | {status} |")
    append_summary(summary_lines)
    return errors


def summarize_a11y() -> int:
    a11y_outcome = os.environ.get("A11Y_OUTCOME", "unknown")
    if not A11Y_JSON.exists():
        summary_lines = [
            "## Accessibility",
            "",
            f"- Accessibility outcome: {a11y_outcome}",
            "- Accessibility JSON report not found.",
        ]
        tail_lines = read_log_tail(A11Y_LOG)
        if a11y_outcome in {"failure", "cancelled"} and tail_lines:
            group("CI diagnostics: accessibility log tail")
            for line in tail_lines:
                print(line)
            endgroup()
            summary_lines.extend(["", "Recent log tail:", ""])
            summary_lines.extend(f"- `{line}`" for line in tail_lines[-10:])
        append_summary(summary_lines)
        return 0

    report = json.loads(A11Y_JSON.read_text(encoding="utf-8"))
    total = int(report.get("total") or 0)
    passes = int(report.get("passes") or 0)
    errors = int(report.get("errors") or 0)
    results = report.get("results") or {}

    group("CI diagnostics: accessibility")
    if errors:
        print(f"Accessibility checks reported {errors} issues across {len(results)} pages")
    else:
        print("Accessibility checks reported no issues")

    failing_pages = []
    for page_url, issues in results.items():
        if not issues:
            continue
        failing_pages.append((page_url, issues))
    failing_pages.sort(key=lambda item: (-len(item[1]), item[0]))

    for page_url, issues in failing_pages[:20]:
        first = issues[0]
        if isinstance(first, dict):
            code = first.get("code") or "issue"
            message = first.get("message") or "Accessibility issue"
            context = first.get("context") or ""
            details = f"{code}: {message}"
            if context:
                details += f" | context: {context}"
            annotate("warning", f"{page_url}: {details}")
        else:
            annotate("warning", f"{page_url}: {first}")

    remaining = max(len(failing_pages) - 20, 0)
    if remaining:
        annotate("notice", f"Suppressed accessibility diagnostics for {remaining} additional pages; see pa11y-report.json artifact")
    endgroup()

    summary_lines = [
        "## Accessibility",
        "",
        f"- Accessibility outcome: {a11y_outcome}",
        f"- Pages tested: {total}",
        f"- Pages passing: {passes}",
        f"- Total issues: {errors}",
        "- Full report artifact: `ci-diagnostics-a11y`",
    ]
    if failing_pages:
        summary_lines.extend([
            "",
            "Top failing pages:",
            "",
            "| Page | First issue |",
            "|---|---|",
        ])
        for page_url, issues in failing_pages[:10]:
            first = issues[0]
            if isinstance(first, dict):
                message = str(first.get("message") or first.get("code") or "Accessibility issue")
            else:
                message = str(first)
            message = message.replace("|", "\\|")
            summary_lines.append(f"| `{page_url}` | {message} |")
    append_summary(summary_lines)
    return errors


def main(argv: list[str]) -> int:
    ensure_reports_dir()
    if len(argv) != 2:
        print("usage: ci_report.py [build|linkcheck|a11y]", file=sys.stderr)
        return 2

    mode = argv[1]
    if mode == "build":
        summarize_build()
        return 0
    if mode == "linkcheck":
        summarize_linkcheck()
        return 0
    if mode == "a11y":
        summarize_a11y()
        return 0

    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
