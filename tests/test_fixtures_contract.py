from __future__ import annotations

import shutil
from pathlib import Path

import slidev_linter as sl

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_fixtures_match_expected_after_lint(tmp_path: Path) -> None:
    fixtures_dir = ROOT_DIR / "fixtures"
    expected_dir = fixtures_dir / "expected"
    source_files = sorted(fixtures_dir.glob("[0-9][0-9]-*.md"))
    expected_files = sorted(expected_dir.glob("[0-9][0-9]-*.md"))

    assert source_files, "No source fixtures found"
    assert [path.name for path in source_files] == [path.name for path in expected_files]

    slides_dir = tmp_path / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    for source in source_files:
        shutil.copy2(source, slides_dir / source.name)

    exit_code = sl.main(["--all", "--slides-dir", str(slides_dir)])
    assert exit_code == 0

    for expected in expected_files:
        actual_content = (slides_dir / expected.name).read_text(encoding="utf-8")
        expected_content = expected.read_text(encoding="utf-8")
        assert actual_content == expected_content, f"Mismatch for {expected.name}"
