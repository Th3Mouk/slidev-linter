from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .constants import (
    AVAILABLE_TRANSITIONS,
    EXIT_CHECK_DIRTY,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    EXIT_USAGE_ERROR,
    OUTPUT_JSON,
    OUTPUT_TEXT,
    SECTION_TRANSITION,
)
from .engine import FileResult, RunResult, SlidevLinter
from .output import emit_error, emit_json_summary, emit_text_summary
from .selectors import collect_files_to_process, selector_from_args


def validate_rule_selection(args: argparse.Namespace, linter: SlidevLinter) -> str | None:
    if args.rule_set and args.rules:
        return "Use either --rule-set or --rules, not both."

    if args.rule_set and args.rule_set not in linter.rule_sets:
        return (
            f"Unknown rule set '{args.rule_set}'. "
            f"Available rule sets: {', '.join(linter.get_available_rule_sets())}"
        )

    if args.rules:
        invalid_rules = [rule for rule in args.rules if rule not in linter.rules]
        if invalid_rules:
            return (
                f"Unknown rules: {', '.join(sorted(invalid_rules))}. "
                f"Available rules: {', '.join(linter.get_available_rules())}"
            )

    return None


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Linter for Slidev presentations.",
        epilog=(
            "Migration note: legacy flags like --all/--check were removed. "
            "Use subcommands: lint, check, list."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    def add_selector_options(selector_parser: argparse.ArgumentParser) -> None:
        selector_parser.add_argument("--slides-dir", type=str, help="Custom slides directory")
        selector_parser.add_argument("--rule-set", type=str, help="Rule set to apply")
        selector_parser.add_argument(
            "--rules", type=str, nargs="+", help="Individual rules to apply"
        )
        selector_parser.add_argument(
            "--section-transition",
            type=str,
            choices=AVAILABLE_TRANSITIONS,
            default=SECTION_TRANSITION,
            help=f"Transition animation for section slides (default: {SECTION_TRANSITION})",
        )
        selector_parser.add_argument(
            "--format",
            choices=[OUTPUT_TEXT, OUTPUT_JSON],
            default=OUTPUT_TEXT,
            help="Output format for run summary",
        )

    def add_shared_run_options(run_parser: argparse.ArgumentParser) -> None:
        selectors = run_parser.add_subparsers(dest="selector_kind", required=True)

        all_selector = selectors.add_parser("all", help="Process all chapter files")
        add_selector_options(all_selector)
        all_selector.set_defaults(selector_value="all")

        file_selector = selectors.add_parser("file", help="Process one file or one glob pattern")
        file_selector.add_argument("selector_value", type=str, help="Markdown file path or glob")
        add_selector_options(file_selector)

        chapter_selector = selectors.add_parser("chapter", help="Process one chapter number")
        chapter_selector.add_argument("selector_value", type=str, help="Chapter number (e.g. 20)")
        add_selector_options(chapter_selector)

        range_selector = selectors.add_parser("range", help="Process a chapter range")
        range_selector.add_argument("selector_value", type=str, help="Range like 20-29")
        add_selector_options(range_selector)

        pattern_selector = selectors.add_parser(
            "pattern", help="Process files matching a recursive glob"
        )
        pattern_selector.add_argument("selector_value", type=str, help="Pattern like '**/*.md'")
        add_selector_options(pattern_selector)

    lint_parser = subparsers.add_parser("lint", help="Apply formatting changes")
    add_shared_run_options(lint_parser)

    check_parser = subparsers.add_parser("check", help="Check if formatting changes are needed")
    add_shared_run_options(check_parser)

    list_parser = subparsers.add_parser("list", help="List available lint metadata")
    list_parser.add_argument("target", choices=["rules", "rule-sets"], help="What to list")

    return parser


def run_lint_or_check(args: argparse.Namespace, mode: str, linter: SlidevLinter) -> int:
    output_format = args.format
    selector = selector_from_args(args)

    rule_error = validate_rule_selection(args, linter)
    if rule_error:
        emit_error(rule_error, output_format)
        return EXIT_USAGE_ERROR

    selected_rules = linter.resolve_rules(args.rule_set, args.rules)
    selected_rule_names = [rule.name for rule in selected_rules]

    slides_dir = args.slides_dir or str(Path.cwd() / "slides")
    files_to_process, file_error = collect_files_to_process(selector, slides_dir)
    if file_error:
        emit_error(file_error, output_format)
        if output_format == OUTPUT_TEXT and selector.kind == "range":
            print("Hint: use `slidev-linter check range 20-29`.")
        return EXIT_USAGE_ERROR

    check_only = mode == "check"

    start = time.perf_counter()
    per_file: list[FileResult] = []
    errors: list[str] = []
    changed_count = 0

    for file_path in files_to_process:
        outcome = linter.lint_file(file_path, selected_rules, check_only=check_only)
        per_file.append(outcome)
        if outcome.action == "error" and outcome.error:
            errors.append(outcome.error)
        if outcome.changed:
            changed_count += 1

    duration_ms = int((time.perf_counter() - start) * 1000)
    result = RunResult(
        mode=mode,
        selector=f"{selector.kind}:{selector.value}",
        rules_applied=selected_rule_names,
        files_total=len(files_to_process),
        files_changed=changed_count,
        files_unchanged=len(files_to_process) - changed_count,
        errors=errors,
        duration_ms=duration_ms,
        per_file=per_file,
    )

    if output_format == OUTPUT_JSON:
        emit_json_summary(result)
    else:
        emit_text_summary(result)

    if errors:
        return EXIT_RUNTIME_ERROR
    if mode == "check" and changed_count > 0:
        return EXIT_CHECK_DIRTY
    return EXIT_OK


def handle_list(args: argparse.Namespace, linter: SlidevLinter) -> int:
    if args.target == "rules":
        print("Available rules:")
        for rule_name in linter.get_available_rules():
            print(f"  - {rule_name}: {linter.rules[rule_name].description}")
        return EXIT_OK

    print("Available rule sets:")
    for rule_set_name in linter.get_available_rule_sets():
        rule_set = linter.rule_sets[rule_set_name]
        print(f"  - {rule_set_name}: {rule_set.description}")
        print("    Included rules:")
        for rule in rule_set.rules:
            print(f"      - {rule.name}: {rule.description}")

    return EXIT_OK


def detect_legacy_flags(argv: list[str]) -> str | None:
    legacy = {
        "--all",
        "--file",
        "--pattern",
        "--chapter",
        "--range",
        "--check",
        "--list-rules",
        "--list-rule-sets",
    }
    used = [arg for arg in argv if arg in legacy]
    if not used:
        return None

    unique_used = ", ".join(sorted(set(used)))
    return (
        f"Legacy flags are no longer supported ({unique_used}). "
        "Use subcommands: `slidev-linter lint ...`, `slidev-linter check ...`, "
        "`slidev-linter list ...`."
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    legacy_error = detect_legacy_flags(argv)
    if legacy_error:
        print(f"Error: {legacy_error}")
        return EXIT_USAGE_ERROR

    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return EXIT_USAGE_ERROR

    section_transition = getattr(args, "section_transition", SECTION_TRANSITION)
    linter = SlidevLinter(section_transition=section_transition)

    if args.command == "list":
        return handle_list(args, linter)
    if args.command == "lint":
        return run_lint_or_check(args, mode="lint", linter=linter)
    if args.command == "check":
        return run_lint_or_check(args, mode="check", linter=linter)

    print(f"Error: Unknown command '{args.command}'.")
    return EXIT_USAGE_ERROR
