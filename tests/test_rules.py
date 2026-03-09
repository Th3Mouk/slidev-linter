from __future__ import annotations

import pytest

import slidev_linter as sl


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("# **Title**\n", "# Title\n"),
        ("# Title\n", "# Title\n"),
    ],
)
def test_remove_bold_from_titles_rule(content: str, expected: str) -> None:
    assert sl.RemoveBoldFromTitlesRule().apply(content) == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("# Title\n## Subtitle\n", "# Title\n\n## Subtitle\n"),
        ("# Title\n\n## Subtitle\n", "# Title\n\n## Subtitle\n"),
    ],
)
def test_ensure_space_between_title_subtitle_rule(content: str, expected: str) -> None:
    assert sl.EnsureSpaceBetweenTitleAndSubtitleRule().apply(content) == expected


def test_default_transition_no_frontmatter_is_noop() -> None:
    content = "# Intro\n"
    assert sl.DefaultTransitionRule().apply(content) == content


def test_default_transition_malformed_frontmatter_is_noop() -> None:
    content = "---\ntitle: Demo\n# Intro\n"
    assert sl.DefaultTransitionRule().apply(content) == content


def test_default_transition_replaces_existing_value() -> None:
    content = "---\ntitle: Demo\ntransition: fade\n---\n# Intro\n"
    result = sl.DefaultTransitionRule().apply(content)
    assert "transition: slide-left" in result
    assert "transition: fade" not in result


def test_default_transition_adds_missing_transition() -> None:
    content = "---\ntitle: Demo\n---\n# Intro\n"
    result = sl.DefaultTransitionRule().apply(content)
    assert "title: Demo\ntransition: slide-left" in result


def test_default_transition_only_updates_top_frontmatter() -> None:
    content = (
        "---\n"
        "title: Demo\n"
        "transition: fade\n"
        "---\n"
        "# Intro\n"
        "\n---\n"
        "layout: section\n"
        "transition: zoom\n"
        "---\n"
        "# Next\n"
    )
    result = sl.DefaultTransitionRule().apply(content)
    assert "title: Demo\ntransition: slide-left" in result
    assert "layout: section\ntransition: zoom" in result


@pytest.mark.parametrize(
    ("content", "expected_contains", "expected_not_contains"),
    [
        (
            "---\ntitle: Demo\n---\n# Intro\n\n---\nlayout: section\n---\n# Section\n",
            "layout: section\ntransition: slide-left",
            "",
        ),
        (
            "---\ntitle: Demo\n---\n# Intro\n\n---\nlayout: section\ntransition: fade\n---\n# Section\n",
            "layout: section\ntransition: slide-left",
            "layout: section\ntransition: fade",
        ),
    ],
)
def test_section_transition_rule_for_section_slides(
    content: str, expected_contains: str, expected_not_contains: str
) -> None:
    result = sl.SectionTransitionRule().apply(content)
    assert expected_contains in result
    if expected_not_contains:
        assert expected_not_contains not in result


def test_section_transition_ignores_non_section_blocks() -> None:
    content = "---\ntitle: Demo\n---\n# Intro\n\n---\nlayout: image-right\n---\n# Next\n"
    result = sl.SectionTransitionRule().apply(content)
    assert "transition: slide-left" not in result.split("\n---\nlayout: image-right\n")[-1]


def test_section_transition_ignores_non_metadata_blocks() -> None:
    content = "---\ntitle: Demo\n---\n# Intro\n\n---\n# Not metadata block\n---\n# Next\n"
    assert sl.SectionTransitionRule().apply(content) == content


def test_section_transition_ignores_unclosed_metadata_block() -> None:
    content = "---\ntitle: Demo\n---\n# Intro\n\n---\nlayout: section\n# Missing closing separator\n"
    assert sl.SectionTransitionRule().apply(content) == content


