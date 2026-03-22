from __future__ import annotations

import re
from typing import Final

from .constants import FRONTMATTER_RE

METADATA_LINE_RE: Final[re.Pattern[str]] = re.compile(r"^\s*[A-Za-z_][\w-]*\s*:")


def split_frontmatter(content: str) -> tuple[str, str]:
    """Split a document into top-frontmatter and body."""
    match = FRONTMATTER_RE.match(content)
    if not match:
        return "", content
    return match.group(0), content[match.end() :]


def rebuild_frontmatter(meta: str, had_trailing_newline: bool) -> str:
    """Build a normalized frontmatter block from metadata lines."""
    rebuilt = f"---\n{meta}\n---"
    if had_trailing_newline:
        rebuilt += "\n"
    return rebuilt


def is_metadata_line(line: str) -> bool:
    """Return True when a line looks like frontmatter metadata."""
    return bool(METADATA_LINE_RE.match(line))


def has_metadata_key(metadata: str, key: str) -> bool:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:", re.MULTILINE)
    return bool(pattern.search(metadata))


def set_metadata_key(metadata: str, key: str, value: str) -> str:
    """Set metadata key to value, replacing existing key or appending it."""
    key_pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*.*$", re.MULTILINE)
    if key_pattern.search(metadata):
        return key_pattern.sub(f"{key}: {value}", metadata, count=1)

    suffix = "" if metadata.endswith("\n") else "\n"
    return f"{metadata}{suffix}{key}: {value}"


def find_metadata_block(lines: list[str], start_index: int) -> tuple[int, str] | None:
    """Return (end_index, metadata_text) for a metadata block, or None."""
    if lines[start_index].strip() != "---":
        return None

    end_index = start_index + 1
    while end_index < len(lines) and lines[end_index].strip() != "---":
        end_index += 1

    if end_index >= len(lines):
        return None

    metadata_lines = lines[start_index + 1 : end_index]
    meaningful_lines = [line.strip() for line in metadata_lines if line.strip()]
    if not meaningful_lines or not all(is_metadata_line(line) for line in meaningful_lines):
        return None

    return end_index, "".join(metadata_lines)
