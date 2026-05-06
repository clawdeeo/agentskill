"""Packaged CLI entrypoint for agentskill."""

import argparse
import sys

from agentskill.lib.generate_runner import generate_agents
from agentskill.lib.logging_utils import configure_logging
from agentskill.lib.output import run_and_output, write_output
from agentskill.lib.output_layouts import (
    DEFAULT_OUTPUT_LAYOUT,
    validate_output_layout,
)
from agentskill.lib.output_profiles import (
    DEFAULT_OUTPUT_PROFILE,
    validate_output_profile,
)
from agentskill.lib.runner import COMMANDS, run_many
from agentskill.lib.update_runner import update_agents


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        result = run_many(
            args.repos,
            getattr(args, "lang", None),
            getattr(args, "reference", None),
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    write_output(
        result,
        args.pretty,
        getattr(args, "out", None),
        schema_mode="analyze",
    )

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


def cmd_update(args: argparse.Namespace) -> int:
    if getattr(args, "pretty", False):
        print("update does not support --pretty", file=sys.stderr)
        return 1

    try:
        profile = validate_output_profile(
            getattr(args, "profile", DEFAULT_OUTPUT_PROFILE)
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        layout = validate_output_layout(getattr(args, "layout", DEFAULT_OUTPUT_LAYOUT))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return update_agents(
        args.repo,
        include_sections=getattr(args, "section", None),
        exclude_sections=getattr(args, "exclude_section", None),
        force=args.force,
        out=getattr(args, "out", None),
        profile=profile,
        layout=layout,
    )


def cmd_generate(args: argparse.Namespace) -> int:
    if getattr(args, "pretty", False):
        print("generate does not support --pretty", file=sys.stderr)
        return 1

    try:
        profile = validate_output_profile(
            getattr(args, "profile", DEFAULT_OUTPUT_PROFILE)
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        layout = validate_output_layout(getattr(args, "layout", DEFAULT_OUTPUT_LAYOUT))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return generate_agents(
        args.repo,
        out=getattr(args, "out", None),
        references=getattr(args, "reference", None),
        interactive=getattr(args, "interactive", False),
        profile=profile,
        layout=layout,
    )


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(
        prog="agentskill",
        description="agentskill CLI",
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

    p_analyze.add_argument(
        "--reference",
        action="append",
        help="Reference repository path or URL; may be repeated",
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
    p_update = sub.add_parser("update", help="Update or create AGENTS.md")
    p_update.add_argument("repo", help="Path to repository")

    p_update.add_argument(
        "--section",
        action="append",
        help="Regenerate only the named section; may be repeated",
    )

    p_update.add_argument(
        "--exclude-section",
        action="append",
        help="Skip regenerating the named section; may be repeated",
    )

    p_update.add_argument(
        "--force",
        action="store_true",
        help="Rebuild AGENTS.md from regenerated sections only",
    )

    p_update.add_argument("--out", metavar="FILE", help="Write markdown to file")
    p_update.add_argument(
        "--profile",
        default=DEFAULT_OUTPUT_PROFILE,
        help=f"Output profile (default: {DEFAULT_OUTPUT_PROFILE})",
    )

    p_update.add_argument(
        "--layout",
        default=DEFAULT_OUTPUT_LAYOUT,
        help=f"Output layout (default: {DEFAULT_OUTPUT_LAYOUT})",
    )

    p_generate = sub.add_parser(
        "generate", help="Generate AGENTS.md markdown from repository analysis"
    )

    p_generate.add_argument("repo", help="Path to repository")
    p_generate.add_argument(
        "--reference",
        action="append",
        help="Reference repository path or URL; may be repeated",
    )

    p_generate.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for missing or ambiguous generation inputs",
    )

    p_generate.add_argument("--out", metavar="FILE", help="Write markdown to file")
    p_generate.add_argument(
        "--profile",
        default=DEFAULT_OUTPUT_PROFILE,
        help=f"Output profile (default: {DEFAULT_OUTPUT_PROFILE})",
    )

    p_generate.add_argument(
        "--layout",
        default=DEFAULT_OUTPUT_LAYOUT,
        help=f"Output layout (default: {DEFAULT_OUTPUT_LAYOUT})",
    )

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
        "update": cmd_update,
        "generate": cmd_generate,
    }

    handler = dispatch.get(args.command)

    if not handler:
        parser.print_help()
        return 1

    return handler(args)
