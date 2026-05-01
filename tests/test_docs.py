from pathlib import Path


def test_api_reference_files_exist():
    reference_dir = Path("docs/reference")

    assert (reference_dir / "README.md").exists()
    assert (reference_dir / "cli.md").exists()
    assert (reference_dir / "commands.md").exists()
    assert (reference_dir / "library.md").exists()
    assert (reference_dir / "common.md").exists()


def test_documented_packaged_paths_exist():
    expected_paths = [
        Path("agentskill/main.py"),
        Path("agentskill/commands/scan.py"),
        Path("agentskill/commands/measure.py"),
        Path("agentskill/commands/config.py"),
        Path("agentskill/commands/git.py"),
        Path("agentskill/commands/graph.py"),
        Path("agentskill/commands/symbols.py"),
        Path("agentskill/commands/tests.py"),
        Path("agentskill/lib/runner.py"),
        Path("agentskill/lib/output.py"),
        Path("agentskill/lib/output_schema.py"),
        Path("agentskill/lib/generate_runner.py"),
        Path("agentskill/lib/update_runner.py"),
        Path("agentskill/lib/update_merge.py"),
        Path("agentskill/lib/update_feedback.py"),
        Path("agentskill/lib/reference_flow.py"),
        Path("agentskill/lib/reference_initialization.py"),
        Path("agentskill/lib/reference_adaptation.py"),
        Path("agentskill/lib/reference_questions.py"),
        Path("agentskill/lib/references.py"),
        Path("agentskill/lib/interactive_runner.py"),
        Path("agentskill/lib/cli_entrypoint.py"),
        Path("agentskill/lib/logging_utils.py"),
        Path("agentskill/lib/parsers.py"),
        Path("agentskill/lib/agents_document.py"),
        Path("agentskill/common/languages.py"),
        Path("agentskill/common/fs.py"),
        Path("agentskill/common/walk.py"),
        Path("agentskill/common/constants.py"),
    ]

    for path in expected_paths:
        assert path.exists(), f"documented path missing: {path}"
