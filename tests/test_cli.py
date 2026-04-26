import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from test_support import create_sample_repo

import cli


def test_cli_scan_outputs_json(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = cli.main(["scan", str(repo), "--pretty"])

    assert exit_code == 0

    output = json.loads(capsys.readouterr().out)
    assert output["summary"]["total_files"] >= 4


def test_cli_analyze_runs_all_commands(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = cli.main(["analyze", str(repo), "--pretty"])

    assert exit_code == 0

    output = json.loads(capsys.readouterr().out)

    assert set(output) == {
        "scan",
        "measure",
        "config",
        "git",
        "graph",
        "symbols",
        "tests",
    }


def test_cli_writes_out_file_and_multi_repo_results(tmp_path):
    repo_one = create_sample_repo(tmp_path / "one")
    repo_two = create_sample_repo(tmp_path / "two")
    out_file = tmp_path / "report.json"

    exit_code = cli.main(
        ["analyze", str(repo_one), str(repo_two), "--out", str(out_file)]
    )

    assert exit_code == 0

    payload = json.loads(out_file.read_text())
    assert set(payload) == {str(repo_one), str(repo_two)}


def test_pyproject_includes_cli_module_for_console_script():
    with Path("pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    assert data["tool"]["setuptools"]["py-modules"] == ["cli"]
