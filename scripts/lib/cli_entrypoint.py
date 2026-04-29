"""Shared CLI entrypoint helper for analyzer command modules."""

import argparse

from lib.output import run_and_output


def run_command_main(
    *,
    argv: list[str] | None,
    description: str | None,
    command_fn,
    script_name: str,
    supports_lang: bool = False,
) -> int:
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("repo", help="Path to repository")

    if supports_lang:
        parser.add_argument("--lang", help="Filter to a single language")

    parser.add_argument("--pretty", action="store_true", help="Pretty-print output")

    args = parser.parse_args(argv)
    extra_kwargs = None

    if supports_lang:
        extra_kwargs = {"lang_filter": args.lang}

    return run_and_output(
        command_fn,
        repo=args.repo,
        pretty=args.pretty,
        script_name=script_name,
        extra_kwargs=extra_kwargs,
    )
