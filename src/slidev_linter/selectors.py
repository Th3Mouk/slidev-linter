from __future__ import annotations

import argparse
import glob
import re
from pathlib import Path

from .engine import Selector


def parse_range(range_value: str) -> tuple[int, int] | None:
    """Parse chapter range values like '20-29'."""
    range_match = re.match(r"^(\d+)-(\d+)$", range_value)
    if not range_match:
        return None

    start = int(range_match.group(1))
    end = int(range_match.group(2))
    if start > end:
        return None

    return start, end


def expand_file_arg(file_arg: str, slides_dir: str) -> list[str]:
    """Resolve file selector value as explicit file path or glob pattern."""
    slides_path = Path(slides_dir)
    if Path(file_arg).is_absolute():
        candidates = [Path(file_arg)]
    else:
        candidates = [Path(file_arg), slides_path / file_arg]

    for candidate in candidates:
        if candidate.is_file() and candidate.suffix == ".md":
            return [str(candidate)]

    matched_files: list[str] = []
    for candidate in candidates:
        matched_files.extend(glob.glob(str(candidate)))

    return sorted({path for path in matched_files if Path(path).is_file() and path.endswith(".md")})


def _sorted_markdown_paths(paths: list[Path]) -> list[str]:
    return sorted(str(path) for path in paths if path.is_file() and path.suffix == ".md")


def collect_files_to_process(selector: Selector, slides_dir: str) -> tuple[list[str], str | None]:
    """Return selected markdown files plus optional user-facing error."""
    slides_path = Path(slides_dir)

    if selector.kind == "file":
        files = expand_file_arg(selector.value, slides_dir)
        if files:
            return files, None
        return [], f"File selector did not match any markdown file: {selector.value}."

    if selector.kind == "pattern":
        files = _sorted_markdown_paths(list(slides_path.glob(selector.value)))
        if files:
            return files, None
        return [], f"Pattern selector did not match any markdown file: {selector.value}."

    if selector.kind == "chapter":
        chapter = int(selector.value)
        chapter_pattern = f"{chapter:02d}-*.md"
        files = _sorted_markdown_paths(list(slides_path.rglob(chapter_pattern)))
        if files:
            return files, None
        return [], f"Chapter selector found no files for chapter: {chapter}."

    if selector.kind == "range":
        parsed_range = parse_range(selector.value)
        if not parsed_range:
            return (
                [],
                f"Invalid range '{selector.value}'. Expected '<start>-<end>' like "
                "'20-29' with start <= end.",
            )

        start, end = parsed_range
        paths: list[Path] = []
        for chapter in range(start, end + 1):
            paths.extend(slides_path.rglob(f"{chapter:02d}-*.md"))

        files = _sorted_markdown_paths(paths)
        if files:
            return files, None
        return [], f"Range selector found no files for range: {selector.value}."

    if selector.kind == "all":
        files = _sorted_markdown_paths(list(slides_path.rglob("[0-9][0-9]-*.md")))
        if files:
            return files, None
        return [], "No files found for selector 'all'."

    return [], f"Unknown selector kind: {selector.kind}."


def selector_from_args(args: argparse.Namespace) -> Selector:
    return Selector(kind=args.selector_kind, value=args.selector_value)
