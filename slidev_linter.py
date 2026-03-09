#!/usr/bin/env python3
"""
Slidev Linter - A tool to maintain consistency in Slidev presentations.

Usage:
  python slidev_linter.py --all
  python slidev_linter.py --all --check
  python slidev_linter.py --chapter 20
  python slidev_linter.py --range 20-29
  python slidev_linter.py --list-rules
  python slidev_linter.py --list-rule-sets
  python slidev_linter.py --rule-set basic_formatting
  python slidev_linter.py --rules remove_bold_from_titles add_spacing_after_titles
"""

from __future__ import annotations

import argparse
import glob
import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

DEFAULT_TRANSITION = "slide-left"
SECTION_TRANSITION = "slide-left"
DEFAULT_RULE_SET = "advanced_formatting"

FRONTMATTER_RE = re.compile(r"^---\s*\n(?P<meta>.*?)\n---\s*\n?", re.DOTALL)


#######################################
# BASE RULES
#######################################


class Rule(ABC):
    """Abstract base class for defining a linting rule."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.enabled = True

    @abstractmethod
    def apply(self, content: str) -> str:
        """Apply the rule to the content and return the modified content."""

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


def split_frontmatter(content: str) -> Tuple[str, str]:
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


#######################################
# FORMATTING RULES
#######################################


class RemoveBoldFromTitlesRule(Rule):
    """Rule to remove bold formatting from titles."""

    def __init__(self):
        super().__init__(
            "remove_bold_from_titles",
            "Removes bold formatting from titles (# **Title** -> # Title)",
        )

    def apply(self, content: str) -> str:
        """Remove bold formatting from titles."""
        return re.sub(r"(#\s+)\*\*(.*?)\*\*", r"\1\2", content)


#######################################
# TRANSITION RULES
#######################################


class DefaultTransitionRule(Rule):
    """Rule to ensure the default transition in the header is 'slide-left'."""

    def __init__(self):
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
    """Rule to enforce 'transition: slide-left' on section slides."""

    def __init__(self):
        super().__init__(
            "section_transition",
            "Adds 'transition: slide-left' only for slides with layout 'section'",
        )

    def apply(self, content: str) -> str:
        """Add or fix transition for metadata blocks with layout: section."""
        lines = content.splitlines(keepends=True)
        output: List[str] = []
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
                    f"transition: {SECTION_TRANSITION}",
                    metadata,
                    count=1,
                    flags=re.MULTILINE,
                )
            else:
                suffix = "" if metadata.endswith("\n") else "\n"
                updated_metadata = f"{metadata}{suffix}transition: {SECTION_TRANSITION}\n"

            output.append(current_line)
            output.append(updated_metadata)
            output.append(lines[end])
            index = end + 1

        return "".join(output)


class CleanTransitionsRule(Rule):
    """Rule to clean up duplicate or misplaced transitions."""

    def __init__(self):
        super().__init__(
            "clean_transitions",
            "Cleans up duplicate or misplaced transitions",
        )

    def apply(self, content: str) -> str:
        """Clean up duplicate or misplaced transitions."""
        frontmatter, body = split_frontmatter(content)

        # Remove transitions inserted directly after separators on normal slides.
        body = re.sub(
            r"(?m)^---\s*\ntransition:\s*[\w-]+\s*\n(?!layout:)",
            "---\n\n",
            body,
        )

        # Keep one blank line after separators unless explicitly followed by metadata.
        body = re.sub(r"(?m)(\n---[ \t]*\n)(?!\n|layout:|transition:)", r"\1\n", body)

        # Normalize duplicated spacing tags inserted by spacing rule runs.
        body = re.sub(r"(<p class=\"py-2\"/>\s*\n){2,}", '<p class="py-2"/>\n', body)

        if frontmatter:
            return frontmatter + body.lstrip("\n")

        return re.sub(r"^---\s*\n\s*\n", "---\n", body)


class EnsureSpaceBetweenTitleAndSubtitleRule(Rule):
    """Rule to ensure there is a blank line between a title and its subtitle."""

    def __init__(self):
        super().__init__(
            "ensure_space_between_title_subtitle",
            "Ensures there is a blank line between a title (#) and its subtitle (##)",
        )

    def apply(self, content: str) -> str:
        """Ensure there is a blank line between a title and its subtitle."""
        return re.sub(r"(^#\s+.*$)\n(^##\s+.*$)", r"\1\n\n\2", content, flags=re.MULTILINE)


class AddSpacingAfterTitlesRule(Rule):
    """Rule to add a customizable HTML spacing tag after level 1 titles."""

    def __init__(self, tag: str = '<p class="py-2"/>'):
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
        presenter_notes: List[str] = []

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


#######################################
# RULE SETS
#######################################


class RuleSet:
    """A set of rules to apply."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.rules: List[Rule] = []

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the set."""
        self.rules.append(rule)

    def apply(self, content: str) -> str:
        """Apply all enabled rules to the content."""
        for rule in self.rules:
            if rule.enabled:
                content = rule.apply(content)
        return content

    def __str__(self) -> str:
        return f"{self.name}: {self.description}\nRules:\n" + "\n".join(f"  - {rule}" for rule in self.rules)


#######################################
# MAIN LINTER
#######################################


class SlidevLinter:
    """Linter for Slidev presentations."""

    def __init__(self):
        self.rule_sets: Dict[str, RuleSet] = {}
        self.rules: Dict[str, Rule] = {}
        self._initialize_rules()

    def _initialize_rules(self) -> None:
        """Initialize available rules and rule sets."""
        self.rules["remove_bold_from_titles"] = RemoveBoldFromTitlesRule()
        self.rules["default_transition"] = DefaultTransitionRule()
        self.rules["section_transition"] = SectionTransitionRule()
        self.rules["clean_transitions"] = CleanTransitionsRule()
        self.rules["add_spacing_after_titles"] = AddSpacingAfterTitlesRule(tag='<p class="py-2"/>')
        self.rules["ensure_space_between_title_subtitle"] = EnsureSpaceBetweenTitleAndSubtitleRule()

        basic_formatting = RuleSet(
            "basic_formatting",
            "Basic formatting rules for Slidev presentations",
        )
        basic_formatting.add_rule(self.rules["remove_bold_from_titles"])
        basic_formatting.add_rule(self.rules["default_transition"])
        basic_formatting.add_rule(self.rules["section_transition"])
        basic_formatting.add_rule(self.rules["clean_transitions"])
        basic_formatting.add_rule(self.rules["ensure_space_between_title_subtitle"])

        advanced_formatting = RuleSet(
            "advanced_formatting",
            "Advanced formatting rules for Slidev presentations",
        )
        advanced_formatting.add_rule(self.rules["remove_bold_from_titles"])
        advanced_formatting.add_rule(self.rules["default_transition"])
        advanced_formatting.add_rule(self.rules["section_transition"])
        advanced_formatting.add_rule(self.rules["clean_transitions"])
        advanced_formatting.add_rule(self.rules["add_spacing_after_titles"])
        advanced_formatting.add_rule(self.rules["ensure_space_between_title_subtitle"])

        self.rule_sets["basic_formatting"] = basic_formatting
        self.rule_sets["advanced_formatting"] = advanced_formatting

    def get_available_rules(self) -> List[str]:
        """Return the list of available rules."""
        return list(self.rules.keys())

    def get_available_rule_sets(self) -> List[str]:
        """Return the list of available rule sets."""
        return list(self.rule_sets.keys())

    def lint_file(
        self,
        file_path: str,
        rule_set_name: Optional[str] = None,
        rule_names: Optional[List[str]] = None,
        check_only: bool = False,
    ) -> bool:
        """Lint a file with the specified rules."""
        print(f"Processing file: {file_path}")

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        original_content = content

        if rule_set_name and rule_set_name in self.rule_sets:
            content = self.rule_sets[rule_set_name].apply(content)
        elif rule_names:
            for rule_name in rule_names:
                if rule_name in self.rules and self.rules[rule_name].enabled:
                    content = self.rules[rule_name].apply(content)

        if content != original_content:
            if check_only:
                print(f"❌ Would apply modifications to {file_path}")
                return True

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)
            print(f"✅ Applied modifications to {file_path}")
            return True

        print(f"ℹ️ No modifications needed for {file_path}")
        return False


#######################################
# COMMAND LINE INTERFACE
#######################################


def parse_range(range_value: str) -> Optional[Tuple[int, int]]:
    """Parse chapter range values like '20-29'."""
    range_match = re.match(r"^(\d+)-(\d+)$", range_value)
    if not range_match:
        return None

    start = int(range_match.group(1))
    end = int(range_match.group(2))
    if start > end:
        return None

    return start, end


def expand_file_arg(file_arg: str, slides_dir: str) -> List[str]:
    """Resolve --file argument as explicit file path or glob pattern."""
    if os.path.isabs(file_arg):
        candidates = [file_arg]
    else:
        candidates = [file_arg, os.path.join(slides_dir, file_arg)]

    for candidate in candidates:
        if os.path.isfile(candidate) and candidate.endswith(".md"):
            return [candidate]

    matched_files: List[str] = []
    for candidate in candidates:
        matched_files.extend(glob.glob(candidate))

    return sorted({path for path in matched_files if os.path.isfile(path) and path.endswith(".md")})


def collect_files_to_process(args: argparse.Namespace, slides_dir: str) -> Tuple[List[str], Optional[str]]:
    """Return selected markdown files plus optional user-facing error."""
    if args.file:
        files = expand_file_arg(args.file, slides_dir)
        if files:
            return files, None
        return [], f"Error: File not found or pattern unmatched: {args.file}"

    if args.pattern:
        files = sorted(
            {
                path
                for path in glob.glob(os.path.join(slides_dir, args.pattern))
                if os.path.isfile(path) and path.endswith(".md")
            }
        )
        if files:
            return files, None
        return [], f"Error: No files found matching pattern: {args.pattern}"

    if args.chapter is not None:
        chapter_pattern = f"{args.chapter:02d}-*.md"
        files = sorted(glob.glob(os.path.join(slides_dir, chapter_pattern)))
        if files:
            return files, None
        return [], f"Error: No files found for chapter: {args.chapter}"

    if args.range:
        parsed_range = parse_range(args.range)
        if not parsed_range:
            return [], f"Error: Invalid range format: {args.range}. Expected format like 20-29."

        start, end = parsed_range
        files: List[str] = []
        for chapter in range(start, end + 1):
            files.extend(glob.glob(os.path.join(slides_dir, f"{chapter:02d}-*.md")))

        files = sorted({path for path in files if os.path.isfile(path) and path.endswith(".md")})
        if files:
            return files, None
        return [], f"Error: No files found for range: {args.range}"

    if args.all:
        files = sorted(glob.glob(os.path.join(slides_dir, "[0-9][0-9]-*.md")))
        if files:
            return files, None
        return [], "No files found matching the criteria."

    return [], "Error: Please specify --file, --pattern, --chapter, --range, or --all"


def validate_rule_selection(args: argparse.Namespace, linter: SlidevLinter) -> Optional[str]:
    """Validate rule-related arguments and return an optional error message."""
    if args.rule_set and args.rules:
        return "Error: Use either --rule-set or --rules, not both."

    if args.rule_set and args.rule_set not in linter.rule_sets:
        return (
            f"Error: Unknown rule set '{args.rule_set}'. "
            f"Available rule sets: {', '.join(sorted(linter.get_available_rule_sets()))}"
        )

    if args.rules:
        invalid_rules = [rule for rule in args.rules if rule not in linter.rules]
        if invalid_rules:
            return (
                f"Error: Unknown rules: {', '.join(sorted(invalid_rules))}. "
                f"Available rules: {', '.join(sorted(linter.get_available_rules()))}"
            )

    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(description="Linter for Slidev presentations.")
    parser.add_argument("--file", type=str, help="Process a specific file")
    parser.add_argument("--pattern", type=str, help="Process files matching a glob pattern")
    parser.add_argument("--chapter", type=int, help="Process all slides for one chapter (e.g., 20)")
    parser.add_argument("--range", type=str, help="Process a chapter range (e.g., 20-29)")
    parser.add_argument("--all", action="store_true", help="Process all files")
    parser.add_argument("--slides-dir", type=str, help="Custom slides directory")
    parser.add_argument("--check", action="store_true", help="Check mode: detect issues without writing files")
    parser.add_argument("--rule-set", type=str, help="Rule set to apply")
    parser.add_argument("--rules", type=str, nargs="+", help="Individual rules to apply")
    parser.add_argument("--list-rules", action="store_true", help="List available rules")
    parser.add_argument("--list-rule-sets", action="store_true", help="List available rule sets")

    args = parser.parse_args(argv)

    linter = SlidevLinter()

    if args.list_rules:
        print("Available rules:")
        for rule_name, rule in linter.rules.items():
            print(f"  - {rule_name}: {rule.description}")
        return 0

    if args.list_rule_sets:
        print("Available rule sets:")
        for rule_set_name, rule_set in linter.rule_sets.items():
            print(f"  - {rule_set_name}: {rule_set.description}")
            print("    Included rules:")
            for rule in rule_set.rules:
                print(f"      - {rule.name}: {rule.description}")
        return 0

    rule_error = validate_rule_selection(args, linter)
    if rule_error:
        print(rule_error)
        return 2

    base_dir = os.path.dirname(os.path.abspath(__file__))
    slides_dir = args.slides_dir or os.path.join(base_dir, "slides")

    files_to_process, file_error = collect_files_to_process(args, slides_dir)
    if file_error:
        print(file_error)
        return 2

    selected_rule_set = args.rule_set
    selected_rules = args.rules

    if not selected_rule_set and not selected_rules:
        selected_rule_set = DEFAULT_RULE_SET
        print(f"ℹ️ No rule selection provided, defaulting to '{DEFAULT_RULE_SET}'.")

    modified_count = 0
    for file_path in files_to_process:
        if linter.lint_file(file_path, selected_rule_set, selected_rules, check_only=args.check):
            modified_count += 1

    if args.check:
        print(f"\nSummary: {modified_count}/{len(files_to_process)} files need changes.")
        if modified_count > 0:
            return 1
    else:
        print(f"\nSummary: {modified_count}/{len(files_to_process)} files modified.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
