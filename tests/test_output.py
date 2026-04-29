import json
import logging
from pathlib import Path

from lib.logging_utils import LOGGER_NAME, configure_logging, get_logger
from lib.output import run_and_output, validate_out_path, write_output
from lib.output_schema import OutputSchemaError


def test_write_output_prints_and_writes_file(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_output({"ok": True}, pretty=False)
    assert json.loads(capsys.readouterr().out) == {"ok": True}

    out_file = Path("report.json")
    write_output({"ok": True}, pretty=True, out=str(out_file))

    assert json.loads(out_file.read_text()) == {"ok": True}


def test_validate_out_path_accepts_safe_relative_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert validate_out_path("report.json") == tmp_path / "report.json"
    assert validate_out_path("reports/output.json") == tmp_path / "reports/output.json"


def test_validate_out_path_rejects_absolute_and_escaping_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    absolute = str(tmp_path / "report.json")

    try:
        validate_out_path(absolute)
        raise AssertionError("absolute paths should be rejected")
    except ValueError as exc:
        assert str(exc) == (
            f"invalid output path: absolute paths are not allowed: {absolute}"
        )

    for out in ["../output.json", "nested/../../escape.json"]:
        try:
            validate_out_path(out)
            raise AssertionError("escaping paths should be rejected")
        except ValueError as exc:
            assert str(exc) == (
                "invalid output path: escaping the working directory is not allowed: "
                f"{out}"
            )


def test_write_output_creates_parent_directories_and_rejects_invalid_paths(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    nested = Path("reports/latest/output.json")
    write_output({"ok": True}, out=str(nested))

    assert json.loads(nested.read_text()) == {"ok": True}

    absolute = str(tmp_path / "escape.json")

    try:
        write_output({"ok": True}, out=absolute)
        raise AssertionError("absolute output paths should be rejected")
    except ValueError as exc:
        assert str(exc) == (
            f"invalid output path: absolute paths are not allowed: {absolute}"
        )


def test_logging_configuration_is_stable():
    logger = get_logger()
    original_handlers = list(logger.handlers)
    original_level = logger.level
    original_propagate = logger.propagate

    try:
        logger.handlers.clear()

        configured = configure_logging()
        handler_count = len(configured.handlers)

        assert configured is logging.getLogger(LOGGER_NAME)
        assert configured.level == logging.WARNING
        assert configured.propagate is False

        configured = configure_logging()

        assert len(configured.handlers) == handler_count
    finally:
        logger.handlers.clear()
        logger.handlers.extend(original_handlers)
        logger.setLevel(original_level)
        logger.propagate = original_propagate


def test_run_and_output_handles_success_and_exceptions(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def ok(repo: str, *, value: int):
        return {"repo": repo, "value": value}

    exit_code = run_and_output(
        ok,
        repo="sample",
        pretty=False,
        script_name="demo",
        extra_kwargs={"value": 3},
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"repo": "sample", "value": 3}

    out_file = Path("error.json")

    def boom(repo: str):
        raise RuntimeError("kaboom")

    exit_code = run_and_output(
        boom,
        repo="sample",
        pretty=True,
        out=str(out_file),
        script_name="demo",
    )

    assert exit_code == 1

    assert json.loads(out_file.read_text()) == {"error": "kaboom", "script": "demo"}


def test_run_and_output_logs_exceptions_to_stderr_without_polluting_stdout(capsys):
    def boom(repo: str):
        raise RuntimeError("kaboom")

    exit_code = run_and_output(
        boom,
        repo="sample",
        pretty=False,
        script_name="demo",
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert json.loads(captured.out) == {"error": "kaboom", "script": "demo"}
    assert "ERROR agentskill: Command demo failed for repo sample" in captured.err
    assert "Traceback" in captured.err


def test_run_and_output_raises_on_invalid_output_shape():
    def bad(repo: str):
        return {"error": "kaboom"}

    try:
        run_and_output(
            bad,
            repo="sample",
            pretty=False,
            script_name="demo",
        )
        raise AssertionError("invalid output shape should raise OutputSchemaError")
    except OutputSchemaError as exc:
        assert "exactly 'error' and 'script'" in str(exc)
