"""CLI entry point for agentskill."""

import argparse
import json
import sys
from pathlib import Path

from .constants import JSON_INDENT
from .extractors.git import analyze_git_commits, analyze_branches, analyze_git_config, get_remote_info
from .extractors.filesystem import scan_source_files, detect_tooling, is_git_repo, get_project_metadata, analyze_dependency_philosophy
from .extractors.structure import extract_repo_structure
from .extractors.commands import extract_commands
from .engine import analyze_codebase
from .synthesis import AgentSynthesizer, SynthesisConfig


def analyze_repository(repo_path: str) -> dict:
    """Analyze a single repository using the language-agnostic engine."""
    abs_path = str(Path(repo_path).resolve())

    if not is_git_repo(abs_path):
        print(f"Warning: {repo_path} may not be a git repository", file=sys.stderr)

    files_by_lang = scan_source_files(abs_path)

    files_by_ext = {}
    for lang, files in files_by_lang.items():
        for filepath in files:
            ext = filepath.suffix
            if ext not in files_by_ext:
                files_by_ext[ext] = []
            files_by_ext[ext].append(filepath)

    result = analyze_codebase(abs_path, files_by_ext)

    result_dict = {
        "path": abs_path,
        "languages": result.languages,
        "examples": result.examples,

        "git": {
            "commits": analyze_git_commits(abs_path),
            "branches": analyze_branches(abs_path),
            "config": analyze_git_config(abs_path),
            "remotes": get_remote_info(abs_path),
        },

        "tooling": detect_tooling(abs_path),
        "metadata": get_project_metadata(abs_path),
        "structure": extract_repo_structure(abs_path),
        "dependencies": analyze_dependency_philosophy(abs_path),
        "commands": extract_commands(abs_path),
    }

    return result_dict


def generate_agents_md(analyses: list, repos: list, config: SynthesisConfig = None) -> str:
    """Generate AGENTS.md from analyses."""
    synthesizer = AgentSynthesizer(config)
    return synthesizer.synthesize(analyses, repos)


def main():
    parser = argparse.ArgumentParser(
        description="Generate AGENTS.md from your actual coding style",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agentskill ~/projects/myapp
  agentskill ~/projects/repo1 ~/projects/repo2 -o AGENTS.md
  agentskill ~/projects --json -o report.json
        """
    )

    parser.add_argument(
        "repos",
        nargs="+",
        help="Paths to repositories to analyze"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON analysis instead of AGENTS.md"
    )

    parser.add_argument(
        "--skip-git",
        action="store_true",
        help="Skip git analysis"
    )

    parser.add_argument(
        "--skip-tooling",
        action="store_true",
        help="Skip tooling detection"
    )

    args = parser.parse_args()

    valid_repos = []
    for repo in args.repos:
        if Path(repo).is_dir():
            valid_repos.append(repo)
        else:
            print(f"Error: Not a directory: {repo}", file=sys.stderr)

    if not valid_repos:
        print("Error: No valid repositories to analyze", file=sys.stderr)
        sys.exit(1)

    analyses = []
    for repo in valid_repos:
        print(f"Analyzing {repo}...", file=sys.stderr)
        analysis = analyze_repository(repo)
        analyses.append(analysis)

    if args.json:
        output = json.dumps({
            "repos": valid_repos,
            "analyses": analyses,
        }, indent=JSON_INDENT)
    else:
        config = SynthesisConfig(
            include_git=not args.skip_git,
            include_tooling=not args.skip_tooling,
        )
        output = generate_agents_md(analyses, valid_repos, config)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
