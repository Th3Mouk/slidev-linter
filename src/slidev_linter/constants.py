from __future__ import annotations

import re

DEFAULT_TRANSITION = "slide-left"
SECTION_TRANSITION = "slide-left"
DEFAULT_RULE_SET = "advanced_formatting"

AVAILABLE_TRANSITIONS = [
    "slide-left",
    "slide-right",
    "slide-up",
    "slide-down",
    "fade",
    "zoom",
]

EXIT_OK = 0
EXIT_CHECK_DIRTY = 1
EXIT_USAGE_ERROR = 2
EXIT_RUNTIME_ERROR = 3

OUTPUT_TEXT = "text"
OUTPUT_JSON = "json"

FRONTMATTER_RE = re.compile(r"^---\s*\n(?P<meta>.*?)\n---\s*\n?", re.DOTALL)
