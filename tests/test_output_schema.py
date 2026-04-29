import json

from lib.output import write_output
from lib.output_schema import (
    OutputSchemaError,
    validate_analyze_output,
    validate_analyzer_output,
    validate_error_payload,
)


def _assert_raises_schema_error(fn, message: str) -> None:
    try:
        fn()
        raise AssertionError("expected OutputSchemaError")
    except OutputSchemaError as exc:
        assert message in str(exc)


def test_output_schema_accepts_valid_error_payload():
    validate_error_payload({"error": "path does not exist: /tmp/x", "script": "scan"})


def test_output_schema_rejects_invalid_error_payloads():
    cases = [
        ({}, "exactly 'error' and 'script'"),
        ({"error": 1, "script": "scan"}, "field 'error' must be a string"),
        (["bad"], "error payload must be a dict"),
    ]

    for payload, message in cases:
        _assert_raises_schema_error(
            lambda payload=payload: validate_error_payload(payload), message
        )


def test_output_schema_accepts_valid_single_analyzer_output():
    validate_analyzer_output(
        {
            "summary": {"total_files": 1, "by_language": {"python": {"file_count": 1}}},
            "read_order": ["pkg/main.py"],
        }
    )


def test_output_schema_accepts_valid_analyze_outputs():
    single_repo = {
        "scan": {"summary": {"total_files": 1}},
        "measure": {"python": {}},
        "config": {"python": {}},
        "git": {"error": "git log failed", "script": "git"},
        "graph": {"python": {"edges": []}},
        "symbols": {"python": {"functions": {"total": 0}}},
        "tests": {"python": {"framework": "pytest"}},
    }

    multi_repo = {
        "repo-one": single_repo,
        "repo-two": {
            "scan": {"summary": {"total_files": 2}},
            "measure": {"python": {}},
            "config": {"python": {}},
            "git": {"error": "empty repository", "script": "git"},
            "graph": {"python": {"edges": []}},
            "symbols": {"python": {"functions": {"total": 0}}},
            "tests": {"python": {"framework": "pytest"}},
        },
    }

    validate_analyze_output(single_repo)
    validate_analyze_output(multi_repo)


def test_output_schema_rejects_invalid_analyze_outputs():
    cases = [
        ([], "analyze output must be a dict"),
        ({"scan": []}, "analyze output must contain exactly the analyzer keys"),
        (
            {
                "repo": {
                    "scan": {"summary": {}},
                    "measure": {"python": {}},
                    "config": {"python": {}},
                    "git": {"error": "bad"},
                    "graph": {"python": {"edges": []}},
                    "symbols": {"python": {"functions": {"total": 0}}},
                    "tests": {"python": {"framework": "pytest"}},
                }
            },
            "exactly 'error' and 'script'",
        ),
    ]

    for payload, message in cases:
        _assert_raises_schema_error(
            lambda payload=payload: validate_analyze_output(payload),
            message,
        )


def test_output_schema_integration_preserves_valid_serialization(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    payload = {"error": "path does not exist: repo", "script": "scan"}

    write_output(payload, pretty=False, schema_mode="single")
    assert json.loads(capsys.readouterr().out) == payload


def test_output_schema_integration_rejects_malformed_output():
    _assert_raises_schema_error(
        lambda: write_output({"error": "boom"}, schema_mode="single"),
        "exactly 'error' and 'script'",
    )