def test_clean_transitions_keeps_top_frontmatter_transition() -> None:
    content = (
        "---\n"
        "transition: slide-left\n"
        "theme: default\n"
        "---\n"
        "# Intro\n"
        "\n---\n"
        "transition: slide-left\n"
        "# Body\n"
    )
    result = sl.CleanTransitionsRule().apply(content)
    assert "transition: slide-left\ntheme: default" in result
    assert "\n---\ntransition: slide-left\n# Body" not in result


def test_clean_transitions_normalizes_body_spacing_and_duplicate_tags() -> None:
    content = (
        "---\ntitle: Demo\n---\n# Intro\n"
        "\n---\n# Body\n"
        '<p class="py-2"/>\n'
        '<p class="py-2"/>\n'
        "Text\n"
    )
    result = sl.CleanTransitionsRule().apply(content)
    assert '<p class="py-2"/>\n<p class="py-2"/>' not in result


def test_clean_transitions_without_frontmatter_normalizes_first_separator() -> None:
    content = "---\n\n# Slide\n"
    assert sl.CleanTransitionsRule().apply(content).startswith("---\n# Slide\n")


def test_add_spacing_after_titles_requires_frontmatter() -> None:
    content = "# Intro\nBody\n"
    assert sl.AddSpacingAfterTitlesRule().apply(content) == content


def test_add_spacing_after_titles_preserves_presenter_notes() -> None:
    content = (
        "---\ntitle: Demo\n---\n# Intro\n"
        "\n---\n"
        "# Slide\n"
        "<!-- presenter note -->\n"
        "Text\n"
    )
    result = sl.AddSpacingAfterTitlesRule().apply(content)
    assert "<!-- presenter note -->" in result
    assert '<p class="py-2"/>' in result


@pytest.mark.parametrize(
    ("body_after_title", "should_add_spacing"),
    [
        ("Body\n", True),
        ("## Subtitle\n", False),
        ("| col |\n| --- |\n", False),
        ("```ts\nconst x = 1\n```\n", False),
    ],
)
def test_add_spacing_after_titles_guards(body_after_title: str, should_add_spacing: bool) -> None:
    content = f"---\ntitle: Demo\n---\n# Intro\n\n---\n# Slide\n{body_after_title}"
    result = sl.AddSpacingAfterTitlesRule().apply(content)
    has_spacing = '<p class="py-2"/>\n' in result
    assert has_spacing is should_add_spacing


def test_add_spacing_after_titles_deduplicates_existing_spacing_tag() -> None:
    content = (
        "---\ntitle: Demo\n---\n# Intro\n\n---\n# Slide\n"
        '<p class="py-2"/>\n'
        '<p class="py-2"/>\n'
        "Body\n"
    )
    result = sl.AddSpacingAfterTitlesRule().apply(content)
    assert result.count('<p class="py-2"/>') == 1


def test_add_spacing_after_titles_handles_multiple_slides() -> None:
    content = (
        "---\ntitle: Demo\n---\n# Intro\n"
        "\n---\n# Slide One\nBody\n"
        "\n---\n# Slide Two\nBody\n"
    )
    result = sl.AddSpacingAfterTitlesRule().apply(content)
    assert result.count('<p class="py-2"/>') == 2


@pytest.mark.parametrize(
    "rule",
    [
        sl.RemoveBoldFromTitlesRule(),
        sl.DefaultTransitionRule(),
        sl.SectionTransitionRule(),
        sl.CleanTransitionsRule(),
        sl.AddSpacingAfterTitlesRule(),
        sl.EnsureSpaceBetweenTitleAndSubtitleRule(),
    ],
)
def test_each_rule_is_idempotent(rule: sl.Rule) -> None:
    content = (
        "---\n"
        "title: Demo\n"
        "transition: fade\n"
        "---\n"
        "# **Intro**\n"
        "## Subtitle\n"
        "\n---\n"
        "layout: section\n"
        "transition: zoom\n"
        "---\n"
        "# Section slide\n"
        "<!-- note -->\n"
        "Body\n"
    )
    once = rule.apply(content)
    twice = rule.apply(once)
    assert twice == once
