from __future__ import annotations

import argparse
from pathlib import Path

import pytest

import slidev_linter as sl


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("20-29", (20, 29)),
        ("29-20", None),
        ("invalid", None),
        ("20", None),
    ],
)
def test_parse_range(raw: str, expected: tuple[int, int] | None) -> None:
    assert sl.parse_range(raw) == expected


def test_expand_file_arg_with_relative_name(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "# Demo\n")
    result = sl.expand_file_arg("20-demo.md", str(slides_dir))
    assert result == [str(slides_dir / "20-demo.md")]


def test_expand_file_arg_with_absolute_name(slides_dir: Path, write_slide) -> None:
    path = write_slide("20-demo.md", "# Demo\n")
    result = sl.expand_file_arg(str(path), str(slides_dir))
    assert result == [str(path)]


def test_expand_file_arg_with_glob_pattern(slides_dir: Path, write_slide) -> None:
    write_slide("20-foo.md", "# Foo\n")
    write_slide("20-bar.md", "# Bar\n")
    write_slide("20-not-md.txt", "ignore\n")
    result = sl.expand_file_arg("20-*.md", str(slides_dir))
    assert result == [str(slides_dir / "20-bar.md"), str(slides_dir / "20-foo.md")]


def test_expand_file_arg_unmatched_returns_empty(slides_dir: Path) -> None:
    assert sl.expand_file_arg("does-not-exist.md", str(slides_dir)) == []


def _build_args(**overrides: object) -> argparse.Namespace:
    defaults = {
        "file": None,
        "pattern": None,
        "chapter": None,
        "range": None,
        "all": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_collect_files_to_process_for_file_selector(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "# Demo\n")
    files, error = sl.collect_files_to_process(_build_args(file="20-demo.md"), str(slides_dir))
    assert error is None
    assert files == [str(slides_dir / "20-demo.md")]


def test_collect_files_to_process_for_pattern_selector(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "# Demo\n")
    files, error = sl.collect_files_to_process(_build_args(pattern="20-*.md"), str(slides_dir))
    assert error is None
    assert files == [str(slides_dir / "20-demo.md")]


def test_collect_files_to_process_pattern_recursive_glob(slides_dir: Path) -> None:
    nested = slides_dir / "a" / "b"
    nested.mkdir(parents=True)
    (slides_dir / "a" / "01-root.md").write_text("# Root\n", encoding="utf-8")
    (nested / "02-deep.md").write_text("# Deep\n", encoding="utf-8")

    files, error = sl.collect_files_to_process(_build_args(pattern="**/*.md"), str(slides_dir))

    assert error is None
    assert files == [str(slides_dir / "a" / "01-root.md"), str(nested / "02-deep.md")]


def test_collect_files_to_process_for_chapter_selector(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "# Demo\n")
    files, error = sl.collect_files_to_process(_build_args(chapter=20), str(slides_dir))
    assert error is None
    assert files == [str(slides_dir / "20-demo.md")]


def test_collect_files_to_process_for_chapter_selector_recurses(slides_dir: Path) -> None:
    nested = slides_dir / "php"
    nested.mkdir(parents=True)
    (nested / "01-intro.md").write_text("# Intro\n", encoding="utf-8")

    files, error = sl.collect_files_to_process(_build_args(chapter=1), str(slides_dir))

    assert error is None
    assert files == [str(nested / "01-intro.md")]


def test_collect_files_to_process_for_range_selector(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "# Demo\n")
    write_slide("21-demo.md", "# Demo\n")
    files, error = sl.collect_files_to_process(_build_args(range="20-21"), str(slides_dir))
    assert error is None
    assert files == [str(slides_dir / "20-demo.md"), str(slides_dir / "21-demo.md")]


def test_collect_files_to_process_for_range_selector_recurses(slides_dir: Path) -> None:
    php = slides_dir / "php"
    symfony = slides_dir / "symfony"
    php.mkdir(parents=True)
    symfony.mkdir(parents=True)
    (php / "01-intro.md").write_text("# Intro\n", encoding="utf-8")
    (symfony / "02-bootstrapping.md").write_text("# Boot\n", encoding="utf-8")

    files, error = sl.collect_files_to_process(_build_args(range="1-2"), str(slides_dir))

    assert error is None
    assert files == [str(php / "01-intro.md"), str(symfony / "02-bootstrapping.md")]


def test_collect_files_to_process_for_all_selector_recurses(slides_dir: Path) -> None:
    php = slides_dir / "php"
    symfony = slides_dir / "symfony"
    php.mkdir(parents=True)
    symfony.mkdir(parents=True)
    (php / "01-intro.md").write_text("# Intro\n", encoding="utf-8")
    (symfony / "02-bootstrapping.md").write_text("# Boot\n", encoding="utf-8")

    files, error = sl.collect_files_to_process(_build_args(all=True), str(slides_dir))

    assert error is None
    assert files == [str(php / "01-intro.md"), str(symfony / "02-bootstrapping.md")]


@pytest.mark.parametrize(
    ("args", "error_fragment"),
    [
        (_build_args(file="missing.md"), "File not found or pattern unmatched"),
        (_build_args(pattern="missing-*.md"), "No files found matching pattern"),
        (_build_args(chapter=42), "No files found for chapter"),
        (_build_args(range="42-40"), "Invalid range format"),
        (_build_args(range="42-43"), "No files found for range"),
        (_build_args(), "Please specify --file, --pattern, --chapter, --range, or --all"),
        (_build_args(all=True), "No files found matching the criteria"),
    ],
)
def test_collect_files_to_process_errors(
    slides_dir: Path, args: argparse.Namespace, error_fragment: str
) -> None:
    files, error = sl.collect_files_to_process(args, str(slides_dir))
    assert files == []
    assert error is not None
    assert error_fragment in error


def test_validate_rule_selection_success(linter: sl.SlidevLinter) -> None:
    args = argparse.Namespace(rule_set="basic_formatting", rules=None)
    assert sl.validate_rule_selection(args, linter) is None


@pytest.mark.parametrize(
    ("args", "error_fragment"),
    [
        (argparse.Namespace(rule_set="basic_formatting", rules=["remove_bold_from_titles"]), "Use either"),
        (argparse.Namespace(rule_set="unknown_set", rules=None), "Unknown rule set"),
        (argparse.Namespace(rule_set=None, rules=["unknown_rule"]), "Unknown rules"),
    ],
)
def test_validate_rule_selection_errors(
    linter: sl.SlidevLinter, args: argparse.Namespace, error_fragment: str
) -> None:
    error = sl.validate_rule_selection(args, linter)
    assert error is not None
    assert error_fragment in error
