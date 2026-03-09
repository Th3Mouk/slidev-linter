from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .constants import DEFAULT_RULE_SET
from .rules import (
    AddSpacingAfterTitlesRule,
    CleanTransitionsRule,
    DefaultTransitionRule,
    EnsureSpaceBetweenTitleAndSubtitleRule,
    RemoveBoldFromTitlesRule,
    Rule,
    SectionTransitionRule,
)


@dataclass(frozen=True)
class Selector:
    kind: str
    value: str


@dataclass(frozen=True)
class FileResult:
    file: str
    changed: bool
    action: str
    error: str | None = None


@dataclass
class RunResult:
    mode: str
    selector: str
    rules_applied: list[str]
    files_total: int
    files_changed: int
    files_unchanged: int
    errors: list[str]
    duration_ms: int
    per_file: list[FileResult]


class RuleSet:
    """A set of rules to apply."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.rules: list[Rule] = []

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def apply(self, content: str) -> str:
        for rule in self.rules:
            if rule.enabled:
                content = rule.apply(content)
        return content


class SlidevLinter:
    """Linter for Slidev presentations."""

    def __init__(self) -> None:
        self.rule_sets: dict[str, RuleSet] = {}
        self.rules: dict[str, Rule] = {}
        self._initialize_rules()

    def _initialize_rules(self) -> None:
        self.rules["remove_bold_from_titles"] = RemoveBoldFromTitlesRule()
        self.rules["default_transition"] = DefaultTransitionRule()
        self.rules["section_transition"] = SectionTransitionRule()
        self.rules["clean_transitions"] = CleanTransitionsRule()
        self.rules["add_spacing_after_titles"] = AddSpacingAfterTitlesRule()
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

    def get_available_rules(self) -> list[str]:
        return sorted(self.rules.keys())

    def get_available_rule_sets(self) -> list[str]:
        return sorted(self.rule_sets.keys())

    def resolve_rules(self, rule_set_name: str | None, rule_names: list[str] | None) -> list[Rule]:
        if rule_set_name:
            return list(self.rule_sets[rule_set_name].rules)
        if rule_names:
            return [self.rules[rule_name] for rule_name in rule_names]
        return list(self.rule_sets[DEFAULT_RULE_SET].rules)

    def lint_file(
        self, file_path: str, selected_rules: list[Rule], check_only: bool = False
    ) -> FileResult:
        path = Path(file_path)
        try:
            original_content = path.read_text(encoding="utf-8")
        except OSError as exc:
            return FileResult(
                file=file_path,
                changed=False,
                action="error",
                error=f"Cannot read file '{file_path}': {exc}",
            )

        content = original_content
        for rule in selected_rules:
            if rule.enabled:
                content = rule.apply(content)

        if content == original_content:
            return FileResult(file=file_path, changed=False, action="no_changes")

        if check_only:
            return FileResult(file=file_path, changed=True, action="would_modify")

        try:
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return FileResult(
                file=file_path,
                changed=False,
                action="error",
                error=f"Cannot write file '{file_path}': {exc}",
            )

        return FileResult(file=file_path, changed=True, action="modified")
