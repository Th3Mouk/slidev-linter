# Changelog

All notable changes to this project will be documented in this file.

## v0.3.0

### Added
- Declarative rule registry and rule-set specifications in the engine.
- Dedicated frontmatter helpers for parsing and metadata updates.
- `--explain` support for per-rule impact reporting.
- `--fail-on-error` support for `check` mode.
- `list rule-sets --verbose` and JSON output for listing commands.

### Changed
- Rule execution now isolates failures per file and reports the failed rule.
- Text and JSON outputs now include richer diagnostics.
- Frontmatter and metadata handling were centralized into `frontmatter.py`.
- Technical architecture documentation was updated to reflect the new structure.

### Fixed
- `check all --fail-on-error` is now accepted in the natural CLI position.
- Long-standing regex and frontmatter edge cases were hardened.

### Tests
- Added coverage for explain mode, rule execution errors, and list command variants.
- Added architecture consistency checks for rule sets and registered rules.
