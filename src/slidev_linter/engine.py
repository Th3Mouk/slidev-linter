from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .constants import DEFAULT_RULE_SET, SECTION_TRANSITION
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
class RuleExecutionError:
    file: str
    rule: str
    message: str


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
    failed_rule: str | None = None
    changed_rules: list[str] | None = None


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
    rule_impact: dict[str, int] | None = None


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

    _RULE_FACTORIES: dict[str, Callable[[str], Rule]] = {
        "remove_bold_from_titles": lambda _transition: RemoveBoldFromTitlesRule(),
        "default_transition": lambda _transition: DefaultTransitionRule(),
        "section_transition": lambda transition: SectionTransitionRule(transition),
        "clean_transitions": lambda _transition: CleanTransitionsRule(),
        "add_spacing_after_titles": lambda _transition: AddSpacingAfterTitlesRule(),
        "ensure_space_between_title_subtitle": (
            lambda _transition: EnsureSpaceBetweenTitleAndSubtitleRule()
        ),
    }

    _RULE_SET_SPECS: dict[str, tuple[str, list[str]]] = {
        "basic_formatting": (
            "Basic formatting rules for Slidev presentations",
            [
                "remove_bold_from_titles",
                "default_transition",
                "section_transition",
                "clean_transitions",
                "ensure_space_between_title_subtitle",
            ],
        ),
        "advanced_formatting": (
            "Advanced formatting rules for Slidev presentations",
            [
                "remove_bold_from_titles",
                "default_transition",
                "section_transition",
                "clean_transitions",
                "add_spacing_after_titles",
                "ensure_space_between_title_subtitle",
            ],
        ),
    }

    def __init__(self, section_transition: str = SECTION_TRANSITION) -> None:
        self.rule_sets: dict[str, RuleSet] = {}
        self.rules: dict[str, Rule] = {}
        self._section_transition = section_transition
        self._initialize_rules()

    def _initialize_rules(self) -> None:
        self.rules = {
            rule_name: factory(self._section_transition)
            for rule_name, factory in self._RULE_FACTORIES.items()
        }

        for rule_set_name, (description, rule_names) in self._RULE_SET_SPECS.items():
            rule_set = RuleSet(rule_set_name, description)
            for rule_name in rule_names:
                rule_set.add_rule(self.rules[rule_name])
            self.rule_sets[rule_set_name] = rule_set

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
        self,
        file_path: str,
        selected_rules: list[Rule],
        check_only: bool = False,
        explain: bool = False,
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
        changed_rules: list[str] = []
        for rule in selected_rules:
            if rule.enabled:
                before = content
                try:
                    content = rule.apply(content)
                except Exception as exc:
                    rule_error = RuleExecutionError(
                        file=file_path,
                        rule=rule.name,
                        message=str(exc),
                    )
                    return FileResult(
                        file=file_path,
                        changed=False,
                        action="error",
                        error=(
                            f"Rule '{rule_error.rule}' failed for '{rule_error.file}': "
                            f"{rule_error.message}"
                        ),
                        failed_rule=rule_error.rule,
                        changed_rules=changed_rules if explain else None,
                    )

                if explain and content != before:
                    changed_rules.append(rule.name)

        if content == original_content:
            return FileResult(
                file=file_path,
                changed=False,
                action="no_changes",
                changed_rules=changed_rules if explain else None,
            )

        if check_only:
            return FileResult(
                file=file_path,
                changed=True,
                action="would_modify",
                changed_rules=changed_rules if explain else None,
            )

        try:
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return FileResult(
                file=file_path,
                changed=False,
                action="error",
                error=f"Cannot write file '{file_path}': {exc}",
                changed_rules=changed_rules if explain else None,
            )

        return FileResult(
            file=file_path,
            changed=True,
            action="modified",
            changed_rules=changed_rules if explain else None,
        )
