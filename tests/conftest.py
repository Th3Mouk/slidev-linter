from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import slidev_linter as sl


@pytest.fixture
def linter() -> sl.SlidevLinter:
    return sl.SlidevLinter()


@pytest.fixture
def slides_dir(tmp_path: Path) -> Path:
    path = tmp_path / "slides"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def write_slide(slides_dir: Path):
    def _write(name: str, body: str) -> Path:
        path = slides_dir / name
        path.write_text(body, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def read_slide(slides_dir: Path):
    def _read(name: str) -> str:
        return (slides_dir / name).read_text(encoding="utf-8")

    return _read
