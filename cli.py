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
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add scripts/ directory to path so scripts can be imported as modules
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "scripts"))

import scan as _scan
import measure as _measure
import config as _config
import git as _git
import graph as _graph
import symbols as _symbols
import tests as _tests


def _run_all(repo: str, lang: str | None = None) -> dict:
    """Run all 7 scripts in parallel and merge output."""
    tasks = {
        "scan":    lambda: _scan.scan(repo),
        "measure": lambda: _measure.measure(repo, lang),
        "config":  lambda: _config.detect(repo),
        "git":     lambda: _git.analyze(repo),
        "graph":   lambda: _graph.build_graph(repo, lang),
        "symbols": lambda: _symbols.extract_symbols(repo, lang),
        "tests":   lambda: _tests.analyze_tests(repo),
    }

    result: dict = {}
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                result[name] = future.result()
            except Exception as exc:
                result[name] = {"error": str(exc)}

    return result


def _output(data: dict, pretty: bool, out: str | None) -> None:
    indent = 2 if pretty else None
    text = json.dumps(data, indent=indent)
    if out:
        Path(out).write_text(text + "\n")
    else:
        print(text)


def cmd_analyze(args: argparse.Namespace) -> int:
    repos = args.repos
    if len(repos) == 1:
        result = _run_all(repos[0], getattr(args, "lang", None))
    else:
        result = {}
        for repo in repos:
            result[repo] = _run_all(repo, getattr(args, "lang", None))

    _output(result, args.pretty, getattr(args, "out", None))
    return 0


def _single_script_cmd(fn, args: argparse.Namespace, extra_kwargs: dict | None = None) -> int:
    kwargs = extra_kwargs or {}
    try:
        result = fn(args.repo, **kwargs)
    except Exception as exc:
        result = {"error": str(exc)}

    _output(result, args.pretty, getattr(args, "out", None))
    return 1 if "error" in result else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentskill",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--out", metavar="FILE", help="Write output to file instead of stdout")

    sub = parser.add_subparsers(dest="command", required=True)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Run all scripts and merge output")
    p_analyze.add_argument("repos", nargs="+", metavar="repo", help="Path(s) to repository")
    p_analyze.add_argument("--lang", help="Filter to a single language where applicable")

    # scan
    p_scan = sub.add_parser("scan", help="Directory tree + file inventory")
    p_scan.add_argument("repo", help="Path to repository")
    p_scan.add_argument("--lang", help="Filter to a single language")

    # measure
    p_measure = sub.add_parser("measure", help="Exact formatting metrics")
    p_measure.add_argument("repo", help="Path to repository")
    p_measure.add_argument("--lang", help="Filter to a single language")

    # config
    p_config = sub.add_parser("config", help="Formatter/linter detection and config")
    p_config.add_argument("repo", help="Path to repository")

    # git
    p_git = sub.add_parser("git", help="Commit log and branch analysis")
    p_git.add_argument("repo", help="Path to repository")

    # graph
    p_graph = sub.add_parser("graph", help="Internal import graph")
    p_graph.add_argument("repo", help="Path to repository")
    p_graph.add_argument("--lang", help="Filter to a single language")

    # symbols
    p_symbols = sub.add_parser("symbols", help="Symbol name extraction and pattern clustering")
    p_symbols.add_argument("repo", help="Path to repository")
    p_symbols.add_argument("--lang", help="Filter to a single language")

    # tests
    p_tests = sub.add_parser("tests", help="Test-to-source mapping and framework detection")
    p_tests.add_argument("repo", help="Path to repository")

    # Propagate global flags to subparsers
    for p in [p_scan, p_measure, p_config, p_git, p_graph, p_symbols, p_tests, p_analyze]:
        p.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
        p.add_argument("--out", metavar="FILE", help="Write output to file")

    args = parser.parse_args(argv)

    dispatch = {
        "analyze": cmd_analyze,
        "scan":    lambda a: _single_script_cmd(_scan.scan, a, {"lang_filter": getattr(a, "lang", None)}),
        "measure": lambda a: _single_script_cmd(_measure.measure, a, {"lang_filter": getattr(a, "lang", None)}),
        "config":  lambda a: _single_script_cmd(_config.detect, a),
        "git":     lambda a: _single_script_cmd(_git.analyze, a),
        "graph":   lambda a: _single_script_cmd(_graph.build_graph, a, {"lang_filter": getattr(a, "lang", None)}),
        "symbols": lambda a: _single_script_cmd(_symbols.extract_symbols, a, {"lang_filter": getattr(a, "lang", None)}),
        "tests":   lambda a: _single_script_cmd(_tests.analyze_tests, a),
    }

    handler = dispatch.get(args.command)
    if not handler:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
