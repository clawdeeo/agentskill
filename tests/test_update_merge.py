from lib.agents_document import build_section
from lib.update_merge import MergeResult, merge_agents_document


def test_merge_replaces_one_existing_section():
    existing = (
        "# Overview\n"
        "Original overview.\n"
        "## Testing\n"
        "Keep these notes.\n"
        "## Git\n"
        "Linear history.\n"
    )

    result = merge_agents_document(
        existing,
        {
            "overview": build_section(
                "Overview", "Updated overview.\n", heading_level=1
            ),
        },
    )

    assert result == MergeResult(
        text=(
            "# Overview\n"
            "Updated overview.\n"
            "## Testing\n"
            "Keep these notes.\n"
            "## Git\n"
            "Linear history.\n"
        ),
        updated_sections=["overview"],
        preserved_sections=["testing", "git"],
        added_sections=[],
        removed_sections=[],
        forced=False,
    )


def test_merge_replaces_multiple_sections_and_preserves_order():
    existing = (
        "# Overview\n"
        "Old overview.\n"
        "## Commands and Workflows\n"
        "Old commands.\n"
        "## Testing\n"
        "Old testing.\n"
    )

    result = merge_agents_document(
        existing,
        {
            "overview": build_section("Overview", "New overview.\n", heading_level=1),
            "commands and workflows": build_section(
                "Commands and Workflows",
                "New commands.\n",
            ),
        },
    )

    assert result.text == (
        "# Overview\n"
        "New overview.\n"
        "## Commands and Workflows\n"
        "New commands.\n"
        "## Testing\n"
        "Old testing.\n"
    )

    assert result.updated_sections == ["overview", "commands and workflows"]
    assert result.preserved_sections == ["testing"]
    assert result.added_sections == []
    assert result.removed_sections == []


def test_merge_preserves_untouched_manual_edits_and_custom_sections():
    existing = (
        "Manual preamble.\n\n"
        "# Overview\n"
        "Generated summary.\n"
        "## Team Notes\n"
        "Manual notes stay here.\n"
        "## Testing\n"
        "Locally edited testing text.\n"
    )

    result = merge_agents_document(
        existing,
        {
            "overview": build_section(
                "Overview", "Refreshed summary.\n", heading_level=1
            ),
        },
    )

    assert result.text == (
        "Manual preamble.\n\n"
        "# Overview\n"
        "Refreshed summary.\n"
        "## Team Notes\n"
        "Manual notes stay here.\n"
        "## Testing\n"
        "Locally edited testing text.\n"
    )

    assert result.preserved_sections == ["team notes", "testing"]


def test_merge_adds_missing_section_at_end():
    existing = "# Overview\nSummary.\n"

    result = merge_agents_document(
        existing,
        {
            "testing": build_section("Testing", "Added test guidance.\n"),
        },
    )

    assert result.text == ("# Overview\nSummary.\n## Testing\nAdded test guidance.\n")
    assert result.updated_sections == []
    assert result.preserved_sections == ["overview"]
    assert result.added_sections == ["testing"]


def test_merge_include_only_filters_targets():
    existing = "# Overview\nOld overview.\n## Testing\nOld testing.\n"

    result = merge_agents_document(
        existing,
        {
            "overview": build_section("Overview", "New overview.\n", heading_level=1),
            "testing": build_section("Testing", "New testing.\n"),
        },
        include_sections=[" testing "],
    )

    assert result.text == ("# Overview\nOld overview.\n## Testing\nNew testing.\n")
    assert result.updated_sections == ["testing"]
    assert result.preserved_sections == ["overview"]


def test_merge_exclude_filters_targets():
    existing = "# Overview\nOld overview.\n## Testing\nOld testing.\n"

    result = merge_agents_document(
        existing,
        {
            "overview": build_section("Overview", "New overview.\n", heading_level=1),
            "testing": build_section("Testing", "New testing.\n"),
        },
        exclude_sections=["overview"],
    )

    assert result.text == ("# Overview\nOld overview.\n## Testing\nNew testing.\n")
    assert result.updated_sections == ["testing"]
    assert result.preserved_sections == ["overview"]


def test_merge_rejects_include_exclude_overlap():
    try:
        merge_agents_document(
            "# Overview\nOld overview.\n",
            {
                "overview": build_section(
                    "Overview",
                    "New overview.\n",
                    heading_level=1,
                ),
            },
            include_sections=["Overview"],
            exclude_sections=[" overview "],
        )

        raise AssertionError("should have raised ValueError")
    except ValueError as exc:
        assert str(exc) == (
            "section names cannot be both included and excluded: overview"
        )


def test_merge_rejects_duplicate_normalized_regenerated_names():
    try:
        merge_agents_document(
            None,
            {
                "Overview": build_section("Overview", "One.\n", heading_level=1),
                " overview ": build_section("Overview", "Two.\n", heading_level=1),
            },
        )

        raise AssertionError("should have raised ValueError")
    except ValueError as exc:
        assert str(exc) == (
            "duplicate regenerated section after normalization:  overview "
        )


def test_force_mode_rebuilds_clean_slate():
    existing = (
        "Manual preamble.\n\n"
        "# Overview\n"
        "Old overview.\n"
        "## Team Notes\n"
        "Custom notes.\n"
        "## Testing\n"
        "Old testing.\n"
    )

    result = merge_agents_document(
        existing,
        {
            "testing": build_section("Testing", "Fresh testing.\n"),
            "overview": build_section("Overview", "Fresh overview.\n", heading_level=1),
        },
        force=True,
    )

    assert result == MergeResult(
        text="# Overview\nFresh overview.\n## Testing\nFresh testing.\n",
        updated_sections=["overview", "testing"],
        preserved_sections=[],
        added_sections=[],
        removed_sections=["team notes"],
        forced=True,
    )
