import time

from lib import runner
from lib.logging_utils import get_logger
from lib.runner import (
    ANALYZER_TIMEOUT_SECONDS,
    COMMANDS,
    POLL_INTERVAL_SECONDS,
    _command_kwargs,
    run_all,
    run_many,
)
from test_support import create_sample_repo


def test_runner_registry_matches_expected_commands():
    assert set(COMMANDS) == {
        "scan",
        "measure",
        "config",
        "git",
        "graph",
        "symbols",
        "tests",
    }


def test_run_all_returns_all_command_results(tmp_path):
    repo = create_sample_repo(tmp_path)
    result = run_all(str(repo))

    assert set(result) == set(COMMANDS)
    assert result["scan"]["summary"]["total_files"] >= 4


def test_runner_supports_lang_and_multi_repo(tmp_path):
    repo_one = create_sample_repo(tmp_path / "one")
    repo_two = create_sample_repo(tmp_path / "two")

    assert _command_kwargs("scan", "python") == {"lang_filter": "python"}
    assert _command_kwargs("config", "python") == {}

    result = run_many([str(repo_one), str(repo_two)], "python")
    assert set(result) == {str(repo_one), str(repo_two)}
    assert "python" in result[str(repo_one)]["measure"]


def test_runner_captures_command_exceptions(monkeypatch, caplog):
    original = runner.COMMANDS["scan"]["fn"]
    logger = get_logger()
    original_propagate = logger.propagate

    monkeypatch.setitem(
        runner.COMMANDS["scan"],
        "fn",
        lambda repo, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    logger.propagate = True

    try:
        with caplog.at_level("ERROR", logger="agentskill"):
            result = run_all("repo")
    finally:
        logger.propagate = original_propagate

    assert result["scan"] == {"error": "boom", "script": "scan"}
    assert "Analyzer scan failed for repo repo" in caplog.text
    assert "Traceback" in caplog.text
    monkeypatch.setitem(runner.COMMANDS["scan"], "fn", original)


def test_runner_times_out_slow_commands(monkeypatch, caplog):
    monkeypatch.setattr(runner, "ANALYZER_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(runner, "POLL_INTERVAL_SECONDS", 0.01)
    original = runner.COMMANDS["scan"]["fn"]
    logger = get_logger()
    original_propagate = logger.propagate

    def slow_command(repo, **kwargs):
        time.sleep(0.2)
        return {"ok": True}

    monkeypatch.setitem(runner.COMMANDS["scan"], "fn", slow_command)
    logger.propagate = True

    try:
        with caplog.at_level("WARNING", logger="agentskill"):
            result = run_all("repo")
    finally:
        logger.propagate = original_propagate

    assert result["scan"] == {
        "error": (f"analyzer timed out after {runner.ANALYZER_TIMEOUT_SECONDS}s"),
        "script": "scan",
    }

    assert "Analyzer scan timed out after 0.05s for repo repo" in caplog.text

    monkeypatch.setitem(runner.COMMANDS["scan"], "fn", original)


def test_runner_handles_mixed_success_exception_and_timeout(monkeypatch, caplog):
    monkeypatch.setattr(runner, "ANALYZER_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(runner, "POLL_INTERVAL_SECONDS", 0.01)

    originals = {name: metadata["fn"] for name, metadata in runner.COMMANDS.items()}
    logger = get_logger()
    original_propagate = logger.propagate

    monkeypatch.setitem(
        runner.COMMANDS,
        "scan",
        {"fn": lambda repo, **kwargs: {"ok": "scan"}, "supports_lang": True},
    )

    monkeypatch.setitem(
        runner.COMMANDS,
        "measure",
        {
            "fn": lambda repo, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
            "supports_lang": True,
        },
    )

    def slow_command(repo, **kwargs):
        time.sleep(0.2)
        return {"ok": "config"}

    monkeypatch.setitem(
        runner.COMMANDS,
        "config",
        {"fn": slow_command, "supports_lang": False},
    )

    for name in ["git", "graph", "symbols", "tests"]:
        monkeypatch.setitem(
            runner.COMMANDS,
            name,
            {
                "fn": lambda repo, name=name, **kwargs: {"ok": name},
                "supports_lang": False,
            },
        )

    logger.propagate = True

    try:
        with caplog.at_level("WARNING", logger="agentskill"):
            result = run_all("repo", "python")
    finally:
        logger.propagate = original_propagate

    assert result["scan"] == {"ok": "scan"}
    assert result["measure"] == {"error": "boom", "script": "measure"}

    assert result["config"] == {
        "error": (f"analyzer timed out after {runner.ANALYZER_TIMEOUT_SECONDS}s"),
        "script": "config",
    }

    assert set(result) == set(runner.COMMANDS)
    assert caplog.text.count("Analyzer measure failed for repo repo") == 1
    assert caplog.text.count("Analyzer config timed out after 0.05s for repo repo") == 1
    assert "Traceback" in caplog.text

    for name, fn in originals.items():
        monkeypatch.setitem(runner.COMMANDS[name], "fn", fn)


def test_runner_module_constants_are_stable():
    assert ANALYZER_TIMEOUT_SECONDS == 60
    assert POLL_INTERVAL_SECONDS == 0.1
