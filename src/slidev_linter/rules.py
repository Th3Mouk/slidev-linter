from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Final
from uuid import uuid4

from .constants import DEFAULT_TRANSITION, FRONTMATTER_RE, SECTION_TRANSITION

SPACING_TAG: Final[str] = '<p class="py-2"/>'


class Rule(ABC):
    """Abstract base class for defining a linting rule."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.enabled = True

    @abstractmethod
    def apply(self, content: str) -> str:
        """Apply the rule to the content and return the modified content."""

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


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
    return bool(re.match(r"^\s*[A-Za-z_][\w-]*\s*:", line))


class RemoveBoldFromTitlesRule(Rule):
    """Rule to remove bold formatting from titles."""

    def __init__(self) -> None:
        super().__init__(
            "remove_bold_from_titles",
            "Removes bold formatting from titles (# **Title** -> # Title)",
        )

    def apply(self, content: str) -> str:
        """Remove bold formatting from titles."""
        return re.sub(r"(#\s+)\*\*(.*?)\*\*", r"\1\2", content)


class DefaultTransitionRule(Rule):
    """Rule to ensure the default transition in the header is 'slide-left'."""

    def __init__(self) -> None:
        super().__init__(
            "default_transition",
            "Ensures the default transition in the header is 'slide-left'",
        )

    def apply(self, content: str) -> str:
        """Ensure the default transition in the header is 'slide-left'."""
        frontmatter, body = split_frontmatter(content)
        if not frontmatter:
            return content

        frontmatter_match = re.match(r"^---\s*\n(?P<meta>.*?)\n---\s*\n?$", frontmatter, re.DOTALL)
        if not frontmatter_match:
            return content

        metadata = frontmatter_match.group("meta")
        if not re.search(r"^\s*transition\s*:", metadata, re.MULTILINE):
            suffix = "" if metadata.endswith("\n") else "\n"
            new_metadata = f"{metadata}{suffix}transition: {DEFAULT_TRANSITION}"
        else:
            new_metadata = re.sub(
                r"^\s*transition\s*:\s*.*$",
                f"transition: {DEFAULT_TRANSITION}",
                metadata,
                count=1,
                flags=re.MULTILINE,
            )

        if new_metadata == metadata:
            return content

        rebuilt = rebuild_frontmatter(new_metadata, frontmatter.endswith("\n"))
        return rebuilt + body


class SectionTransitionRule(Rule):
    """Rule to enforce a specific transition on section slides."""

    def __init__(self, transition: str = SECTION_TRANSITION) -> None:
        super().__init__(
            "section_transition",
            f"Adds 'transition: {transition}' for slides with layout 'section'",
        )
        self.transition = transition

    def apply(self, content: str) -> str:
        """Add or fix transition for metadata blocks with layout: section."""
        lines = content.splitlines(keepends=True)
        output: list[str] = []
        index = 0

        while index < len(lines):
            current_line = lines[index]
            if current_line.strip() != "---":
                output.append(current_line)
                index += 1
                continue

            end = index + 1
            while end < len(lines) and lines[end].strip() != "---":
                end += 1

            if end >= len(lines):
                output.append(current_line)
                index += 1
                continue

            metadata_lines = lines[index + 1 : end]
            meaningful_lines = [line.strip() for line in metadata_lines if line.strip()]

            if not meaningful_lines or not all(is_metadata_line(line) for line in meaningful_lines):
                output.append(current_line)
                index += 1
                continue

            metadata = "".join(metadata_lines)
            if not re.search(r"^\s*layout\s*:\s*section\s*$", metadata, re.MULTILINE):
                output.append(current_line)
                index += 1
                continue

            if re.search(r"^\s*transition\s*:", metadata, re.MULTILINE):
                updated_metadata = re.sub(
                    r"^\s*transition\s*:\s*.*$",
                    f"transition: {self.transition}",
                    metadata,
                    count=1,
                    flags=re.MULTILINE,
                )
            else:
                suffix = "" if metadata.endswith("\n") else "\n"
                updated_metadata = f"{metadata}{suffix}transition: {self.transition}\n"

            output.append(current_line)
            output.append(updated_metadata)
            output.append(lines[end])
            index = end + 1

        return "".join(output)


class CleanTransitionsRule(Rule):
    """Rule to clean up duplicate or misplaced transitions."""

    def __init__(self) -> None:
        super().__init__(
            "clean_transitions",
            "Cleans up duplicate or misplaced transitions",
        )

    def apply(self, content: str) -> str:
        """Clean up duplicate or misplaced transitions."""
        frontmatter, body = split_frontmatter(content)

        body = re.sub(
            r"(?m)^---\s*\ntransition:\s*[\w-]+[ \t]*\n(?=#)",
            "---\n\n",
            body,
        )
        body = re.sub(r"(?m)(\n---[ \t]*\n)(?!\n|layout:|transition:)", r"\1\n", body)
        body = re.sub(r"(<p class=\"py-2\"/>\s*\n){2,}", '<p class="py-2"/>\n', body)

        if frontmatter:
            return frontmatter + body.lstrip("\n")

        return re.sub(r"^---\s*\n\s*\n", "---\n", body)


class EnsureSpaceBetweenTitleAndSubtitleRule(Rule):
    """Rule to ensure there is a blank line between a title and its subtitle."""

    def __init__(self) -> None:
        super().__init__(
            "ensure_space_between_title_subtitle",
            "Ensures there is a blank line between a title (#) and its subtitle (##)",
        )

    def apply(self, content: str) -> str:
        """Ensure there is a blank line between a title and its subtitle."""
        return re.sub(r"(^#\s+.*$)\n(^##\s+.*$)", r"\1\n\n\2", content, flags=re.MULTILINE)


class AddSpacingAfterTitlesRule(Rule):
    """Rule to add a customizable HTML spacing tag after level 1 titles."""

    def __init__(self, tag: str = SPACING_TAG) -> None:
        self.tag = tag
        super().__init__(
            "add_spacing_after_titles",
            f"Adds an HTML tag {tag} after level 1 titles, except before tables",
        )

    def apply(self, content: str) -> str:
        """Add a customizable spacing tag after level 1 titles."""
        frontmatter, body = split_frontmatter(content)
        if not frontmatter:
            return content

        tag_escaped = re.escape(self.tag)
        token_prefix = f"__SLIDEV_NOTE_{uuid4().hex}__"
        presenter_notes: list[str] = []

        def save_presenter_note(match: re.Match[str]) -> str:
            presenter_notes.append(match.group(0))
            return f"{token_prefix}{len(presenter_notes) - 1}__"

        body_without_notes = re.sub(r"<!--[\s\S]*?-->", save_presenter_note, body)
        slides = re.split(r"\n---\s*\n", body_without_notes)

        if len(slides) > 1:
            for i in range(1, len(slides)):
                if re.match(r"^\s*#\s+[^\n]+\s*$", slides[i].strip()):
                    continue

                slides[i] = re.sub(
                    r"(^|\n)(#\s+[^\n]+\n)(?!\s*```|\s*\||\s*##|\s*" + tag_escaped + ")",
                    r"\1\2\n" + self.tag + "\n",
                    slides[i],
                )

            body_without_notes = slides[0]
            for i in range(1, len(slides)):
                if re.match(r"^\s*(layout:|transition:)", slides[i].lstrip()):
                    body_without_notes += "\n---\n" + slides[i]
                else:
                    body_without_notes += "\n---\n\n" + slides[i]

        duplicate_pattern = tag_escaped + r"\s*\n" + tag_escaped
        body_without_notes = re.sub(duplicate_pattern, self.tag, body_without_notes)

        for i, note in enumerate(presenter_notes):
            body_without_notes = body_without_notes.replace(f"{token_prefix}{i}__", note)

        return frontmatter + body_without_notes
