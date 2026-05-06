from pathlib import Path

from test_support import create_sample_repo

from agentskill.lib.output_layouts import (
    DEFAULT_OUTPUT_LAYOUT,
    SUPPORTED_OUTPUT_LAYOUTS,
    validate_output_layout,
)
from agentskill.lib.output_profiles import (
    DEFAULT_OUTPUT_PROFILE,
    SUPPORTED_OUTPUT_PROFILES,
    validate_output_profile,
)
from agentskill.lib.profile_rendering import (
    RenderedSectionBody,
    build_companion_document,
    combine_section_body,
    companion_path,
    companion_relative_link,
    inject_split_link,
)
from agentskill.main import main


class TestValidateOutputProfile:
    def test_concise_is_valid(self):
        assert validate_output_profile("concise") == "concise"

    def test_comprehensive_is_valid(self):
        assert validate_output_profile("comprehensive") == "comprehensive"

    def test_default_is_concise(self):
        assert DEFAULT_OUTPUT_PROFILE == "concise"

    def test_supported_profiles_are_concise_and_comprehensive(self):
        assert set(SUPPORTED_OUTPUT_PROFILES) == {"concise", "comprehensive"}

    def test_split_is_not_a_profile(self):
        try:
            validate_output_profile("split")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "unsupported output profile" in str(exc)

    def test_invalid_profile_raises_value_error(self):
        try:
            validate_output_profile("verbose")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "unsupported output profile" in str(exc)

    def test_normalizes_uppercase(self):
        assert validate_output_profile("Concise") == "concise"

    def test_normalizes_whitespace(self):
        assert validate_output_profile("  concise  ") == "concise"


class TestValidateOutputLayout:
    def test_single_is_valid(self):
        assert validate_output_layout("single") == "single"

    def test_split_is_valid(self):
        assert validate_output_layout("split") == "split"

    def test_multifile_is_valid(self):
        assert validate_output_layout("multifile") == "multifile"

    def test_default_is_single(self):
        assert DEFAULT_OUTPUT_LAYOUT == "single"

    def test_supported_layouts_include_all_three(self):
        assert set(SUPPORTED_OUTPUT_LAYOUTS) == {"single", "split", "multifile"}

    def test_invalid_layout_raises_value_error(self):
        try:
            validate_output_layout("flat")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "unsupported output layout" in str(exc)

    def test_normalizes_uppercase(self):
        assert validate_output_layout("Single") == "single"

    def test_normalizes_whitespace(self):
        assert validate_output_layout("  multifile  ") == "multifile"


class TestGenerateProfileDefaults:
    def test_generate_defaults_to_concise(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo)])

        assert exit_code == 0
        assert "## 1. Overview\n" in capsys.readouterr().out

    def test_generate_explicit_concise(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "concise"])

        assert exit_code == 0
        assert "## 1. Overview\n" in capsys.readouterr().out

    def test_generate_comprehensive_succeeds(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "comprehensive"])

        assert exit_code == 0
        output = capsys.readouterr().out
        assert output.startswith("# AGENTS.md\n\n## 1. Overview\n")

    def test_generate_profile_split_is_invalid(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "split"])

        assert exit_code == 1
        assert "unsupported output profile" in capsys.readouterr().err

    def test_generate_invalid_profile_fails(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "verbose"])

        assert exit_code == 1
        assert "unsupported output profile" in capsys.readouterr().err

    def test_generate_concise_matches_default_output(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)

        exit_code_default = main(["generate", str(repo)])
        assert exit_code_default == 0
        default_out = capsys.readouterr().out

        exit_code_concise = main(["generate", str(repo), "--profile", "concise"])
        assert exit_code_concise == 0
        concise_out = capsys.readouterr().out

        assert default_out == concise_out


