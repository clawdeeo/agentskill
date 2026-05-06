from test_support import create_sample_repo

from agentskill.lib.output_profiles import (
    DEFAULT_OUTPUT_PROFILE,
    SUPPORTED_OUTPUT_PROFILES,
    validate_output_profile,
)
from agentskill.lib.profile_rendering import RenderedSectionBody, combine_section_body
from agentskill.main import main


class TestValidateOutputProfile:
    def test_concise_is_valid(self):
        assert validate_output_profile("concise") == "concise"

    def test_comprehensive_is_valid(self):
        assert validate_output_profile("comprehensive") == "comprehensive"

    def test_split_is_valid(self):
        assert validate_output_profile("split") == "split"

    def test_default_is_concise(self):
        assert DEFAULT_OUTPUT_PROFILE == "concise"

    def test_supported_profiles_include_all_three(self):
        assert set(SUPPORTED_OUTPUT_PROFILES) == {"concise", "comprehensive", "split"}

    def test_invalid_profile_raises_value_error(self):
        try:
            validate_output_profile("verbose")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "unsupported output profile" in str(exc)

    def test_empty_profile_raises_value_error(self):
        try:
            validate_output_profile("")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "unsupported output profile" in str(exc)

    def test_normalizes_uppercase(self):
        assert validate_output_profile("Concise") == "concise"

    def test_normalizes_whitespace(self):
        assert validate_output_profile("  concise  ") == "concise"

    def test_error_message_lists_allowed_values(self):
        try:
            validate_output_profile("detailed")
            raise AssertionError("should have raised ValueError")
        except ValueError as exc:
            assert "concise, comprehensive, split" in str(exc)


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

    def test_generate_split_is_accepted_but_not_implemented(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "split"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "split" in err and "not implemented yet" in err

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

    def test_update_split_is_accepted_but_not_implemented(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "split"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "split" in err and "not implemented yet" in err

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
