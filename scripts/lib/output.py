"""Shared JSON output helpers for CLI and command entrypoints."""

import json
from pathlib import Path

from lib.logging_utils import configure_logging
from lib.output_schema import validate_public_output


def validate_out_path(out: str) -> Path:
    raw_path = Path(out)

    if raw_path.is_absolute():
        raise ValueError(f"invalid output path: absolute paths are not allowed: {out}")

    base_dir = Path.cwd().resolve()
    resolved = (base_dir / raw_path).resolve()

    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError(
            f"invalid output path: escaping the working directory is not allowed: {out}"
        ) from exc

    return resolved


def write_output(
    data: dict,
    pretty: bool = False,
    out: str | None = None,
    schema_mode: str | None = None,
) -> None:
    configure_logging()

    if schema_mode:
        validate_public_output(data, mode=schema_mode)

    indent = 2 if pretty else None
    text = json.dumps(data, indent=indent)

    if out:
        output_path = validate_out_path(out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n")
        return

    print(text)


def run_and_output(
    command_fn,
    *,
    repo: str,
    pretty: bool = False,
    out: str | None = None,
    script_name: str,
    extra_kwargs: dict | None = None,
) -> int:
    logger = configure_logging()
    kwargs = extra_kwargs or {}

    try:
        result = command_fn(repo, **kwargs)
    except Exception as exc:
        logger.exception("Command %s failed for repo %s", script_name, repo)
        result = {"error": str(exc), "script": script_name}

    write_output(result, pretty=pretty, out=out, schema_mode="single")

    return 1 if "error" in result else 0
