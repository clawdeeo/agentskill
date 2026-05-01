import builtins
from pathlib import Path

from test_support import (
    commit_all,
    create_repo,
    create_sample_repo,
    init_git_repo,
    write,
)

from agentskill.main import main


def test_generate_prints_markdown_to_stdout_without_writing_repo_file(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = main(["generate", str(repo)])

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

    exit_code = main(["generate", str(repo), "--out", str(out_path)])

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

    exit_code = main(["generate", str(repo)])

    assert exit_code == 0
    generated = capsys.readouterr().out
    assert generated.startswith("# AGENTS\n\n## 1. Overview\n")
    assert "Team Notes" not in generated


def test_generate_includes_reference_metadata_block(tmp_path, capsys):
    repo = create_sample_repo(tmp_path / "target")
    reference = create_repo(tmp_path, name="reference")
    write(reference, "AGENTS.md", "# AGENTS\n\n## 12. Testing\nUse pytest.\n")

    exit_code = main(["generate", str(repo), "--reference", str(reference)])

    assert exit_code == 0
    generated = capsys.readouterr().out
    assert generated.startswith("# AGENTS\n\n<!-- agentskill-metadata\n")
    assert f'"value": "{reference}"' in generated
    assert "## 1. Overview\n" in generated


def test_generate_multiple_references_preserve_cli_order(tmp_path, capsys):
    repo = create_sample_repo(tmp_path / "target")
    reference_a = create_repo(tmp_path, name="reference-a")
    reference_b = create_repo(tmp_path, name="reference-b")
    write(reference_a, "AGENTS.md", "# AGENTS\n\n## 12. Testing\nUse pytest.\n")
    write(reference_b, "AGENTS.md", "# AGENTS\n\n## 6. Code Formatting\nUse ruff.\n")

    exit_code = main(
        [
            "generate",
            str(repo),
            "--reference",
            str(reference_a),
            "--reference",
            str(reference_b),
        ]
    )

    assert exit_code == 0
    generated = capsys.readouterr().out
    index_a = generated.index(f'"value": "{reference_a}"')
    index_b = generated.index(f'"value": "{reference_b}"')
    assert index_a < index_b


def test_generate_interactive_adds_answered_gap_notes(tmp_path, capsys, monkeypatch):
    repo = create_repo(tmp_path)
    prompts: list[str] = []
    answers = iter(["pytest -q", "feat:, fix:", "rebase"])

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr(builtins, "input", fake_input)

    exit_code = main(["generate", str(repo), "--interactive"])

    assert exit_code == 0
    generated = capsys.readouterr().out
    assert len(prompts) == 3
    assert "Use `pytest -q` as the canonical test command." in generated
    assert "Preferred commit prefixes: `feat:, fix:`." in generated
    assert "Preferred merge strategy: `rebase`." in generated


def test_generate_interactive_skip_answers_keeps_default_sections(
    tmp_path, capsys, monkeypatch
):
    repo = create_repo(tmp_path)
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return ""

    monkeypatch.setattr(builtins, "input", fake_input)
    exit_code = main(["generate", str(repo), "--interactive"])

    assert exit_code == 0
    generated = capsys.readouterr().out
    assert len(prompts) == 3
    assert "Interactive answers:\n" not in generated


def test_generate_interactive_no_gaps_does_not_prompt(tmp_path, capsys, monkeypatch):
    repo = create_sample_repo(tmp_path)
    init_git_repo(repo)
    commit_all(repo, "feat: initial")

    def fail_input(prompt: str) -> str:
        raise AssertionError(f"unexpected prompt: {prompt}")

    monkeypatch.setattr(builtins, "input", fail_input)
    exit_code = main(["generate", str(repo), "--interactive"])

    assert exit_code == 0
    generated = capsys.readouterr().out
    assert "Interactive answers:\n" not in generated


def test_generate_interactive_references_reduce_prompt_count(
    tmp_path, capsys, monkeypatch
):
    repo = create_repo(tmp_path / "target")
    reference = create_repo(tmp_path, name="reference")

    write(
        reference,
        "AGENTS.md",
        (
            "# AGENTS\n\n"
            "## 12. Testing\n"
            "- Run command: `pytest`\n\n"
            "## 13. Git\n"
            "- Commit prefixes observed: `feat:, fix:`.\n"
        ),
    )

    prompts: list[str] = []
    answers = iter(["rebase"])

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr(builtins, "input", fake_input)

    exit_code = main(
        ["generate", str(repo), "--interactive", "--reference", str(reference)]
    )

    assert exit_code == 0
    generated = capsys.readouterr().out
    assert len(prompts) == 1
    assert "canonical test command" not in prompts[0].lower()
    assert "Use `pytest` as the canonical test command." in generated
    assert "Preferred commit prefixes: `feat:, fix:`." in generated
    assert "Preferred merge strategy: `rebase`." in generated


def test_generate_interactive_conflicting_references_prompt_for_ambiguous_gap(
    tmp_path, capsys, monkeypatch
):
    repo = create_repo(tmp_path / "target")
    reference_a = create_repo(tmp_path, name="reference-a")
    reference_b = create_repo(tmp_path, name="reference-b")

    write(
        reference_a,
        "AGENTS.md",
        "# AGENTS\n\n## 12. Testing\n- Run command: `pytest`\n",
    )

    write(
        reference_b,
        "AGENTS.md",
        "# AGENTS\n\n## 12. Testing\n- Run command: `python -m pytest`\n",
    )

    prompts: list[str] = []
    answers = iter(["pytest -q", "feat:, fix:", "rebase"])

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr(builtins, "input", fake_input)

    exit_code = main(
        [
            "generate",
            str(repo),
            "--interactive",
            "--reference",
            str(reference_a),
            "--reference",
            str(reference_b),
        ]
    )

    assert exit_code == 0
    generated = capsys.readouterr().out
    assert len(prompts) == 3
    assert "canonical test command" in prompts[0].lower()
    assert "Use `pytest -q` as the canonical test command." in generated


def test_generate_reports_invalid_repo_path(tmp_path, capsys):
    missing = tmp_path / "missing"
    exit_code = main(["generate", str(missing)])

    assert exit_code == 1
    assert f"Generate failed for repo {missing}: path does not exist: {missing}" in (
        capsys.readouterr().err
    )


def test_generate_reports_invalid_reference_path(tmp_path, capsys):
    repo = create_sample_repo(tmp_path / "target")
    missing = tmp_path / "missing-reference"

    exit_code = main(["generate", str(repo), "--reference", str(missing)])

    assert exit_code == 1
    assert (
        f"Generate failed for repo {repo}: reference path does not exist: {missing}"
    ) in capsys.readouterr().err


def test_generate_reports_missing_agents_file_in_reference_repo(tmp_path, capsys):
    repo = create_sample_repo(tmp_path / "target")
    reference = create_repo(tmp_path, name="reference")

    exit_code = main(["generate", str(repo), "--reference", str(reference)])

    assert exit_code == 1
    assert (
        f"Generate failed for repo {repo}: "
        f"AGENTS.md not found in reference repository: {reference}"
    ) in capsys.readouterr().err


def test_generate_rejects_duplicate_reference_sources(tmp_path, capsys):
    repo = create_sample_repo(tmp_path / "target")
    reference = create_repo(tmp_path, name="reference")
    write(reference, "AGENTS.md", "# AGENTS\n\n## 12. Testing\nUse pytest.\n")

    exit_code = main(
        [
            "generate",
            str(repo),
            "--reference",
            str(reference),
            "--reference",
            str(reference),
        ]
    )

    assert exit_code == 1
    assert (
        f"Generate failed for repo {repo}: duplicate reference source: {reference}"
    ) in capsys.readouterr().err


def test_generate_reference_output_is_stable_across_repeated_runs(tmp_path, capsys):
    repo = create_sample_repo(tmp_path / "target")
    reference = create_repo(tmp_path, name="reference")
    write(reference, "AGENTS.md", "# AGENTS\n\n## 12. Testing\nUse pytest.\n")

    exit_code = main(["generate", str(repo), "--reference", str(reference)])
    assert exit_code == 0
    first = capsys.readouterr()

    exit_code = main(["generate", str(repo), "--reference", str(reference)])
    assert exit_code == 0
    second = capsys.readouterr()

    assert first.err == ""
    assert second.err == ""
    assert first.out == second.out


def test_generate_rejects_pretty_flag(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = main(["--pretty", "generate", str(repo)])

    assert exit_code == 1
    assert capsys.readouterr().err == "generate does not support --pretty\n"
