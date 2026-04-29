"""Lightweight validation helpers for public JSON output contracts."""

import json
from dataclasses import dataclass

ANALYZER_NAMES = (
    "scan",
    "measure",
    "config",
    "git",
    "graph",
    "symbols",
    "tests",
)


class OutputSchemaError(ValueError):
    """Raised when a public output payload violates the JSON contract."""


@dataclass(frozen=True)
class ErrorPayload:
    error: str
    script: str


def is_error_payload(data: object) -> bool:
    return (
        isinstance(data, dict)
        and set(data) == {"error", "script"}
        and isinstance(data.get("error"), str)
        and isinstance(data.get("script"), str)
    )


def _ensure_jsonable(data: object, *, context: str) -> None:
    try:
        json.dumps(data)
    except TypeError as exc:
        raise OutputSchemaError(f"{context} is not JSON-serializable") from exc


def validate_error_payload(data: object) -> None:
    if not isinstance(data, dict):
        raise OutputSchemaError("error payload must be a dict")

    if set(data) != {"error", "script"}:
        raise OutputSchemaError(
            "error payload must contain exactly 'error' and 'script'"
        )

    if not isinstance(data["error"], str):
        raise OutputSchemaError("error payload field 'error' must be a string")

    if not isinstance(data["script"], str):
        raise OutputSchemaError("error payload field 'script' must be a string")

    _ensure_jsonable(data, context="error payload")


def validate_analyzer_output(data: object, *, allow_error: bool = True) -> None:
    if not isinstance(data, dict):
        raise OutputSchemaError("analyzer output must be a dict")

    if "error" in data:
        if not allow_error:
            raise OutputSchemaError("unexpected error payload in analyzer output")

        validate_error_payload(data)
        return

    _ensure_jsonable(data, context="analyzer output")


def validate_analyze_repo_output(data: object) -> None:
    if not isinstance(data, dict):
        raise OutputSchemaError("analyze output for a repo must be a dict")

    keys = set(data)

    if keys != set(ANALYZER_NAMES):
        raise OutputSchemaError("analyze output must contain exactly the analyzer keys")

    for _analyzer_name, payload in data.items():
        validate_analyzer_output(payload)


def validate_analyze_output(data: object) -> None:
    if not isinstance(data, dict):
        raise OutputSchemaError("analyze output must be a dict")

    if not data:
        raise OutputSchemaError("analyze output must not be empty")

    keys = set(data)

    analyzer_keys = set(ANALYZER_NAMES)

    if keys.issubset(analyzer_keys):
        validate_analyze_repo_output(data)
        return

    for repo_path, repo_payload in data.items():
        if not isinstance(repo_path, str):
            raise OutputSchemaError("analyze output repo keys must be strings")

        validate_analyze_repo_output(repo_payload)


def validate_generation_output(data: object) -> None:
    if not isinstance(data, dict):
        raise OutputSchemaError("generation output must be a dict")

    _ensure_jsonable(data, context="generation output")


def validate_public_output(data: object, *, mode: str) -> None:
    if mode == "single":
        validate_analyzer_output(data)
        return

    if mode == "analyze":
        validate_analyze_output(data)
        return

    if mode == "generation":
        validate_generation_output(data)
        return

    raise OutputSchemaError(f"unknown output validation mode: {mode}")