class TestUpdateProfileDefaults:
    def test_update_defaults_to_concise(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo)])

        assert exit_code == 0
        assert (repo / "AGENTS.md").exists()

    def test_update_explicit_concise(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "concise"])

        assert exit_code == 0
        assert (repo / "AGENTS.md").exists()

    def test_update_comprehensive_succeeds(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "comprehensive"])

        assert exit_code == 0
        assert (repo / "AGENTS.md").exists()

    def test_update_layout_split_not_implemented(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--layout", "split"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "split" in err and "not implemented yet" in err

    def test_update_layout_multifile_not_implemented(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--layout", "multifile"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "multifile" in err and "not implemented yet" in err

    def test_update_invalid_profile_fails(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "verbose"])

        assert exit_code == 1
        assert "unsupported output profile" in capsys.readouterr().err

    def test_update_concise_matches_default_output(self, tmp_path):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        exit_code_default = main(["update", str(repo_a)])
        assert exit_code_default == 0
        default_text = (repo_a / "AGENTS.md").read_text()

        exit_code_concise = main(["update", str(repo_b), "--profile", "concise"])
        assert exit_code_concise == 0
        concise_text = (repo_b / "AGENTS.md").read_text()

        assert default_text == concise_text


class TestCombineSectionBody:
    def test_concise_returns_core_only(self):
        body = RenderedSectionBody(core="alpha\n", expanded="beta\n")
        assert combine_section_body("concise", body) == "alpha\n"

    def test_comprehensive_returns_core_plus_expanded(self):
        body = RenderedSectionBody(core="alpha\n", expanded="beta\n")
        assert combine_section_body("comprehensive", body) == "alpha\nbeta\n"

    def test_empty_expanded_concise(self):
        body = RenderedSectionBody(core="alpha\n")
        assert combine_section_body("concise", body) == "alpha\n"

    def test_empty_expanded_comprehensive(self):
        body = RenderedSectionBody(core="alpha\n")
        assert combine_section_body("comprehensive", body) == "alpha\n"


SECTION_HEADINGS_IN_ORDER = [
    "## 1. Overview",
    "## 2. Repository Structure",
    "## 5. Commands and Workflows",
    "## 6. Code Formatting",
    "## 7. Naming Conventions",
    "## 8. Type Annotations",
    "## 9. Imports",
    "## 10. Error Handling",
    "## 11. Comments and Docstrings",
    "## 12. Testing",
    "## 13. Git",
    "## 14. Dependencies and Tooling",
    "## 15. Red Lines",
]


class TestProfileStructuralInvariants:
    def _headings(self, text: str) -> list[str]:
        return [
            line
            for line in text.splitlines()
            if line.startswith("## ") and not line.startswith("### ")
        ]

    def test_concise_has_all_section_headings(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path / "c")
        main(["generate", str(repo), "--profile", "concise"])
        concise = capsys.readouterr().out
        headings = self._headings(concise)

        for expected in SECTION_HEADINGS_IN_ORDER:
            assert expected in headings, f"Missing heading in concise: {expected}"

    def test_comprehensive_has_all_section_headings(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path / "c")
        main(["generate", str(repo), "--profile", "comprehensive"])
        comprehensive = capsys.readouterr().out
        headings = self._headings(comprehensive)

        for expected in SECTION_HEADINGS_IN_ORDER:
            assert expected in headings, f"Missing heading in comprehensive: {expected}"

    def test_headings_are_in_same_order(self, tmp_path, capsys):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")
        main(["generate", str(repo_a), "--profile", "concise"])
        concise_headings = self._headings(capsys.readouterr().out)
        main(["generate", str(repo_b), "--profile", "comprehensive"])
        comp_headings = self._headings(capsys.readouterr().out)
        assert concise_headings == comp_headings


class TestProfileDensityDifferences:
    def test_comprehensive_is_longer_than_concise(self, tmp_path, capsys):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")
        main(["generate", str(repo_a), "--profile", "concise"])
        concise_len = len(capsys.readouterr().out)
        main(["generate", str(repo_b), "--profile", "comprehensive"])
        comp_len = len(capsys.readouterr().out)
        assert comp_len > concise_len

    def test_concise_omits_code_formatting_snippet(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        main(["generate", str(repo), "--profile", "concise"])
        concise = capsys.readouterr().out
        concise_formatting_start = concise.index("## 6. Code Formatting")
        concise_formatting_end = concise.index("## 7. Naming Conventions")
        concise_formatting = concise[concise_formatting_start:concise_formatting_end]
        assert "```" not in concise_formatting

    def test_comprehensive_formatting_includes_indent_rule(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        main(["generate", str(repo), "--profile", "comprehensive"])
        comp = capsys.readouterr().out
        comp_formatting_start = comp.index("## 6. Code Formatting")
        comp_formatting_end = comp.index("## 7. Naming Conventions")
        comp_formatting = comp[comp_formatting_start:comp_formatting_end]
        assert "Indent with" in comp_formatting

    def test_concise_omits_import_block(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        main(["generate", str(repo), "--profile", "concise"])
        concise = capsys.readouterr().out
        imports_start = concise.index("## 9. Imports")
        imports_end = concise.index("## 10. Error Handling")
        concise_imports = concise[imports_start:imports_end]
        assert "```python" not in concise_imports

    def test_comprehensive_includes_import_block(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        main(["generate", str(repo), "--profile", "comprehensive"])
        comp = capsys.readouterr().out
        imports_start = comp.index("## 9. Imports")
        imports_end = comp.index("## 10. Error Handling")
        comp_imports = comp[imports_start:imports_end]
        assert "```" in comp_imports


class TestProfileFactConsistency:
    def test_both_profiles_mention_same_test_framework(self, tmp_path, capsys):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        main(["generate", str(repo_a), "--profile", "concise"])
        concise = capsys.readouterr().out

        main(["generate", str(repo_b), "--profile", "comprehensive"])
        comp = capsys.readouterr().out

        assert "pytest" in concise
        assert "pytest" in comp

    def test_both_profiles_mention_indentation_rule(self, tmp_path, capsys):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        main(["generate", str(repo_a), "--profile", "concise"])
        concise = capsys.readouterr().out

        main(["generate", str(repo_b), "--profile", "comprehensive"])
        comp = capsys.readouterr().out

        assert "Indent with" in concise
        assert "Indent with" in comp

    def test_both_profiles_mention_red_lines(self, tmp_path, capsys):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        main(["generate", str(repo_a), "--profile", "concise"])
        concise = capsys.readouterr().out

        main(["generate", str(repo_b), "--profile", "comprehensive"])
        comp = capsys.readouterr().out

        assert "Do not" in concise
        assert "Do not" in comp

    def test_update_uses_selected_profile_density(self, tmp_path):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        main(["update", str(repo_a), "--profile", "concise"])
        concise_text = (repo_a / "AGENTS.md").read_text()

        main(["update", str(repo_b), "--profile", "comprehensive"])
        comp_text = (repo_b / "AGENTS.md").read_text()

        assert len(comp_text) > len(concise_text)


class TestCompanionPath:
    def test_companion_path_beside_agents_md(self):
        primary = Path("AGENTS.md")
        assert companion_path(primary) == Path("AGENTS.reference.md")

    def test_companion_path_with_directory(self):
        primary = Path("docs/AGENTS.md")
        assert companion_path(primary) == Path("docs/AGENTS.reference.md")

    def test_companion_path_custom_name(self):
        primary = Path("output/MY_DOCS.md")
        assert companion_path(primary) == Path("output/MY_DOCS.reference.md")

    def test_companion_path_no_md_extension(self):
        primary = Path("output/notes")
        assert companion_path(primary) == Path("output/notes.reference.md")

    def test_companion_relative_link(self):
        primary = Path("AGENTS.md")
        link = companion_relative_link(primary)
        assert "AGENTS.reference.md" in link
        assert "./" in link

    def test_companion_relative_link_with_directory(self):
        primary = Path("docs/AGENTS.md")
        link = companion_relative_link(primary)
        assert "AGENTS.reference.md" in link


class TestInjectSplitLink:
    def test_injects_link_after_title(self):
        markdown = "# AGENTS.md\n\n## 1. Overview\nSome text.\n"
        primary_path = Path("AGENTS.md")
        result = inject_split_link(markdown, primary_path)
        assert result.startswith("# AGENTS.md\n\n> Extended reference:")
        assert "AGENTS.reference.md" in result
        assert "## 1. Overview" in result

    def test_injects_link_when_no_title(self):
        markdown = "## 1. Overview\nSome text.\n"
        primary_path = Path("AGENTS.md")
        result = inject_split_link(markdown, primary_path)
        assert result.startswith("> Extended reference:")
        assert "AGENTS.reference.md" in result


class TestBuildCompanionDocument:
    def test_replaces_title(self):
        markdown = "# AGENTS.md\n\n## 1. Overview\nSome text.\n"
        result = build_companion_document(markdown)

        assert result.startswith(
            "> Extended reference document for the main AGENTS.md.\n\n# AGENTS Reference\n"
        )

        assert "## 1. Overview" in result
        assert "# AGENTS.md" not in result

    def test_preserves_content_without_title(self):
        markdown = "## 1. Overview\nSome text.\n"
        result = build_companion_document(markdown)
        assert "## 1. Overview" in result


class TestSplitGeneration:
    def test_split_writes_primary_and_companion(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        exit_code = main(
            ["generate", str(repo), "--layout", "split", "--out", str(out_file)]
        )

        assert exit_code == 0
        primary = Path("output/AGENTS.md")
        companion = Path("output/AGENTS.reference.md")
        assert primary.exists()
        assert companion.exists()

    def test_primary_contains_link_to_companion(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(["generate", str(repo), "--layout", "split", "--out", str(out_file)])
        primary_text = Path("output/AGENTS.md").read_text()
        assert "AGENTS.reference.md" in primary_text

    def test_primary_is_concise_content(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(["generate", str(repo), "--layout", "split", "--out", str(out_file)])
        primary_text = Path("output/AGENTS.md").read_text()
        assert "## 1. Overview" in primary_text

    def test_companion_has_reference_title(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(["generate", str(repo), "--layout", "split", "--out", str(out_file)])
        companion_text = Path("output/AGENTS.reference.md").read_text()
        assert "# AGENTS Reference" in companion_text

    def test_companion_is_longer_than_primary(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(["generate", str(repo), "--layout", "split", "--out", str(out_file)])
        primary_text = Path("output/AGENTS.md").read_text()
        companion_text = Path("output/AGENTS.reference.md").read_text()
        assert len(companion_text) > len(primary_text)

    def test_split_preserves_section_order_in_both(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(["generate", str(repo), "--layout", "split", "--out", str(out_file)])
        primary_text = Path("output/AGENTS.md").read_text()
        companion_text = Path("output/AGENTS.reference.md").read_text()

        primary_headings = [
            line
            for line in primary_text.splitlines()
            if line.startswith("## ") and not line.startswith("### ")
        ]

        companion_headings = [
            line
            for line in companion_text.splitlines()
            if line.startswith("## ") and not line.startswith("### ")
        ]

        assert primary_headings == companion_headings

    def test_split_deterministic_across_runs(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        out_a = Path("run_a/AGENTS.md")
        main(["generate", str(repo), "--layout", "split", "--out", str(out_a)])
        primary_a = Path("run_a/AGENTS.md").read_text()

        out_b = Path("run_b/AGENTS.md")
        main(["generate", str(repo), "--layout", "split", "--out", str(out_b)])
        primary_b = Path("run_b/AGENTS.md").read_text()

        assert primary_a == primary_b


class TestSplitFailurePaths:
    def test_split_without_out_fails(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--layout", "split"])

        assert exit_code == 1
        assert "--out" in capsys.readouterr().err

    def test_update_layout_split_rejected(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--layout", "split"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "split" in err and "not implemented yet" in err


class TestMultifileGeneration:
    def test_multifile_writes_root_and_section_files(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        exit_code = main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                str(out_file),
            ]
        )

        assert exit_code == 0
        assert Path("output/AGENTS.md").exists()
        assert Path("output/agents").is_dir()
        assert Path("output/agents/01_OVERVIEW.md").exists()
        assert Path("output/agents/15_RED_LINES.md").exists()

    def test_root_contains_section_index(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                str(out_file),
            ]
        )

        root_text = Path("output/AGENTS.md").read_text()
        assert "# AGENTS.md" in root_text
        assert "Section Index" in root_text
        assert "agents/01_OVERVIEW.md" in root_text
        assert "agents/15_RED_LINES.md" in root_text

    def test_root_does_not_contain_full_section_content(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                str(out_file),
            ]
        )

        root_text = Path("output/AGENTS.md").read_text()
        assert "## 6. Code Formatting" not in root_text

    def test_section_files_contain_headings(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                str(out_file),
            ]
        )

        overview_text = Path("output/agents/01_OVERVIEW.md").read_text()
        assert "# 1. Overview" in overview_text

    def test_section_files_contain_backlinks(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                str(out_file),
            ]
        )

        overview_text = Path("output/agents/01_OVERVIEW.md").read_text()
        assert "AGENTS.md" in overview_text

    def test_section_files_have_correct_names(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_file = Path("output/AGENTS.md")

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                str(out_file),
            ]
        )

        expected_files = [
            "01_OVERVIEW.md",
            "02_REPOSITORY_STRUCTURE.md",
            "05_COMMANDS_AND_WORKFLOWS.md",
            "06_CODE_FORMATTING.md",
            "15_RED_LINES.md",
        ]

        agents_dir = Path("output/agents")
        for filename in expected_files:
            assert (agents_dir / filename).exists(), f"Missing section file: {filename}"

    def test_multifile_deterministic_across_runs(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        out_a = Path("run_a/AGENTS.md")
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                str(out_a),
            ]
        )

        root_a = Path("run_a/AGENTS.md").read_text()
        out_b = Path("run_b/AGENTS.md")

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                str(out_b),
            ]
        )

        root_b = Path("run_b/AGENTS.md").read_text()
        assert root_a == root_b

    def test_multifile_with_profile_comprehensive(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)
        out_concise = Path("concise/AGENTS.md")
        out_comp = Path("comp/AGENTS.md")

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--profile",
                "concise",
                "--out",
                str(out_concise),
            ]
        )

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--profile",
                "comprehensive",
                "--out",
                str(out_comp),
            ]
        )

        concise_red_lines = Path("concise/agents/15_RED_LINES.md").read_text()
        comp_red_lines = Path("comp/agents/15_RED_LINES.md").read_text()
        assert len(comp_red_lines) > len(concise_red_lines)


class TestMultifileFailurePaths:
    def test_multifile_without_out_fails(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--layout", "multifile"])

        assert exit_code == 1
        assert "--out" in capsys.readouterr().err

    def test_update_layout_multifile_rejected(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--layout", "multifile"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "multifile" in err and "not implemented yet" in err
