from pathlib import Path

from test_support import create_sample_repo, write

from agentskill.main import main


def test_update_creates_agents_file_when_missing(tmp_path):
    repo = create_sample_repo(tmp_path)

    exit_code = main(["update", str(repo)])
    assert exit_code == 0

    agents_text = (repo / "AGENTS.md").read_text()
    assert agents_text.startswith("# AGENTS.md\n\n## 1. Overview\n")
    assert "## 5. Commands and Workflows\n" in agents_text
    assert "## 12. Testing\n" in agents_text


def test_update_preserves_untouched_sections_with_include_filter(tmp_path):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        "AGENTS.md",
        (
            "# AGENTS\n\n"
            "## 1. Overview\n"
            "Old overview.\n"
            "## 12. Testing\n"
            "Manual testing notes.\n"
        ),
    )

    exit_code = main(["update", str(repo), "--section", "overview"])

    assert exit_code == 0

    agents_text = (repo / "AGENTS.md").read_text()
    assert "Old overview.\n" not in agents_text
    assert "Manual testing notes.\n" in agents_text


def test_update_excludes_selected_section(tmp_path):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        "AGENTS.md",
        ("# AGENTS\n\n## 1. Overview\nOld overview.\n## 12. Testing\nOld testing.\n"),
    )

    exit_code = main(["update", str(repo), "--exclude-section", "overview"])
    assert exit_code == 0

    agents_text = (repo / "AGENTS.md").read_text()
    assert "Old overview.\n" in agents_text
    assert "Old testing.\n" not in agents_text


def test_update_force_rebuild_drops_custom_sections(tmp_path):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        "AGENTS.md",
        (
            "# AGENTS\n\n"
            "## Team Notes\n"
            "Keep this manually.\n"
            "## 12. Testing\n"
            "Old testing.\n"
        ),
    )

    exit_code = main(["update", str(repo), "--force"])
    assert exit_code == 0

    agents_text = (repo / "AGENTS.md").read_text()
    assert "Team Notes" not in agents_text
    assert agents_text.startswith("# AGENTS.md\n\n## 1. Overview\n")


def test_update_rejects_conflicting_include_and_exclude(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)

    exit_code = main(
        [
            "update",
            str(repo),
            "--section",
            "overview",
            "--exclude-section",
            "overview",
        ]
    )

    assert exit_code == 1
    assert "both included and excluded" in capsys.readouterr().err


def test_update_supports_custom_output_path(tmp_path, monkeypatch):
    repo = create_sample_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    out_path = Path("generated/AGENTS-new.md")

    exit_code = main(["update", str(repo), "--out", str(out_path)])

    assert exit_code == 0
    assert out_path.exists()
    assert not (repo / "AGENTS.md").exists()


def test_update_preserves_manual_preamble_and_custom_sections_in_normal_mode(tmp_path):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        "AGENTS.md",
        (
            "Manual preamble.\n\n"
            "## Team Notes\n"
            "Keep this manual section.\n\n"
            "## 12. Testing\n"
            "Old testing.\n"
        ),
    )

    exit_code = main(["update", str(repo), "--section", "testing"])

    assert exit_code == 0
    agents_text = (repo / "AGENTS.md").read_text()
    assert agents_text.startswith("Manual preamble.\n\n## Team Notes\n")
    assert "Keep this manual section.\n" in agents_text
    assert "Old testing.\n" not in agents_text


def test_update_adds_missing_targeted_section_without_rewriting_other_content(tmp_path):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        "AGENTS.md",
        (
            "# AGENTS\n\n"
            "## 1. Overview\n"
            "Manual overview.\n\n"
            "## Team Notes\n"
            "Keep these notes.\n"
        ),
    )

    exit_code = main(["update", str(repo), "--section", "testing"])

    assert exit_code == 0
    agents_text = (repo / "AGENTS.md").read_text()
    assert "Manual overview.\n" in agents_text
    assert "Keep these notes.\n" in agents_text
    assert "## 12. Testing\n" in agents_text


def test_update_out_uses_existing_repo_agents_as_merge_input(tmp_path, monkeypatch):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        "AGENTS.md",
        (
            "Manual preamble.\n\n"
            "## Team Notes\n"
            "Keep this manual section.\n\n"
            "## 12. Testing\n"
            "Old testing.\n"
        ),
    )

    monkeypatch.chdir(tmp_path)
    out_path = Path("generated/AGENTS-new.md")

    exit_code = main(
        ["update", str(repo), "--section", "testing", "--out", str(out_path)]
    )

    assert exit_code == 0
    generated = out_path.read_text()
    assert generated.startswith("Manual preamble.\n\n## Team Notes\n")
    assert "Keep this manual section.\n" in generated
    assert "Old testing.\n" not in generated
    assert "Old testing.\n" in (repo / "AGENTS.md").read_text()
