"""Regression tests for the 1.4.0 output contract.

These tests protect the core release invariants:

1. Same facts, different presentation — all outputs derive from the same analysis.
2. Stable section structure — headings and ordering are preserved across modes.
3. Deterministic defaults — running the default path yields consistent output.
4. Packaging differences are explicit — layout changes files, not content truth.
5. Unsupported combinations fail clearly — invalid profiles/layouts produce targeted errors.
"""

from pathlib import Path

from test_support import create_repo, create_sample_repo, write

from agentskill.main import main


class TestDefaultBehavior:
    """Contract 3: deterministic defaults."""

    def test_generate_default_uses_concise_profile(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        main(["generate", str(repo)])
        default_out = capsys.readouterr().out

        main(["generate", str(repo), "--profile", "concise"])
        concise_out = capsys.readouterr().out

        assert default_out == concise_out

    def test_generate_default_uses_single_layout(self, tmp_path, monkeypatch, capsys):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(["generate", str(repo), "--out", "default.md"])
        default_text = Path("default.md").read_text()

        main(["generate", str(repo), "--layout", "single", "--out", "single.md"])
        single_text = Path("single.md").read_text()

        assert default_text == single_text

    def test_update_default_uses_single_layout(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        main(["update", str(repo)])
        default_text = (repo / "AGENTS.md").read_text()

        repo_b = create_sample_repo(tmp_path / "b")
        main(["update", str(repo_b), "--layout", "single"])
        single_text = (repo_b / "AGENTS.md").read_text()

        assert default_text == single_text


class TestStableSectionStructure:
    """Contract 2: stable section headings and ordering across modes."""

    HEADINGS = [
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

    def _h2_headings(self, text: str) -> list[str]:
        return [
            line
            for line in text.splitlines()
            if line.startswith("## ") and not line.startswith("### ")
        ]

    def test_concise_single_has_stable_headings(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path / "c")
        main(["generate", str(repo), "--profile", "concise"])
        text = capsys.readouterr().out
        headings = self._h2_headings(text)

        for expected in self.HEADINGS:
            assert expected in headings, f"Missing in concise single: {expected}"

    def test_comprehensive_single_has_stable_headings(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path / "c")
        main(["generate", str(repo), "--profile", "comprehensive"])
        text = capsys.readouterr().out
        headings = self._h2_headings(text)

        for expected in self.HEADINGS:
            assert expected in headings, f"Missing in comprehensive single: {expected}"

    def test_split_primary_has_stable_headings(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "split/AGENTS.md",
            ]
        )

        primary_text = Path("split/AGENTS.md").read_text()
        headings = self._h2_headings(primary_text)

        for expected in self.HEADINGS:
            assert expected in headings, f"Missing in split primary: {expected}"

    def test_split_companion_has_stable_headings(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "split/AGENTS.md",
            ]
        )

        companion_text = Path("split/AGENTS.reference.md").read_text()
        headings = self._h2_headings(companion_text)

        for expected in self.HEADINGS:
            assert expected in headings, f"Missing in split companion: {expected}"

    def test_multifile_root_lists_all_sections(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "mf/AGENTS.md",
            ]
        )

        root_text = Path("mf/AGENTS.md").read_text()

        expected_sections = [
            ("01_OVERVIEW.md", "Overview"),
            ("02_REPOSITORY_STRUCTURE.md", "Repository Structure"),
            ("06_CODE_FORMATTING.md", "Code Formatting"),
            ("15_RED_LINES.md", "Red Lines"),
        ]

        for filename, title in expected_sections:
            assert filename in root_text, f"Missing section link to {filename}"
            assert title in root_text, f"Missing section title {title}"

    def test_heading_order_is_identical_across_concise_and_comprehensive(
        self, tmp_path, capsys
    ):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        main(["generate", str(repo_a), "--profile", "concise"])
        concise_headings = self._h2_headings(capsys.readouterr().out)

        main(["generate", str(repo_b), "--profile", "comprehensive"])
        comp_headings = self._h2_headings(capsys.readouterr().out)

        assert concise_headings == comp_headings


class TestSameFactsDifferentPresentation:
    """Contract 1: all outputs are derived from the same analyzer results."""

    def test_concise_and_comprehensive_agree_on_test_framework(self, tmp_path, capsys):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        main(["generate", str(repo_a), "--profile", "concise"])
        concise = capsys.readouterr().out

        main(["generate", str(repo_b), "--profile", "comprehensive"])
        comp = capsys.readouterr().out

        assert "pytest" in concise
        assert "pytest" in comp

    def test_concise_and_comprehensive_agree_on_language(self, tmp_path, capsys):
        repo_a = create_sample_repo(tmp_path / "a")
        repo_b = create_sample_repo(tmp_path / "b")

        main(["generate", str(repo_a), "--profile", "concise"])
        concise = capsys.readouterr().out

        main(["generate", str(repo_b), "--profile", "comprehensive"])
        comp = capsys.readouterr().out

        assert "python" in concise.lower()
        assert "python" in comp.lower()

    def test_split_primary_and_companion_agree_on_test_framework(
        self, tmp_path, monkeypatch
    ):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "split/AGENTS.md",
            ]
        )

        primary_text = Path("split/AGENTS.md").read_text()
        companion_text = Path("split/AGENTS.reference.md").read_text()

        assert "pytest" in primary_text
        assert "pytest" in companion_text


