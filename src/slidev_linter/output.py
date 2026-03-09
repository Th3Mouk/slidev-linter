from __future__ import annotations

import json

from .constants import OUTPUT_JSON
from .engine import RunResult


def emit_text_summary(result: RunResult) -> None:
    for item in result.per_file:
        print(f"Processing file: {item.file}")
        if item.action == "would_modify":
            print(f"❌ Would apply modifications to {item.file}")
        elif item.action == "modified":
            print(f"✅ Applied modifications to {item.file}")
        elif item.action == "no_changes":
            print(f"ℹ️ No modifications needed for {item.file}")
        elif item.action == "error":
            print(f"❌ Error for {item.file}: {item.error}")

    summary_line = (
        f"Summary: {result.files_changed}/{result.files_total} files need changes."
        if result.mode == "check"
        else f"Summary: {result.files_changed}/{result.files_total} files modified."
    )
    print(f"\n{summary_line}")

    if result.mode == "check" and result.files_changed > 0:
        print("Next: run `slidev-linter lint all` (or the same selector) to apply fixes.")


def emit_json_summary(result: RunResult) -> None:
    payload = {
        "mode": result.mode,
        "selector": result.selector,
        "rules_applied": result.rules_applied,
        "files_total": result.files_total,
        "files_changed": result.files_changed,
        "files_unchanged": result.files_unchanged,
        "errors": result.errors,
        "duration_ms": result.duration_ms,
        "per_file": [
            {
                "file": item.file,
                "changed": item.changed,
                "action": item.action,
                "error": item.error,
            }
            for item in result.per_file
        ],
    }
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def emit_error(message: str, output_format: str) -> None:
    if output_format == OUTPUT_JSON:
        print(
            json.dumps(
                {
                    "mode": "error",
                    "selector": "",
                    "rules_applied": [],
                    "files_total": 0,
                    "files_changed": 0,
                    "files_unchanged": 0,
                    "errors": [message],
                    "duration_ms": 0,
                    "per_file": [],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
    else:
        print(f"Error: {message}")
