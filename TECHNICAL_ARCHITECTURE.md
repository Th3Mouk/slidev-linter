# Technical Architecture - Slidev Linter

> Architecture patterns and design decisions for the `slidev-linter` project.
> This document serves as a reference for AI agents working on the codebase.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Module Structure](#module-structure)
4. [Design Patterns](#design-patterns)
5. [Extension Points](#extension-points)
6. [Testing Strategy](#testing-strategy)

---

## Overview

`slidev-linter` is a Python CLI tool that enforces consistent formatting across Slidev markdown presentation files. The architecture follows a **pipeline pattern** where content flows through a series of transformation rules.

### Core Workflow

```
CLI Input → Selector Resolution → Rule Application → File Output
                ↓                       ↓
            File Discovery          Sequential Rules
```

---

## Architecture Patterns

### 1. Rule Engine Pattern

The core linting logic is implemented using the **Strategy Pattern** via an abstract `Rule` base class.

**Location**: `src/slidev_linter/rules.py`

```python
class Rule(ABC):
    @abstractmethod
    def apply(self, content: str) -> str:
        """Apply the rule to the content and return the modified content."""
```

**Key Characteristics**:
- Each rule is self-contained and idempotent
- Rules are applied sequentially in order
- Rules can be enabled/disabled individually
- New rules inherit from `Rule` and implement `apply()`

### 2. RuleSet Composition Pattern

Rules are grouped into predefined sets for common use cases.

**Location**: `src/slidev_linter/engine.py:79-101`

```python
basic_formatting = RuleSet("basic_formatting", "Basic formatting rules...")
basic_formatting.add_rule(self.rules["remove_bold_from_titles"])
# ... more rules

advanced_formatting = RuleSet("advanced_formatting", "Advanced formatting...")
# Includes all basic rules plus additional ones
```

**Available RuleSets**:
| Name | Rules | Purpose |
|------|-------|---------|
| `basic_formatting` | 5 rules | Essential formatting only |
| `advanced_formatting` | 6 rules | Full formatting (default) |

### 3. Selector Strategy Pattern

File targeting uses a strategy pattern for different selection methods.

**Location**: `src/slidev_linter/selectors.py`

| Selector | Format | Example | Use Case |
|----------|--------|---------|----------|
| `all` | - | `lint all` | Process all chapter files |
| `file` | path/glob | `lint file 20-intro.md` | Single file or pattern |
| `chapter` | number | `lint chapter 20` | Specific chapter |
| `range` | start-end | `lint range 20-29` | Chapter range |
| `pattern` | glob | `lint pattern "2[0-9]-*.md"` | Custom glob |

### 4. Result Data Transfer Object (DTO) Pattern

All operations return structured, serializable result objects.

**Location**: `src/slidev_linter/engine.py:18-43`

```python
@dataclass(frozen=True)
class FileResult:
    file: str
    changed: bool
    action: str  # "modified" | "would_modify" | "no_changes" | "error"
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
```

---

## Module Structure

### Dependency Graph

```
cli.py
├── engine.py
│   ├── rules.py
│   └── constants.py
├── selectors.py
├── output.py
└── constants.py
```

### Module Responsibilities

| Module | Purpose | Key Classes/Functions |
|--------|---------|---------------------|
| `cli.py` | Argument parsing, command dispatch | `build_cli_parser()`, `main()` |
| `engine.py` | Core linting orchestration | `SlidevLinter`, `RuleSet`, `RunResult` |
| `rules.py` | Rule implementations | `Rule` (ABC), 6 concrete rules |
| `selectors.py` | File selection logic | `collect_files_to_process()`, `Selector` |
| `output.py` | Output formatting | `emit_text_summary()`, `emit_json_summary()` |
| `constants.py` | Configuration constants | Exit codes, regex patterns |

---

## Design Patterns

### 1. Abstract Base Class (ABC) for Rules

All rules must inherit from `Rule` and implement `apply()`.

**Pattern**: `src/slidev_linter/rules.py:13-27`

```python
class Rule(ABC):
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.enabled = True

    @abstractmethod
    def apply(self, content: str) -> str:
        ...
```

### 2. Frontmatter Parsing Utility

Many rules need to split content into frontmatter and body.

**Pattern**: `src/slidev_linter/rules.py:29-43`

```python
def split_frontmatter(content: str) -> tuple[str, str]:
    """Split a document into top-frontmatter and body."""
    match = FRONTmatter_RE.match(content)
    if not match:
        return "", content
    return match.group(0), content[match.end():]
```

### 3. Token Preservation Pattern

Rules that modify content with special tokens (like presenter notes) use a save/restore pattern.

**Example**: `src/slidev_linter/rules.py:226-258`

```python
def save_presenter_note(match: re.Match[str]) -> str:
    presenter_notes.append(match.group(0))
    return f"{token_prefix}{len(presenter_notes) - 1}__"

# 1. Save tokens
body_without_notes = re.sub(r"<!--[\s\S]*?-->", save_presenter_note, body)

# 2. Process content
# ... transformations ...

# 3. Restore tokens
for i, note in enumerate(presenter_notes):
    body_without_notes = body_without_notes.replace(f"{token_prefix}{i}__", note)
```

### 4. Idempotency Guarantee

Rules must be idempotent - running twice produces the same result.

**Implementation**: `src/slidev_linter/engine.py:135-136`

```python
if content == original_content:
    return FileResult(file=file_path, changed=False, action="no_changes")
```

### 5. Exit Code Contract

Stable exit codes for CI scripting.

**Location**: `src/slidev_linter/constants.py:9-12`

| Code | Constant | Meaning |
|------|----------|---------|
| 0 | `EXIT_OK` | Success / clean check |
| 1 | `EXIT_CHECK_DIRTY` | Check found files needing changes |
| 2 | `EXIT_USAGE_ERROR` | Usage/validation error |
| 3 | `EXIT_RUNTIME_ERROR` | Runtime file I/O error |

---

## Extension Points

### Adding a New Rule

1. Create a class inheriting from `Rule` in `rules.py`:

```python
class MyNewRule(Rule):
    def __init__(self) -> None:
        super().__init__(
            "my_new_rule",
            "Description of what this rule does",
        )

    def apply(self, content: str) -> str:
        # Implement transformation
        return modified_content
```

2. Register in `engine.py`:

```python
self.rules["my_new_rule"] = MyNewRule()
# Add to relevant RuleSets
```

### Adding a New RuleSet

In `engine.py:_initialize_rules()`:

```python
custom_set = RuleSet("custom_set", "Custom rule combination")
custom_set.add_rule(self.rules["rule1"])
custom_set.add_rule(self.rules["rule2"])
self.rule_sets["custom_set"] = custom_set
```

### Adding a New Selector

1. Add parser in `cli.py:build_cli_parser()`
2. Add handling in `selectors.py:collect_files_to_process()`

---

## Testing Strategy

### Test Structure

| Test File | Coverage |
|-----------|----------|
| `test_cli.py` | CLI argument parsing, exit codes |
| `test_file_selection.py` | Selector logic, file discovery |
| `conftest.py` | Shared fixtures |

### Fixture Contract

- **Source fixtures**: `fixtures/[0-9][0-9]-*.md`
- **Expected outputs**: `fixtures/expected/[0-9][0-9]-*.md`

Tests verify that applying rules to source fixtures produces expected outputs.

### Running Tests

```bash
./.venv/bin/python -m pytest
./.venv/bin/python -m pytest --cov=slidev_linter --cov-report=term-missing
```

---

## Code Style & Conventions

- **Type hints**: Strict mode for source, relaxed for tests
- **Line length**: 100 characters (Ruff configuration)
- **String formatting**: Use f-strings for interpolation
- **Error handling**: Return structured error objects, don't raise in engine
- **Regex**: Use raw strings `r"..."`, compile patterns in constants