class TestPackagingDifferences:
    """Contract 4: layout changes packaging, not content truth."""

    def test_split_primary_is_shorter_than_companion(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "split/AGENTS.md",
            ]
        )

        primary = Path("split/AGENTS.md").read_text()
        companion = Path("split/AGENTS.reference.md").read_text()
        assert len(companion) > len(primary)

    def test_split_primary_contains_link_to_companion(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "spl/AGENTS.md",
            ]
        )

        primary = Path("spl/AGENTS.md").read_text()
        assert "AGENTS.reference.md" in primary

    def test_split_companion_filename_is_deterministic(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "run_a/AGENTS.md",
            ]
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "run_b/AGENTS.md",
            ]
        )

        companion_a = Path("run_a/AGENTS.reference.md").read_text()
        companion_b = Path("run_b/AGENTS.reference.md").read_text()
        assert companion_a == companion_b

    def test_multifile_root_is_compact_index(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "mf/AGENTS.md",
            ]
        )

        root = Path("mf/AGENTS.md").read_text()

        assert "# AGENTS.md" in root
        assert "Section Index" in root

        for heading in [
            "01_OVERVIEW.md",
            "06_CODE_FORMATTING.md",
            "15_RED_LINES.md",
        ]:
            assert heading in root

    def test_multifile_section_files_have_content(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "mf/AGENTS.md",
            ]
        )

        red_lines = Path("mf/.agentskill/15_RED_LINES.md").read_text()
        assert "Do not" in red_lines

    def test_multifile_deterministic_file_tree(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "run1/AGENTS.md",
            ]
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "run2/AGENTS.md",
            ]
        )

        run1_files = sorted(p.name for p in Path("run1/.agentskill").iterdir())
        run2_files = sorted(p.name for p in Path("run2/.agentskill").iterdir())

        assert run1_files == run2_files

    def test_multifile_root_links_use_relative_paths(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "mf/AGENTS.md",
            ]
        )

        root = Path("mf/AGENTS.md").read_text()

        assert ".agentskill/01_OVERVIEW.md" in root
        assert ".agentskill/15_RED_LINES.md" in root

    def test_multifile_section_files_have_backlinks(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")
        monkeypatch.chdir(tmp_path)

        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "mf/AGENTS.md",
            ]
        )

        for section_file in Path("mf/.agentskill").iterdir():
            content = section_file.read_text()
            assert "../AGENTS.md" in content or "AGENTS.md" in content


class TestProfileLayoutInteraction:
    """Tests for how --profile and --layout interact."""

    def test_split_ignores_profile_flag_primary_is_concise(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--profile",
                "concise",
                "--out",
                "concise_split/AGENTS.md",
            ]
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--profile",
                "comprehensive",
                "--out",
                "comp_split/AGENTS.md",
            ]
        )

        concise_primary = Path("concise_split/AGENTS.md").read_text()
        comp_primary = Path("comp_split/AGENTS.md").read_text()

        assert concise_primary == comp_primary

    def test_multifile_with_concise_profile_produces_shorter_sections(
        self, tmp_path, monkeypatch
    ):
        repo = create_sample_repo(tmp_path / "repo")

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--profile",
                "concise",
                "--out",
                "concise_mf/AGENTS.md",
            ]
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--profile",
                "comprehensive",
                "--out",
                "comp_mf/AGENTS.md",
            ]
        )

        concise_red_lines = Path("concise_mf/.agentskill/15_RED_LINES.md").read_text()
        comp_red_lines = Path("comp_mf/.agentskill/15_RED_LINES.md").read_text()

        assert len(comp_red_lines) > len(concise_red_lines)

    def test_multifile_default_profile_matches_comprehensive(
        self, tmp_path, monkeypatch
    ):
        repo = create_sample_repo(tmp_path / "repo")

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "default_mf/AGENTS.md",
            ]
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--profile",
                "comprehensive",
                "--out",
                "comp_mf/AGENTS.md",
            ]
        )

        default_red_lines = Path("default_mf/.agentskill/15_RED_LINES.md").read_text()
        comp_red_lines = Path("comp_mf/.agentskill/15_RED_LINES.md").read_text()

        for heading in ["# 15. Red Lines", "Do not"]:
            assert heading in default_red_lines
            assert heading in comp_red_lines


