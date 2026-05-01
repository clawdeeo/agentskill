import json

from test_support import (
    commit_all,
    create_repo,
    create_sample_repo,
    init_git_repo,
    write,
)

from agentskill.main import main


def create_committed_sample_repo(tmp_path, name: str = "repo"):
    repo = create_sample_repo(tmp_path / name)
    init_git_repo(repo)
    commit_all(repo, "feat: initial")
    return repo


def test_cli_help_lists_public_commands(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        exit_code = exc.code
    else:
        raise AssertionError("expected SystemExit from --help")

    assert exit_code == 0
    help_text = capsys.readouterr().out

    for command in [
        "analyze",
        "scan",
        "measure",
        "config",
        "git",
        "graph",
        "symbols",
        "tests",
        "generate",
        "update",
    ]:
        assert command in help_text


def test_analyzer_commands_have_stable_successful_invocations(tmp_path, capsys):
    repo = create_committed_sample_repo(tmp_path)
    cases = [
        ("scan", ["--lang", "python"]),
        ("measure", ["--lang", "python"]),
        ("config", []),
        ("git", []),
        ("graph", ["--lang", "python"]),
        ("symbols", ["--lang", "python"]),
        ("tests", []),
    ]

    for command, extra_args in cases:
        exit_code = main([command, str(repo), *extra_args, "--pretty"])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        output = json.loads(captured.out)

        if command == "scan":
            assert output["summary"]["total_files"] >= 4
        elif command == "measure" or command == "config":
            assert "python" in output
        elif command == "git":
            assert "error" not in output
        elif command == "graph":
            assert isinstance(output, dict)
        elif command == "symbols":
            assert "python" in output
        elif command == "tests":
            assert output["python"]["framework"] == "pytest"


def test_analyze_success_writes_json_to_stdout_and_not_stderr(tmp_path, capsys):
    repo = create_committed_sample_repo(tmp_path)
    exit_code = main(["analyze", str(repo), "--pretty"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.err == ""

    output = json.loads(captured.out)
    assert set(output) == {
        "scan",
        "measure",
        "config",
        "git",
        "graph",
        "symbols",
        "tests",
    }


def test_analyze_out_writes_file_and_suppresses_stdout(tmp_path, monkeypatch, capsys):
    repo = create_committed_sample_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    exit_code = main(["analyze", str(repo), "--out", "report.json"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    payload = json.loads((tmp_path / "report.json").read_text())
    assert set(payload) == {
        "scan",
        "measure",
        "config",
        "git",
        "graph",
        "symbols",
        "tests",
    }


def test_analyze_reference_preserves_json_output_shape(tmp_path, capsys):
    repo = create_committed_sample_repo(tmp_path, name="target")
    reference = create_repo(tmp_path, name="reference")
    write(reference, "AGENTS.md", "# AGENTS\n\n## 12. Testing\nUse pytest.\n")
    exit_code = main(["analyze", str(repo), "--reference", str(reference), "--pretty"])

    assert exit_code == 0
    captured = capsys.readouterr()

    assert captured.err == ""
    assert set(json.loads(captured.out)) == {
        "scan",
        "measure",
        "config",
        "git",
        "graph",
        "symbols",
        "tests",
    }


def test_analyze_invalid_reference_fails_with_stderr_only(tmp_path, capsys):
    repo = create_committed_sample_repo(tmp_path, name="target")
    missing = tmp_path / "missing-reference"
    exit_code = main(["analyze", str(repo), "--reference", str(missing)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"reference path does not exist: {missing}\n"


def test_analyze_reference_missing_agents_file_fails_clearly(tmp_path, capsys):
    repo = create_committed_sample_repo(tmp_path, name="target")
    reference = create_repo(tmp_path, name="reference")
    exit_code = main(["analyze", str(repo), "--reference", str(reference)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"AGENTS.md not found in reference repository: {reference}\n"


def test_analyze_rejects_duplicate_reference_sources(tmp_path, capsys):
    repo = create_committed_sample_repo(tmp_path, name="target")
    reference = create_repo(tmp_path, name="reference")
    write(reference, "AGENTS.md", "# AGENTS\n\n## 12. Testing\nUse pytest.\n")

    exit_code = main(
        [
            "analyze",
            str(repo),
            "--reference",
            str(reference),
            "--reference",
            str(reference),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"duplicate reference source: {reference}\n"


def test_analyze_reference_order_does_not_change_json_output(tmp_path, capsys):
    repo = create_committed_sample_repo(tmp_path, name="target")
    reference_a = create_repo(tmp_path, name="reference-a")
    reference_b = create_repo(tmp_path, name="reference-b")
    write(reference_a, "AGENTS.md", "# AGENTS\n\n## 12. Testing\nUse pytest.\n")
    write(reference_b, "AGENTS.md", "# AGENTS\n\n## 13. Git\nUse rebase.\n")

    exit_code = main(
        [
            "analyze",
            str(repo),
            "--reference",
            str(reference_a),
            "--reference",
            str(reference_b),
            "--pretty",
        ]
    )

    assert exit_code == 0
    first = json.loads(capsys.readouterr().out)

    exit_code = main(
        [
            "analyze",
            str(repo),
            "--reference",
            str(reference_b),
            "--reference",
            str(reference_a),
            "--pretty",
        ]
    )

    assert exit_code == 0
    second = json.loads(capsys.readouterr().out)

    assert first == second


def test_generate_non_interactive_does_not_prompt(tmp_path, capsys, monkeypatch):
    repo = create_repo(tmp_path)

    def fail_input(prompt: str) -> str:
        raise AssertionError(f"unexpected prompt: {prompt}")

    monkeypatch.setattr("builtins.input", fail_input)
    exit_code = main(["generate", str(repo)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("# AGENTS\n\n## 1. Overview\n")
    assert captured.err == ""


def test_generate_out_writes_file_and_suppresses_stdout(tmp_path, monkeypatch, capsys):
    repo = create_sample_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    exit_code = main(["generate", str(repo), "--out", "generated/AGENTS.md"])

    assert exit_code == 0
    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ""

    assert (
        (tmp_path / "generated/AGENTS.md")
        .read_text()
        .startswith("# AGENTS\n\n## 1. Overview\n")
    )


def test_generate_interactive_is_opt_in_and_writes_to_stdout(
    tmp_path, capsys, monkeypatch
):
    repo = create_repo(tmp_path)
    prompts: list[str] = []
    answers = iter(["pytest -q", "feat:, fix:", "rebase"])

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", fake_input)
    exit_code = main(["generate", str(repo), "--interactive"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert len(prompts) == 3
    assert "Use `pytest -q` as the canonical test command." in captured.out


def test_generate_invalid_reference_fails_to_stderr_only(tmp_path, capsys):
    repo = create_sample_repo(tmp_path / "target")
    missing = tmp_path / "missing-reference"
    exit_code = main(["generate", str(repo), "--reference", str(missing)])

    assert exit_code == 1
    captured = capsys.readouterr()

    assert captured.out == ""
    assert (
        f"Generate failed for repo {repo}: reference path does not exist: {missing}\n"
        == captured.err
    )


def test_update_default_behavior_writes_repo_file_without_stdout(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = main(["update", str(repo)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (repo / "AGENTS.md").read_text().startswith("# AGENTS\n\n## 1. Overview\n")


def test_update_out_writes_custom_file_without_stdout(tmp_path, monkeypatch, capsys):
    repo = create_sample_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    exit_code = main(["update", str(repo), "--out", "generated/AGENTS-new.md"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (tmp_path / "generated/AGENTS-new.md").exists()
    assert not (repo / "AGENTS.md").exists()


def test_update_rejects_invalid_section_with_exit_code_one(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = main(["update", str(repo), "--section", "unknown-section"])

    assert exit_code == 1
    captured = capsys.readouterr()

    assert captured.out == ""
    assert (
        "Update failed for repo "
        f"{repo}: unsupported or unavailable sections: unknown-section\n"
        == captured.err
    )


def test_unsupported_flag_combinations_fail_via_argparse(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)

    try:
        main(["update", str(repo), "--reference", str(repo)])
    except SystemExit as exc:
        exit_code = exc.code
    else:
        raise AssertionError("expected SystemExit from invalid argparse usage")

    assert exit_code == 2
    assert "unrecognized arguments: --reference" in capsys.readouterr().err


def test_generate_and_update_preserve_distinct_public_semantics(tmp_path, capsys):
    generate_repo = create_sample_repo(tmp_path / "generate-case")
    update_repo = create_sample_repo(tmp_path / "update-case")

    manual_agents = "# AGENTS\n\n## Team Notes\nKeep this manual section.\n"
    write(generate_repo, "AGENTS.md", manual_agents)
    write(update_repo, "AGENTS.md", manual_agents)

    generate_exit_code = main(["generate", str(generate_repo)])

    assert generate_exit_code == 0
    generated = capsys.readouterr().out
    assert "## Team Notes\n" not in generated

    update_exit_code = main(["update", str(update_repo)])

    assert update_exit_code == 0
    updated_text = (update_repo / "AGENTS.md").read_text()
    assert "## Team Notes\nKeep this manual section.\n" in updated_text
