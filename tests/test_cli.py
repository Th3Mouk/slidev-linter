from __future__ import annotations

from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout

import pytest

import slidev_linter as sl


def run_main(args: list[str]) -> tuple[int, str]:
    output = StringIO()
    with redirect_stdout(output):
        code = sl.main(args)
    return code, output.getvalue()


def test_list_rules_prints_available_rules() -> None:
    code, output = run_main(["--list-rules"])
    assert code == 0
    assert "Available rules:" in output
    assert "remove_bold_from_titles" in output


def test_list_rule_sets_prints_available_rule_sets() -> None:
    code, output = run_main(["--list-rule-sets"])
    assert code == 0
    assert "Available rule sets:" in output
    assert "advanced_formatting" in output


def test_main_returns_error_without_selector_flags() -> None:
    code, output = run_main([])
    assert code == 2
    assert "Please specify --file, --pattern, --chapter, --range, or --all" in output


def test_main_rejects_unknown_rule_set(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# Intro\n")
    code, output = run_main(["--all", "--slides-dir", str(slides_dir), "--rule-set", "unknown"])
    assert code == 2
    assert "Unknown rule set 'unknown'" in output


@pytest.mark.parametrize(
    ("args", "error_fragment"),
    [
        (["--file", "missing.md"], "File not found or pattern unmatched"),
        (["--pattern", "missing-*.md"], "No files found matching pattern"),
        (["--chapter", "42"], "No files found for chapter: 42"),
        (["--range", "42-40"], "Invalid range format"),
        (["--range", "42-43"], "No files found for range: 42-43"),
    ],
)
def test_main_reports_selection_errors(
    slides_dir: Path, args: list[str], error_fragment: str
) -> None:
    code, output = run_main([*args, "--slides-dir", str(slides_dir)])
    assert code == 2
    assert error_fragment in output


def test_main_supports_file_selector_relative_absolute_and_glob(
    slides_dir: Path, write_slide, read_slide
) -> None:
    relative = write_slide("20-relative.md", "---\ntitle: Demo\n---\n# **Relative**\n")
    absolute = write_slide("21-absolute.md", "---\ntitle: Demo\n---\n# **Absolute**\n")
    write_slide("22-glob.md", "---\ntitle: Demo\n---\n# **Glob**\n")

    code_relative, _ = run_main(["--file", "20-relative.md", "--slides-dir", str(slides_dir)])
    code_absolute, _ = run_main(["--file", str(absolute), "--slides-dir", str(slides_dir)])
    code_glob, _ = run_main(["--file", "22-*.md", "--slides-dir", str(slides_dir)])

    assert code_relative == 0
    assert code_absolute == 0
    assert code_glob == 0
    assert "# Relative" in read_slide(relative.name)
    assert "# Absolute" in read_slide(absolute.name)
    assert "# Glob" in read_slide("22-glob.md")


def test_main_rejects_combined_rule_set_and_rules(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# Intro\n")
    code, output = run_main(
        [
            "--all",
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


def test_main_rejects_invalid_rule_name(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# Intro\n")
    code, output = run_main(["--all", "--slides-dir", str(slides_dir), "--rules", "unknown_rule"])
    assert code == 2
    assert "Unknown rules: unknown_rule" in output


def test_main_defaults_to_advanced_rule_set(slides_dir: Path, write_slide, read_slide) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# **Title**\n")
    code, output = run_main(["--all", "--slides-dir", str(slides_dir)])
    assert code == 0
    assert "defaulting to 'advanced_formatting'" in output
    assert "# Title" in read_slide("20-demo.md")


def test_main_supports_chapter_and_range(slides_dir: Path, write_slide, read_slide) -> None:
    write_slide("20-foo.md", "---\ntitle: Demo\n---\n# **Slide 20**\n")
    write_slide("21-bar.md", "---\ntitle: Demo\n---\n# **Slide 21**\n")

    chapter_code, _ = run_main(["--chapter", "20", "--slides-dir", str(slides_dir)])
    range_code, _ = run_main(["--range", "20-21", "--slides-dir", str(slides_dir)])

    assert chapter_code == 0
    assert range_code == 0
    assert "# Slide 20" in read_slide("20-foo.md")
    assert "# Slide 21" in read_slide("21-bar.md")


def test_main_check_mode_reports_issues_without_writing(slides_dir: Path, write_slide, read_slide) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\n---\n# **Title**\n")
    code, output = run_main(["--all", "--check", "--slides-dir", str(slides_dir)])
    assert code == 1
    assert "Would apply modifications" in output
    assert "# **Title**" in read_slide("20-demo.md")


def test_main_check_mode_returns_zero_when_clean(slides_dir: Path, write_slide) -> None:
    write_slide("20-demo.md", "---\ntitle: Demo\ntransition: slide-left\n---\n# Title\n")
    code, output = run_main(
        [
            "--all",
            "--check",
            "--slides-dir",
            str(slides_dir),
            "--rules",
            "remove_bold_from_titles",
        ]
    )
    assert code == 0
    assert "Summary: 0/1 files need changes." in output


def test_advanced_formatting_is_idempotent_via_cli(slides_dir: Path, write_slide, read_slide) -> None:
    write_slide(
        "20-demo.md",
        "---\ntitle: Demo\ntransition: fade\n---\n# **Title**\n## Subtitle\n\n---\nlayout: section\n---\n# Section\n",
    )
    first_code, _ = run_main(["--all", "--slides-dir", str(slides_dir)])
    once = read_slide("20-demo.md")

    second_code, second_output = run_main(["--all", "--slides-dir", str(slides_dir)])
    twice = read_slide("20-demo.md")

    assert first_code == 0
    assert second_code == 0
    assert twice == once
    assert "Summary: 0/1 files modified." in second_output