class TestUnsupportedCombinations:
    """Contract 5: unsupported combinations fail clearly."""

    def test_invalid_profile_rejected(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "verbose"])

        assert exit_code == 1
        assert "unsupported output profile" in capsys.readouterr().err

    def test_invalid_layout_rejected(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--layout", "flat"])

        assert exit_code == 1
        assert "unsupported output layout" in capsys.readouterr().err

    def test_profile_split_rejected(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--profile", "split"])

        assert exit_code == 1
        assert "unsupported output profile" in capsys.readouterr().err

    def test_split_without_out_defaults_to_repo(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--layout", "split"])

        assert exit_code == 0
        assert (repo / "AGENTS.md").exists()
        assert (repo / "AGENTS.reference.md").exists()

    def test_multifile_without_out_defaults_to_repo(self, tmp_path):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["generate", str(repo), "--layout", "multifile"])

        assert exit_code == 0
        assert (repo / "AGENTS.md").exists()
        assert (repo / ".agentskill").is_dir()
        assert (repo / ".agentskill" / "01_OVERVIEW.md").exists()

    def test_update_layout_split_rejected(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--layout", "split"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "split" in err
        assert "not implemented yet" in err

    def test_update_layout_multifile_rejected(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--layout", "multifile"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "multifile" in err
        assert "not implemented yet" in err

    def test_update_invalid_profile_rejected(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)
        exit_code = main(["update", str(repo), "--profile", "verbose"])

        assert exit_code == 1
        assert "unsupported output profile" in capsys.readouterr().err


class TestReferenceCompatibility:
    """References should compose with layout modes."""

    def test_split_with_references_succeeds(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "target")
        reference = create_repo(tmp_path, name="reference")
        write(
            reference,
            "AGENTS.md",
            "# AGENTS\n\n## 12. Testing\nUse pytest.\n",
        )

        monkeypatch.chdir(tmp_path)
        exit_code = main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--reference",
                str(reference),
                "--out",
                "split/AGENTS.md",
            ]
        )

        assert exit_code == 0
        assert Path("split/AGENTS.md").exists()
        assert Path("split/AGENTS.reference.md").exists()

    def test_multifile_with_references_succeeds(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "target")
        reference = create_repo(tmp_path, name="reference")
        write(
            reference,
            "AGENTS.md",
            "# AGENTS\n\n## 12. Testing\nUse pytest.\n",
        )

        monkeypatch.chdir(tmp_path)
        exit_code = main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--reference",
                str(reference),
                "--out",
                "mf/AGENTS.md",
            ]
        )

        assert exit_code == 0
        assert Path("mf/AGENTS.md").exists()
        assert Path("mf/.agentskill").is_dir()

    def test_split_with_references_includes_metadata(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "target")
        reference = create_repo(tmp_path, name="reference")
        write(
            reference,
            "AGENTS.md",
            "# AGENTS\n\n## 12. Testing\nUse pytest.\n",
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--reference",
                str(reference),
                "--out",
                "split/AGENTS.md",
            ]
        )

        primary = Path("split/AGENTS.md").read_text()
        companion = Path("split/AGENTS.reference.md").read_text()

        assert "agentskill-metadata" in primary
        assert "agentskill-metadata" in companion

    def test_multifile_with_references_includes_metadata_in_root(
        self, tmp_path, monkeypatch
    ):
        repo = create_sample_repo(tmp_path / "target")
        reference = create_repo(tmp_path, name="reference")
        write(
            reference,
            "AGENTS.md",
            "# AGENTS\n\n## 12. Testing\nUse pytest.\n",
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--reference",
                str(reference),
                "--out",
                "mf/AGENTS.md",
            ]
        )

        root = Path("mf/AGENTS.md").read_text()
        assert "agentskill-metadata" in root


class TestDeterminism:
    """Deterministic output across repeated runs."""

    def test_split_deterministic_across_runs(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "a/AGENTS.md",
            ]
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "split",
                "--out",
                "b/AGENTS.md",
            ]
        )

        primary_a = Path("a/AGENTS.md").read_text()
        companion_a = Path("a/AGENTS.reference.md").read_text()
        primary_b = Path("b/AGENTS.md").read_text()
        companion_b = Path("b/AGENTS.reference.md").read_text()

        assert primary_a == primary_b
        assert companion_a == companion_b

    def test_multifile_deterministic_file_contents(self, tmp_path, monkeypatch):
        repo = create_sample_repo(tmp_path / "repo")

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "a/AGENTS.md",
            ]
        )

        monkeypatch.chdir(tmp_path)
        main(
            [
                "generate",
                str(repo),
                "--layout",
                "multifile",
                "--out",
                "b/AGENTS.md",
            ]
        )

        root_a = Path("a/AGENTS.md").read_text()
        root_b = Path("b/AGENTS.md").read_text()
        assert root_a == root_b

        for section_file in Path("a/.agentskill").iterdir():
            a_content = section_file.read_text()
            b_content = (Path("b/.agentskill") / section_file.name).read_text()
            assert a_content == b_content

    def test_single_deterministic_across_runs(self, tmp_path, capsys):
        repo = create_sample_repo(tmp_path)

        main(["generate", str(repo)])
        first = capsys.readouterr().out

        main(["generate", str(repo)])
        second = capsys.readouterr().out

        assert first == second
