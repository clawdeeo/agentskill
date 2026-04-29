from pathlib import Path

from test_support import create_sample_repo, write

import cli


def test_generate_prints_markdown_to_stdout_without_writing_repo_file(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = cli.main(["generate", str(repo)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("# AGENTS\n\n## 1. Overview\n")
    assert "## 5. Commands and Workflows\n" in captured.out
    assert not (repo / "AGENTS.md").exists()
    assert captured.err == ""


def test_generate_writes_markdown_to_explicit_output_path(
    tmp_path, monkeypatch, capsys
):
    repo = create_sample_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    out_path = Path("generated/AGENTS.md")

    exit_code = cli.main(["generate", str(repo), "--out", str(out_path)])

    assert exit_code == 0
    assert out_path.exists()
    assert out_path.read_text().startswith("# AGENTS\n\n## 1. Overview\n")
    assert capsys.readouterr().out == ""
    assert not (repo / "AGENTS.md").exists()


def test_generate_ignores_existing_agents_file_and_does_not_merge(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        "AGENTS.md",
        "# AGENTS\n\n## Team Notes\nKeep this manual section.\n",
    )

    exit_code = cli.main(["generate", str(repo)])

    assert exit_code == 0
    generated = capsys.readouterr().out
    assert generated.startswith("# AGENTS\n\n## 1. Overview\n")
    assert "Team Notes" not in generated


def test_generate_reports_invalid_repo_path(tmp_path, capsys):
    missing = tmp_path / "missing"
    exit_code = cli.main(["generate", str(missing)])

    assert exit_code == 1
    assert f"Generate failed for repo {missing}: path does not exist: {missing}" in (
        capsys.readouterr().err
    )


def test_generate_rejects_pretty_flag(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = cli.main(["--pretty", "generate", str(repo)])

    assert exit_code == 1
    assert capsys.readouterr().err == "generate does not support --pretty\n"
