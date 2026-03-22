from __future__ import annotations

from .cli import (
    build_cli_parser,
    detect_legacy_flags,
    handle_list,
    main,
    run_lint_or_check,
    validate_rule_selection,
)
from .constants import (
    DEFAULT_RULE_SET,
    DEFAULT_TRANSITION,
    EXIT_CHECK_DIRTY,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    EXIT_USAGE_ERROR,
    OUTPUT_JSON,
    OUTPUT_TEXT,
    SECTION_TRANSITION,
)
from .engine import FileResult, RuleExecutionError, RuleSet, RunResult, Selector, SlidevLinter
from .frontmatter import is_metadata_line, rebuild_frontmatter, split_frontmatter
from .rules import (
    AddSpacingAfterTitlesRule,
    CleanTransitionsRule,
    DefaultTransitionRule,
    EnsureSpaceBetweenTitleAndSubtitleRule,
    RemoveBoldFromTitlesRule,
    Rule,
    SectionTransitionRule,
)
from .selectors import collect_files_to_process, expand_file_arg, parse_range, selector_from_args

__all__ = [
    "AddSpacingAfterTitlesRule",
    "CleanTransitionsRule",
    "DEFAULT_RULE_SET",
    "DEFAULT_TRANSITION",
    "DefaultTransitionRule",
    "EXIT_CHECK_DIRTY",
    "EXIT_OK",
    "EXIT_RUNTIME_ERROR",
    "EXIT_USAGE_ERROR",
    "EnsureSpaceBetweenTitleAndSubtitleRule",
    "FileResult",
    "OUTPUT_JSON",
    "OUTPUT_TEXT",
    "RemoveBoldFromTitlesRule",
    "Rule",
    "RuleExecutionError",
    "RuleSet",
    "RunResult",
    "SECTION_TRANSITION",
    "SectionTransitionRule",
    "Selector",
    "SlidevLinter",
    "build_cli_parser",
    "collect_files_to_process",
    "detect_legacy_flags",
    "expand_file_arg",
    "handle_list",
    "is_metadata_line",
    "main",
    "parse_range",
    "rebuild_frontmatter",
    "run_lint_or_check",
    "selector_from_args",
    "split_frontmatter",
    "validate_rule_selection",
]
