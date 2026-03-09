from __future__ import annotations

import json
import os
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

import slidev_linter as sl


def run_main(args: list[str]) -> tuple[int, str]:
    output = StringIO()
    with redirect_stdout(output):
        code = sl.main(args)
    return code, output.getvalue()


def test_list_rules_prints_available_rules() -> None:
    code, output = run_main(["list", "rules"])
    assert code == 0
    assert "Available rules:" in output
    assert "remove_bold_from_titles" in output


def test_list_rule_sets_prints_available_rule_sets() -> None:
    code, output = run_main(["list", "rule-sets"])
    assert code == 0
    assert "Available rule sets:" in output
    assert "advanced_formatting" in output


def test_main_returns_error_without_command() -> None:
    code, output = run_main([])
    assert code == 2
    assert "usage:" in output


def test_main_rejects_unknown_rule_set(
    slides_dir: Path, write_slide: Callable[[str, str], Path]
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# Intro\n")
    code, output = run_main(["lint", "all", "--slides-dir", str(slides_dir), "--rule-set", "unknown"])
    assert code == 2
    assert "Unknown rule set 'unknown'" in output


@pytest.mark.parametrize(
    ("args", "error_fragment"),
    [
        (["check", "file", "missing.md"], "File selector did not match any markdown file"),
        (["check", "pattern", "missing-*.md"], "Pattern selector did not match any markdown file"),
        (["check", "chapter", "42"], "Chapter selector found no files for chapter: 42"),
        (["check", "range", "42-40"], "Invalid range '42-40'"),
        (["check", "range", "42-43"], "Range selector found no files for range: 42-43"),
    ],
)
def test_main_reports_selection_errors(
    slides_dir: Path, args: list[str], error_fragment: str
) -> None:
    code, output = run_main([*args, "--slides-dir", str(slides_dir)])
    assert code == 2
    assert error_fragment in output


def test_main_supports_file_selector_relative_absolute_and_glob(
    slides_dir: Path,
    write_slide: Callable[[str, str], Path],
    read_slide: Callable[[str], str],
) -> None:
    relative = write_slide("20-relative.md", "---\ntitle: Demo\n---\n# **Relative**\n")
    absolute = write_slide("21-absolute.md", "---\ntitle: Demo\n---\n# **Absolute**\n")
    write_slide("22-glob.md", "---\ntitle: Demo\n---\n# **Glob**\n")

    code_relative, _ = run_main(["lint", "file", "20-relative.md", "--slides-dir", str(slides_dir)])
    code_absolute, _ = run_main(["lint", "file", str(absolute), "--slides-dir", str(slides_dir)])
    code_glob, _ = run_main(["lint", "file", "22-*.md", "--slides-dir", str(slides_dir)])

    assert code_relative == 0
    assert code_absolute == 0
    assert code_glob == 0
    assert "# Relative" in read_slide(relative.name)
    assert "# Absolute" in read_slide(absolute.name)
    assert "# Glob" in read_slide("22-glob.md")


def test_main_rejects_combined_rule_set_and_rules(
    slides_dir: Path, write_slide: Callable[[str, str], Path]
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# Intro\n")
    code, output = run_main(
        [
            "lint",
            "all",
            "--slides-dir",
            str(slides_dir),
            "--rule-set",
            "basic_formatting",
            "--rules",
            "remove_bold_from_titles",
        ]
    )
    assert code == 2
    assert "Use either --rule-set or --rules, not both." in output


def test_main_rejects_invalid_rule_name(
    slides_dir: Path, write_slide: Callable[[str, str], Path]
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# Intro\n")
    code, output = run_main(["lint", "all", "--slides-dir", str(slides_dir), "--rules", "unknown_rule"])
    assert code == 2
    assert "Unknown rules: unknown_rule" in output


def test_lint_defaults_to_advanced_rule_set(
    slides_dir: Path,
    write_slide: Callable[[str, str], Path],
    read_slide: Callable[[str], str],
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# **Title**\n")
    code, _ = run_main(["lint", "all", "--slides-dir", str(slides_dir)])
    assert code == 0
    assert "# Title" in read_slide("20-demo.md")


def test_main_supports_chapter_and_range(
    slides_dir: Path,
    write_slide: Callable[[str, str], Path],
    read_slide: Callable[[str], str],
) -> None:
    write_slide("20-foo.md", "---\ntitle: Demo\n---\n# **Slide 20**\n")
    write_slide("21-bar.md", "---\ntitle: Demo\n---\n# **Slide 21**\n")

    chapter_code, _ = run_main(["lint", "chapter", "20", "--slides-dir", str(slides_dir)])
    range_code, _ = run_main(["lint", "range", "20-21", "--slides-dir", str(slides_dir)])

    assert chapter_code == 0
    assert range_code == 0
    assert "# Slide 20" in read_slide("20-foo.md")
    assert "# Slide 21" in read_slide("21-bar.md")


def test_main_supports_recursive_selectors(slides_dir: Path) -> None:
    php = slides_dir / "php"
    symfony = slides_dir / "symfony"
    php.mkdir(parents=True)
    symfony.mkdir(parents=True)
    (php / "01-intro.md").write_text("---\ntitle: Demo\n---\n# **PHP Intro**\n", encoding="utf-8")
    (symfony / "02-bootstrap.md").write_text(
        "---\ntitle: Demo\n---\n# **Symfony Bootstrap**\n",
        encoding="utf-8",
    )

    all_code, _ = run_main(["lint", "all", "--slides-dir", str(slides_dir)])
    chapter_code, _ = run_main(["lint", "chapter", "1", "--slides-dir", str(slides_dir)])
    range_code, _ = run_main(["lint", "range", "1-2", "--slides-dir", str(slides_dir)])
    pattern_code, _ = run_main(["check", "pattern", "**/*.md", "--slides-dir", str(slides_dir)])

    assert all_code == 0
    assert chapter_code == 0
    assert range_code == 0
    assert pattern_code in (0, 1)


def test_main_defaults_slides_dir_from_current_working_directory(tmp_path: Path) -> None:
    slides_dir = tmp_path / "slides"
    slides_dir.mkdir(parents=True)
    (slides_dir / "20-demo.md").write_text("---\ntitle: Demo\n---\n# **Title**\n", encoding="utf-8")

    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        code, _ = run_main(["lint", "all"])
    finally:
        os.chdir(original_cwd)

    assert code == 0
    assert "# Title" in (slides_dir / "20-demo.md").read_text(encoding="utf-8")


def test_check_mode_reports_issues_without_writing(
    slides_dir: Path,
    write_slide: Callable[[str, str], Path],
    read_slide: Callable[[str], str],
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# **Title**\n")
    code, output = run_main(["check", "all", "--slides-dir", str(slides_dir)])
    assert code == 1
    assert "Would apply modifications" in output
    assert "# **Title**" in read_slide("20-demo.md")


def test_check_mode_returns_zero_when_clean(
    slides_dir: Path, write_slide: Callable[[str, str], Path]
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\ntransition: slide-left\n---\n# Title\n")
    code, output = run_main(
        [
            "check",
            "all",
            "--slides-dir",
            str(slides_dir),
            "--rules",
            "remove_bold_from_titles",
        ]
    )
    assert code == 0
    assert "Summary: 0/1 files need changes." in output


def test_check_rejects_removed_dry_run_alias(
    slides_dir: Path, write_slide: Callable[[str, str], Path]
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# **Title**\n")
    out = StringIO()
    err = StringIO()
    with redirect_stdout(out), redirect_stderr(err), pytest.raises(SystemExit) as exc_info:
        sl.main(["check", "all", "--dry-run", "--slides-dir", str(slides_dir)])

    assert exc_info.value.code == 2
    assert "unrecognized arguments: --dry-run" in err.getvalue()


def test_advanced_formatting_is_idempotent_via_cli(
    slides_dir: Path,
    write_slide: Callable[[str, str], Path],
    read_slide: Callable[[str], str],
) -> None:
    write_slide(
        "20-demo.md",
        "---\ntitle: Demo\ntransition: fade\n---\n# **Title**\n## Subtitle\n\n---\nlayout: section\n---\n# Section\n",
    )
    first_code, _ = run_main(["lint", "all", "--slides-dir", str(slides_dir)])
    once = read_slide("20-demo.md")

    second_code, second_output = run_main(["lint", "all", "--slides-dir", str(slides_dir)])
    twice = read_slide("20-demo.md")

    assert first_code == 0
    assert second_code == 0
    assert twice == once
    assert "Summary: 0/1 files modified." in second_output


def test_json_output_contract_for_check(
    slides_dir: Path, write_slide: Callable[[str, str], Path]
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# **Title**\n")
    code, output = run_main(["check", "all", "--slides-dir", str(slides_dir), "--format", "json"])
    payload = json.loads(output)

    assert code == 1
    assert payload["mode"] == "check"
    assert payload["selector"] == "all:all"
    assert payload["files_total"] == 1
    assert payload["files_changed"] == 1
    assert payload["files_unchanged"] == 0
    assert payload["duration_ms"] >= 0
    assert payload["errors"] == []
    assert payload["rules_applied"]
    assert len(payload["per_file"]) == 1
    assert payload["per_file"][0]["action"] == "would_modify"


def test_json_output_contract_for_lint(
    slides_dir: Path, write_slide: Callable[[str, str], Path]
) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# **Title**\n")
    code, output = run_main(["lint", "all", "--slides-dir", str(slides_dir), "--format", "json"])
    payload = json.loads(output)

    assert code == 0
    assert payload["mode"] == "lint"
    assert payload["files_changed"] == 1
    assert payload["per_file"][0]["action"] == "modified"


def test_legacy_flags_are_rejected_with_migration_hint() -> None:
    code, output = run_main(["--all"])
    assert code == 2
    assert "Legacy flags are no longer supported" in output
    assert "Use subcommands" in output
