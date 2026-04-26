#!/usr/bin/env python3
"""agentskill — analyze repositories and synthesize AGENTS.md.

Runs all analysis scripts and merges output into a single JSON report.

Usage:
    python cli.py analyze <repo> [<repo2> ...]
    python cli.py analyze <repo> --pretty
    python cli.py analyze <repo> --out report.json

    python cli.py scan <repo>
    python cli.py measure <repo> [--lang python]
    python cli.py config <repo>
    python cli.py git <repo>
    python cli.py graph <repo> [--lang python]
    python cli.py symbols <repo> [--lang python]
    python cli.py tests <repo>
"""

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "scripts"))

from lib.logging_utils import configure_logging
from lib.output import run_and_output, write_output
from lib.runner import COMMANDS, run_many


def cmd_analyze(args: argparse.Namespace) -> int:
    result = run_many(args.repos, getattr(args, "lang", None))
    write_output(result, args.pretty, getattr(args, "out", None))
    return 0


def _single_script_cmd(command_name: str, args: argparse.Namespace) -> int:
    metadata = COMMANDS[command_name]
    extra_kwargs = {}

    if metadata["supports_lang"]:
        extra_kwargs["lang_filter"] = getattr(args, "lang", None)

    return run_and_output(
        metadata["fn"],
        repo=args.repo,
        pretty=args.pretty,
        out=getattr(args, "out", None),
        script_name=command_name,
        extra_kwargs=extra_kwargs,
    )


def main(argv: list[str] | None = None) -> int:
    configure_logging()

    parser = argparse.ArgumentParser(
        prog="agentskill",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )

    parser.add_argument(
        "--out", metavar="FILE", help="Write output to file instead of stdout"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Run all scripts and merge output")

    p_analyze.add_argument(
        "repos", nargs="+", metavar="repo", help="Path(s) to repository"
    )

    p_analyze.add_argument(
        "--lang", help="Filter to a single language where applicable"
    )

    p_scan = sub.add_parser("scan", help="Directory tree + file inventory")
    p_scan.add_argument("repo", help="Path to repository")
    p_scan.add_argument("--lang", help="Filter to a single language")

    p_measure = sub.add_parser("measure", help="Exact formatting metrics")
    p_measure.add_argument("repo", help="Path to repository")
    p_measure.add_argument("--lang", help="Filter to a single language")

    p_config = sub.add_parser("config", help="Formatter/linter detection and config")
    p_config.add_argument("repo", help="Path to repository")

    p_git = sub.add_parser("git", help="Commit log and branch analysis")
    p_git.add_argument("repo", help="Path to repository")

    p_graph = sub.add_parser("graph", help="Internal import graph")
    p_graph.add_argument("repo", help="Path to repository")
    p_graph.add_argument("--lang", help="Filter to a single language")

    p_symbols = sub.add_parser(
        "symbols", help="Symbol name extraction and pattern clustering"
    )

    p_symbols.add_argument("repo", help="Path to repository")
    p_symbols.add_argument("--lang", help="Filter to a single language")

    p_tests = sub.add_parser(
        "tests", help="Test-to-source mapping and framework detection"
    )

    p_tests.add_argument("repo", help="Path to repository")

    for p in [
        p_scan,
        p_measure,
        p_config,
        p_git,
        p_graph,
        p_symbols,
        p_tests,
        p_analyze,
    ]:
        p.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
        p.add_argument("--out", metavar="FILE", help="Write output to file")

    args = parser.parse_args(argv)

    dispatch = {
        "analyze": cmd_analyze,
        "scan": lambda a: _single_script_cmd("scan", a),
        "measure": lambda a: _single_script_cmd("measure", a),
        "config": lambda a: _single_script_cmd("config", a),
        "git": lambda a: _single_script_cmd("git", a),
        "graph": lambda a: _single_script_cmd("graph", a),
        "symbols": lambda a: _single_script_cmd("symbols", a),
        "tests": lambda a: _single_script_cmd("tests", a),
    }

    handler = dispatch.get(args.command)

    if not handler:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
