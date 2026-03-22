# AGENTS.md - Slidev Linter

> Guide for AI coding agents working on the `slidev-linter` project.
> Reference: [https://agents.md/](https://agents.md/)
> Technical details: See [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md)

---

## Setup Commands

### Install Dependencies

```bash
uv sync --dev
```

### Run Tests

```bash
uv run pytest
uv run pytest --cov=slidev_linter --cov-report=term-missing
```

### Linting & Type Checking

```bash
uv run ruff check .
uv run mypy src tests
```

### Run the CLI

```bash
uv run slidev-linter list rules
uv run slidev-linter check all --slides-dir ./fixtures
```

---

## Code Style

- **Language**: Python 3.11+
- **Type hints**: Strict mode for source (`src/`), relaxed for tests
- **Line length**: 100 characters (Ruff configured)
- **Imports**: Use `from __future__ import annotations`
- **String formatting**: Prefer f-strings
- **Regex**: Use raw strings `r"..."`

### File Organization

- Source: `src/slidev_linter/`
- Tests: `tests/`
- Fixtures: `fixtures/` (source) and `fixtures/expected/` (expected output)

---

## Architecture Overview

This project uses a **Rule Engine Pattern** where:

1. **Rules** (`rules.py`) transform content via `apply(content: str) -> str`
2. **Engine** (`engine.py`) orchestrates rule application
3. **Selectors** (`selectors.py`) determine which files to process
4. **CLI** (`cli.py`) handles argument parsing and command dispatch

### Adding a New Rule

1. Inherit from `Rule` class in `rules.py`
2. Implement `apply(self, content: str) -> str`
3. Register in `engine.py:_initialize_rules()`

See [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) for detailed patterns.

---

## Testing Instructions

### Test Structure

| File | Purpose |
|------|---------|
| `tests/test_cli.py` | CLI parsing, exit codes, legacy flag detection |
| `tests/test_file_selection.py` | Selectors, file discovery |
| `tests/conftest.py` | Shared fixtures |

### Fixture Contract

- Source: `fixtures/[0-9][0-9]-*.md`
- Expected: `fixtures/expected/[0-9][0-9]-*.md`

Tests verify rule application produces expected outputs.

### Required Checks Before Commit

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest
```

---

## Common Tasks

### Add a New Rule

```python
# In src/slidev_linter/rules.py
class MyRule(Rule):
    def __init__(self) -> None:
        super().__init__("my_rule", "Description")

    def apply(self, content: str) -> str:
        return re.sub(r"pattern", r"replacement", content)
```

Then register in `engine.py`.

### Update Exit Codes

Modify `src/slidev_linter/constants.py` and update all switch statements in `cli.py`.

### Add a New Selector

1. Add subparser in `cli.py:build_cli_parser()`
2. Add handler in `selectors.py:collect_files_to_process()`

---

## CI Configuration

GitHub Actions workflow at `.github/workflows/ci.yml`:
- Runs on Python 3.11
- Executes ruff, mypy, pytest with coverage
- Coverage uploaded to Codecov

---

## Dependencies

### Runtime
- None (stdlib only)

### Development
- `mypy>=1.11.0` - Type checking
- `pytest>=8.3.0` - Testing framework
- `pytest-cov>=5.0.0` - Coverage reporting
- `ruff>=0.6.0` - Linting and formatting

See `pyproject.toml` for exact versions.
