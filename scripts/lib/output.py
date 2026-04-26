"""Shared JSON output helpers for CLI and command entrypoints."""

import json
from pathlib import Path

from lib.logging_utils import configure_logging


def write_output(data: dict, pretty: bool = False, out: str | None = None) -> None:
    configure_logging()
    indent = 2 if pretty else None
    text = json.dumps(data, indent=indent)

    if out:
        Path(out).write_text(text + "\n")
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

    write_output(result, pretty=pretty, out=out)

    return 1 if "error" in result else 0
