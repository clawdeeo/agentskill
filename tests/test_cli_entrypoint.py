import subprocess
import sys

from lib import cli_entrypoint
from test_support import ROOT, create_sample_repo


def test_run_command_main_passes_lang_filter_and_pretty(monkeypatch):
    captured = {}

    def fake_run_and_output(
        command_fn,
        *,
        repo: str,
        pretty: bool = False,
        out: str | None = None,
        script_name: str,
        extra_kwargs: dict | None = None,
    ) -> int:
        captured["command_fn"] = command_fn
        captured["repo"] = repo
        captured["pretty"] = pretty
        captured["out"] = out
        captured["script_name"] = script_name
        captured["extra_kwargs"] = extra_kwargs
        return 7

    monkeypatch.setattr(cli_entrypoint, "run_and_output", fake_run_and_output)
    command_fn = object()

    exit_code = cli_entrypoint.run_command_main(
        argv=["sample-repo", "--lang", "python", "--pretty"],
        description="demo",
        command_fn=command_fn,
        script_name="scan",
        supports_lang=True,
    )

    assert exit_code == 7
    assert captured == {
        "command_fn": command_fn,
        "repo": "sample-repo",
        "pretty": True,
        "out": None,
        "script_name": "scan",
        "extra_kwargs": {"lang_filter": "python"},
    }


def test_run_command_main_rejects_lang_when_command_does_not_support_it(capsys):
    try:
        cli_entrypoint.run_command_main(
            argv=["sample-repo", "--lang", "python"],
            description="demo",
            command_fn=object(),
            script_name="config",
        )
        raise AssertionError(
            "--lang should be rejected for non-language-aware commands"
        )
    except SystemExit as exc:
        assert exc.code == 2

    assert "unrecognized arguments: --lang python" in capsys.readouterr().err


def test_measure_wrapper_still_executes_directly(tmp_path):
    repo = create_sample_repo(tmp_path)

    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "measure.py"), str(repo), "--pretty"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert '"python"' in completed.stdout
