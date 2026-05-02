from test_support import create_sample_repo, write

from agentskill.main import main


def test_update_succeeds_without_feedback_file(tmp_path):
    repo = create_sample_repo(tmp_path)
    exit_code = main(["update", str(repo)])

    assert exit_code == 0
    assert (repo / "AGENTS.md").exists()


def test_feedback_biases_targeted_regeneration(tmp_path):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        ".agentskill-feedback.json",
        (
            "{\n"
            '  "sections": {\n'
            '    "overview": {\n'
            '      "prepend_notes": ["Mention that deployments go through GitHub Actions."],\n'
            '      "pinned_facts": ["Use pytest as the canonical test runner."]\n'
            "    }\n"
            "  }\n"
            "}\n"
        ),
    )

    exit_code = main(["update", str(repo), "--section", "overview"])
    assert exit_code == 0

    agents_text = (repo / "AGENTS.md").read_text()
    assert "Mention that deployments go through GitHub Actions." in agents_text
    assert "Use pytest as the canonical test runner." in agents_text


def test_feedback_preserve_sections_prevents_normal_regeneration(tmp_path):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        ".agentskill-feedback.json",
        '{\n  "preserve_sections": ["testing"]\n}\n',
    )

    write(
        repo,
        "AGENTS.md",
        (
            "# AGENTS\n\n"
            "## 1. Overview\n"
            "Old overview.\n"
            "## 12. Testing\n"
            "Keep this testing guidance exactly.\n"
        ),
    )

    exit_code = main(["update", str(repo)])
    assert exit_code == 0

    agents_text = (repo / "AGENTS.md").read_text()
    assert "Keep this testing guidance exactly.\n" in agents_text
    assert "Old overview.\n" not in agents_text


def test_feedback_preserve_sections_are_ignored_in_force_mode(tmp_path):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        ".agentskill-feedback.json",
        '{\n  "preserve_sections": ["testing"]\n}\n',
    )

    write(
        repo,
        "AGENTS.md",
        ("# AGENTS\n\n## 12. Testing\nKeep this testing guidance exactly.\n"),
    )

    exit_code = main(["update", str(repo), "--force"])
    assert exit_code == 0

    agents_text = (repo / "AGENTS.md").read_text()
    assert "Keep this testing guidance exactly.\n" not in agents_text
    assert "## 12. Testing\n" in agents_text


def test_malformed_feedback_fails_clearly(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    write(
        repo,
        ".agentskill-feedback.json",
        '{\n  "sections": {\n    "overview": {"unknown": ["bad"]}\n  }\n}\n',
    )

    exit_code = main(["update", str(repo)])

    assert exit_code == 1
    assert "unsupported feedback keys for section overview: unknown" in (
        capsys.readouterr().err
    )


def test_update_enriches_error_handling_with_static_source_snippets(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    write(
        repo,
        "pkg/validate.py",
        (
            "from pathlib import Path\n\n\n"
            "def validate_repo(path: str) -> Path:\n"
            "    repo = Path(path).resolve()\n\n"
            "    if not repo.exists():\n"
            '        raise ValueError(f"path does not exist: {path}")\n\n'
            "    return repo\n"
        ),
    )

    write(
        repo,
        "pkg/scan.py",
        (
            "from pkg.validate import validate_repo\n\n\n"
            "def scan(repo_path: str) -> dict:\n"
            "    try:\n"
            "        repo = validate_repo(repo_path)\n"
            "    except ValueError as exc:\n"
            '        return {"error": str(exc), "script": "scan"}\n\n'
            '    return {"repo": str(repo)}\n'
        ),
    )

    write(
        repo,
        "pkg/output.py",
        (
            "import logging\n\n"
            "logger = logging.getLogger(__name__)\n\n\n"
            "def run_and_output(command_fn, repo: str, script_name: str) -> int:\n"
            "    try:\n"
            "        result = command_fn(repo)\n"
            "    except Exception as exc:\n"
            '        logger.exception("Command %s failed for repo %s", script_name, repo)\n'
            '        result = {"error": str(exc), "script": script_name}\n\n'
            '    return 1 if "error" in result else 0\n'
        ),
    )

    write(
        repo,
        "pkg/fs.py",
        (
            "from pathlib import Path\n\n\n"
            "def read_text(path: Path) -> str:\n"
            "    try:\n"
            '        return path.read_text(encoding="utf-8")\n'
            "    except Exception:\n"
            '        return ""\n'
        ),
    )

    exit_code = main(["update", str(repo), "--section", "error handling"])

    assert exit_code == 0

    agents_text = (repo / "AGENTS.md").read_text()
    assert "Low-level validators raise `ValueError`" in agents_text
    assert 'raise ValueError(f"path does not exist: {path}")' in agents_text
    assert '`{"error": ..., "script": ...}` payloads' in agents_text
    assert 'return {"error": str(exc), "script": "scan"}' in agents_text
    assert "logger.exception" in agents_text
    assert 'return ""' in agents_text
