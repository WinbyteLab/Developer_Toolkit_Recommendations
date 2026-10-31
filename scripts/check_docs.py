#!/usr/bin/env python3
"""Check numeric source maps and repository-local Markdown links."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "_audit", "node_modules", ".venv"}
SKIP_NAMES = {"WORKLOG.md"}
SOURCE_HEADING = re.compile(r"(?m)^## Sources\s*$")
CITATION_RE = re.compile(r"(?<!\!)\[(\d+)\]")
SOURCE_LINE_RE = re.compile(r"^\[(\d+)\]\s+(https?://\S+)\s*$")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
FENCED_CODE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if path.name not in SKIP_NAMES
        and not any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts)
    )


def check_source_map(path: Path, text: str) -> list[str]:
    match = SOURCE_HEADING.search(text)
    citation_text = text[: match.start()] if match else text
    citation_text = INLINE_CODE_RE.sub("", FENCED_CODE_RE.sub("", citation_text))
    cited = set(CITATION_RE.findall(citation_text))
    if cited and not match:
        return [f"{path.relative_to(ROOT)}: numeric citations found, but '## Sources' is missing"]
    if not match:
        return []

    found: dict[str, str] = {}
    duplicates: list[str] = []
    for line in text[match.end() :].splitlines():
        item = SOURCE_LINE_RE.match(line.strip())
        if not item:
            continue
        source_id, url = item.groups()
        if source_id in found:
            duplicates.append(source_id)
        found[source_id] = url

    errors: list[str] = []
    if duplicates:
        errors.append(
            f"{path.relative_to(ROOT)}: duplicate source IDs: "
            f"{', '.join(sorted(set(duplicates), key=int))}"
        )
    missing = sorted(cited - set(found), key=int)
    unused = sorted(set(found) - cited, key=int)
    if missing:
        errors.append(
            f"{path.relative_to(ROOT)}: citations missing from Sources: "
            f"{', '.join(missing)}"
        )
    if unused:
        errors.append(
            f"{path.relative_to(ROOT)}: Sources entries not cited in text: "
            f"{', '.join(unused)}"
        )
    return errors


def check_local_links(path: Path, text: str) -> list[str]:
    text = INLINE_CODE_RE.sub("", FENCED_CODE_RE.sub("", text))
    errors: list[str] = []
    root = ROOT.resolve()
    for target in MARKDOWN_LINK_RE.findall(text):
        target = target.strip().strip("<>")
        if not target or target.startswith("#"):
            continue
        if WINDOWS_ABSOLUTE_PATH_RE.match(target) or target.startswith("\\\\"):
            errors.append(
                f"{path.relative_to(ROOT)}: machine-specific absolute link is not allowed: {target}"
            )
            continue

        parts = urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        relative_path = Path(unquote(parts.path))
        if relative_path.is_absolute():
            resolved = (root / str(relative_path).lstrip("/\\")).resolve()
        else:
            resolved = (path.parent / relative_path).resolve()

        try:
            resolved.relative_to(root)
        except ValueError:
            errors.append(
                f"{path.relative_to(ROOT)}: local link escapes repository root: {target}"
            )
            continue
        if not resolved.exists():
            errors.append(
                f"{path.relative_to(ROOT)}: local link target does not exist: {target}"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    files = markdown_files()
    for path in files:
        text = path.read_text(encoding="utf-8")
        errors.extend(check_source_map(path, text))
        errors.extend(check_local_links(path, text))
    if errors:
        print("Documentation checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Documentation checks passed for {len(files)} Markdown files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
