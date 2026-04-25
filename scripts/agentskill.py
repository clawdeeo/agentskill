#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple


SAMPLE_SIZE_SMALL = 30
SAMPLE_SIZE_MEDIUM = 50
COMMIT_LOG_LIMIT = 100
TOP_COMMIT_PREFIXES = 5
TOP_BRANCH_PREFIXES = 10

GIT_TIMEOUT = 30

JSON_INDENT = 2

HIDDEN_PREFIX = "."
GIT_DIR = ".git"
REMOTE_PREFIX = "remotes/origin/"

EXTENSIONS = {
    "rust": [".rs"],
    "python": [".py"],
    "javascript": [".js", ".mjs"],
    "typescript": [".ts", ".tsx"],
    "go": [".go"],
    "bash": [".sh"],
}

TOOL_FILES = {
    "rustfmt.toml": "rustfmt",
    ".rustfmt.toml": "rustfmt",
    "Cargo.toml": "cargo",
    ".github/workflows": "GitHub Actions",
    ".gitignore": "git",
    "Makefile": "make",
    "justfile": "just",
    ".pre-commit-config.yaml": "pre-commit",
}

SKIP_DIRS = {'node_modules', 'target', '__pycache__'}

PYTHON_VAR_KEYWORDS = {'self', 'cls', 'if', 'for', 'while'}

RUST_COMMENT_STYLES = {'///', '//!', '//', '/*'}
PYTHON_COMMENT_STYLE = '#'

RUST_ERROR_PATTERNS = ["unwrap()", "expect(", "?", "panic!", "Result<"]
RUST_ERROR_KEYS = ["unwrap", "expect", "?", "panic", "Result"]

CASE_SCREAMING_SNAKE = "SCREAMING_SNAKE_CASE"
CASE_SNAKE = "snake_case"
CASE_KEBAB = "kebab-case"
CASE_CAMEL = "camelCase"
CASE_PASCAL = "PascalCase"
CASE_MIXED = "mixed"

LANG_RUST = "rust"
LANG_PYTHON = "python"

NAME_VAR = "vars"
NAME_FUNCTION = "functions"
NAME_TYPE = "types"
NAME_CONST = "consts"


@dataclass
class NamingPatterns:
    vars: Dict[str, int] = None
    types: Dict[str, int] = None
    consts: Dict[str, int] = None
    files: Dict[str, int] = None
    branches: Dict[str, int] = None

    def __post_init__(self):
        if self.vars is None:
            self.vars = {}
        if self.types is None:
            self.types = {}
        if self.consts is None:
            self.consts = {}
        if self.files is None:
            self.files = {}
        if self.branches is None:
            self.branches = {}


@dataclass
class CodeStyle:
    naming_descriptiveness: Dict[str, float] = None
    blank_lines: Dict[str, float] = None
    comment_patterns: Dict[str, int] = None
    import_organization: Dict[str, str] = None

    def __post_init__(self):
        if self.naming_descriptiveness is None:
            self.naming_descriptiveness = {}
        if self.blank_lines is None:
            self.blank_lines = {}
        if self.comment_patterns is None:
            self.comment_patterns = {}
        if self.import_organization is None:
            self.import_organization = {}


@dataclass
class Report:
    repos: List[str]
    languages: Dict[str, Dict]
    naming: Dict[str, NamingPatterns]
    code_style: Dict[str, CodeStyle]
    comments: Dict[str, Dict]
    functions: Dict[str, Dict]
    errors: Dict[str, Dict]
    git: Dict
    tooling: Dict
    architecture: Dict


def detect_case_style(s: str) -> str:
    if s.isupper() and '_' in s:
        return CASE_SCREAMING_SNAKE
    if s.islower() and '_' in s:
        return CASE_SNAKE
    if s.islower() and '-' in s:
        return CASE_KEBAB
    if s[0].islower() and '_' not in s and '-' not in s:
        return CASE_CAMEL
    if s[0].isupper() and '_' not in s and '-' not in s:
        return CASE_PASCAL
    return CASE_MIXED


def run_git_log(repo_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path, "log", "--pretty=format:%s", f"-{COMMIT_LOG_LIMIT}"],
        capture_output=True, text=True, timeout=GIT_TIMEOUT
    )
    return result.stdout if result.returncode == 0 else ""


def extract_commit_prefixes(commits: List[str]) -> Dict[str, int]:
    prefixes = {}
    for commit in commits:
        match = re.match(r'^(\[\w+\])(?:\(|:)', commit.lower())
        if match:
            prefix = match.group(1)
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return prefixes


def analyze_git_commits(repo_path: str) -> Dict:
    try:
        stdout = run_git_log(repo_path)
        commits = [c for c in stdout.strip().split('\n') if c]

        lengths = [len(c) for c in commits]
        prefixes = extract_commit_prefixes(commits)

        return {
            "count": len(commits),
            "avg_length": sum(lengths) / len(lengths) if lengths else 0,
            "common_prefixes": dict(sorted(prefixes.items(), key=lambda x: -x[1])[:TOP_COMMIT_PREFIXES])
        }
    except Exception:
        return {}


def run_git_branch(repo_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path, "branch", "-a"],
        capture_output=True, text=True, timeout=GIT_TIMEOUT
    )
    return result.stdout if result.returncode == 0 else ""


def extract_branch_prefixes(branches: List[str]) -> Dict[str, int]:
    prefixes = {}
    for branch in branches:
        branch = branch.replace(REMOTE_PREFIX, '')
        parts = branch.split('/')
        if len(parts) > 1:
            prefix = parts[0]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return prefixes


def analyze_branches(repo_path: str) -> Dict:
    try:
        stdout = run_git_branch(repo_path)
        branches = [b.strip().strip('* ') for b in stdout.split('\n') if b.strip()]

        prefixes = extract_branch_prefixes(branches)

        return {
            "count": len(branches),
            "common_prefixes": dict(sorted(prefixes.items(), key=lambda x: -x[1])[:TOP_BRANCH_PREFIXES])
        }
    except Exception:
        return {}


def is_hidden_path(root: Path) -> bool:
    return any(part.startswith(HIDDEN_PREFIX) for part in root.parts)


def should_skip_dir(root: Path) -> bool:
    return bool(SKIP_DIRS.intersection(root.parts))


def scan_source_files(repo_path: str) -> Dict[str, List[Path]]:
    files_by_lang = {lang: [] for lang in EXTENSIONS}

    for root_str, _, files in os.walk(repo_path):
        root = Path(root_str)
        if is_hidden_path(root) or should_skip_dir(root):
            continue

        for file in files:
            filepath = root / file
            for lang, exts in EXTENSIONS.items():
                if any(file.endswith(ext) for ext in exts):
                    files_by_lang[lang].append(filepath)

    return {k: v for k, v in files_by_lang.items() if v}


def track_blank_lines(stripped: str, prev_was_code: bool, blank_streak: int, counts: List[int]) -> Tuple[bool, int]:
    if not stripped:
        return prev_was_code, blank_streak + 1

    if prev_was_code and blank_streak > 0:
        counts.append(blank_streak)

    return True, 0


def detect_comment_style(stripped: str) -> str:
    if stripped.startswith('///') or stripped.startswith('/**'):
        return '///'
    if stripped.startswith('//!'):
        return '//!'
    if stripped.startswith('//'):
        return '//'
    if stripped.startswith('/*'):
        return '/*'
    if stripped.startswith('#'):
        return '#'
    return None


def extract_rust_name_lengths(line: str) -> Dict[str, int]:
    lengths = {}

    if 'let ' in line:
        match = re.search(r'let\s+(?:mut\s+)?(\w+)', line)
        if match:
            lengths[NAME_VAR] = len(match.group(1))

    if 'fn ' in line:
        match = re.search(r'fn\s+(\w+)', line)
        if match:
            lengths[NAME_FUNCTION] = len(match.group(1))

    if re.search(r'(?:struct|enum|trait|type)\s+\w+', line):
        match = re.search(r'(?:struct|enum|trait|type)\s+(\w+)', line)
        if match:
            lengths[NAME_TYPE] = len(match.group(1))

    if 'const ' in line:
        match = re.search(r'const\s+(\w+)', line)
        if match:
            lengths[NAME_CONST] = len(match.group(1))

    return lengths


def extract_python_name_lengths(line: str) -> Dict[str, int]:
    lengths = {}

    if re.match(r'^\s*\w+\s*=\s*', line) and not line.strip().startswith(PYTHON_COMMENT_STYLE):
        match = re.match(r'^\s*(\w+)\s*=', line)
        if match and match.group(1) not in PYTHON_VAR_KEYWORDS:
            lengths[NAME_VAR] = len(match.group(1))

    if re.match(r'^def\s+\w+', line):
        match = re.search(r'def\s+(\w+)', line)
        if match:
            lengths[NAME_FUNCTION] = len(match.group(1))

    if re.match(r'^class\s+\w+', line):
        match = re.search(r'class\s+(\w+)', line)
        if match:
            lengths[NAME_TYPE] = len(match.group(1))

    return lengths


def process_file_for_style(filepath: Path, language: str, name_lengths: Dict, blank_counts: List, comment_styles: Dict):
    content = filepath.read_text(errors='ignore')
    lines = content.split('\n')

    prev_was_code = False
    blank_streak = 0

    for line in lines:
        stripped = line.strip()

        prev_was_code, blank_streak = track_blank_lines(stripped, prev_was_code, blank_streak, blank_counts)

        style = detect_comment_style(stripped)
        if style:
            comment_styles[style] = comment_styles.get(style, 0) + 1

        if language == LANG_RUST:
            lengths = extract_rust_name_lengths(line)
            for key, val in lengths.items():
                name_lengths[key].append(val)

        elif language == LANG_PYTHON:
            lengths = extract_python_name_lengths(line)
            for key, val in lengths.items():
                name_lengths[key].append(val)


def analyze_code_style(files: List[Path], language: str) -> CodeStyle:
    style = CodeStyle()

    name_lengths = {NAME_VAR: [], NAME_TYPE: [], NAME_FUNCTION: [], NAME_CONST: []}
    blank_line_counts = []
    comment_styles = {k: 0 for k in RUST_COMMENT_STYLES | {PYTHON_COMMENT_STYLE}}

    for filepath in files[:SAMPLE_SIZE_SMALL]:
        try:
            process_file_for_style(filepath, language, name_lengths, blank_line_counts, comment_styles)
        except Exception:
            continue

    for key, lengths in name_lengths.items():
        if lengths:
            style.naming_descriptiveness[key] = sum(lengths) / len(lengths)

    if blank_line_counts:
        style.blank_lines["avg_between_blocks"] = sum(blank_line_counts) / len(blank_line_counts)
        style.blank_lines["max_consecutive"] = max(blank_line_counts)

    style.comment_patterns = comment_styles

    return style


def count_rust_error_pattern(line: str, pattern: str) -> bool:
    if pattern == "?":
        return '?' in line and not line.strip().startswith('//')
    return pattern in line


def extract_rust_naming(line: str) -> Dict[str, Tuple[str, str]]:
    naming = {}

    if 'let ' in line:
        match = re.search(r'let\s+(?:mut\s+)?(\w+)', line)
        if match:
            naming[NAME_VAR] = (match.group(1), detect_case_style(match.group(1)))

    if 'fn ' in line:
        match = re.search(r'fn\s+(\w+)', line)
        if match:
            naming[NAME_FUNCTION] = (match.group(1), detect_case_style(match.group(1)))

    if 'struct ' in line or 'enum ' in line or 'trait ' in line:
        match = re.search(r'(?:struct|enum|trait)\s+(\w+)', line)
        if match:
            naming[NAME_TYPE] = (match.group(1), detect_case_style(match.group(1)))

    if 'const ' in line:
        match = re.search(r'const\s+(\w+)', line)
        if match:
            naming[NAME_CONST] = (match.group(1), detect_case_style(match.group(1)))

    return naming


def process_rust_file(filepath: Path, naming: Dict, error_patterns: Dict, counters: Dict):
    content = filepath.read_text(errors='ignore')
    lines = content.split('\n')

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('//'):
            counters["comment"] += 1
        elif stripped:
            counters["code"] += 1

        for i, pattern in enumerate(RUST_ERROR_PATTERNS):
            key = RUST_ERROR_KEYS[i]
            if count_rust_error_pattern(line, pattern):
                error_patterns[key] += 1

        name_info = extract_rust_naming(line)
        for key, (name, style) in name_info.items():
            naming[key][style] = naming[key].get(style, 0) + 1


def analyze_rust_files(files: List[Path]) -> Dict:
    naming = {NAME_VAR: {}, NAME_TYPE: {}, NAME_CONST: {}, NAME_FUNCTION: {}}
    error_patterns = {k: 0 for k in RUST_ERROR_KEYS}
    counters = {"comment": 0, "code": 0}

    for filepath in files[:SAMPLE_SIZE_MEDIUM]:
        try:
            process_rust_file(filepath, naming, error_patterns, counters)
        except Exception:
            continue

    return {
        "naming": naming,
        "error_handling": error_patterns,
        "comments": {
            "comment_lines": counters["comment"],
            "code_lines": counters["code"],
            "density": counters["comment"] / counters["code"] if counters["code"] > 0 else 0
        }
    }


def detect_tooling(repo_path: str) -> Dict:
    repo = Path(repo_path)
    detected = {}

    for file_pattern, tool in TOOL_FILES.items():
        if (repo / file_pattern).exists():
            detected[tool] = True

    if (repo / ".github" / "workflows").exists():
        detected["GitHub Actions CI"] = True

    return detected


def is_git_repo(repo_path: str) -> bool:
    return os.path.isdir(os.path.join(repo_path, GIT_DIR))


def build_repo_report(abs_path: str, files_by_lang: Dict) -> Dict:
    code_styles = {}
    for lang, files in files_by_lang.items():
        code_styles[lang] = analyze_code_style(files, lang)

    languages = {}
    if LANG_RUST in files_by_lang:
        languages[LANG_RUST] = analyze_rust_files(files_by_lang[LANG_RUST])

    for lang, files in files_by_lang.items():
        if lang not in languages:
            languages[lang] = {}
        languages[lang]["file_count"] = len(files)

    return {
        "path": abs_path,
        "cloc": {},
        "git": {
            "commits": analyze_git_commits(abs_path),
            "branches": analyze_branches(abs_path)
        },
        "tooling": detect_tooling(abs_path),
        "code_style": code_styles,
        "languages": languages
    }


def analyze_repo(repo_path: str) -> Dict:
    abs_path = os.path.abspath(repo_path)

    if not is_git_repo(abs_path):
        print(f"Warning: {repo_path} may not be a git repository", file=sys.stderr)

    files_by_lang = scan_source_files(abs_path)
    return build_repo_report(abs_path, files_by_lang)


def convert_dataclasses(obj):
    if isinstance(obj, dict):
        return {k: convert_dataclasses(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dataclasses(item) for item in obj]
    elif hasattr(obj, '__dataclass_fields__'):
        return convert_dataclasses(asdict(obj))
    return obj


def validate_repos(repo_paths: List[str]) -> List[str]:
    valid = []
    for repo in repo_paths:
        if os.path.isdir(repo):
            valid.append(repo)
        else:
            print(f"Error: Not a directory: {repo}", file=sys.stderr)
    return valid


def generate_report(valid_repos: List[str]) -> Dict:
    reports = []
    for repo in valid_repos:
        print(f"Analyzing {repo}...", file=sys.stderr)
        reports.append(analyze_repo(repo))

    return {
        "repos": valid_repos,
        "analyses": [asdict(r) if hasattr(r, '__dataclass_fields__') else r for r in reports]
    }


def output_report(report: Dict, output_path: str = None):
    report = convert_dataclasses(report)
    output = json.dumps(report, indent=JSON_INDENT)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(output)
        print(f"Report written to {output_path}", file=sys.stderr)
    else:
        print(output)


def main():
    parser = argparse.ArgumentParser(description="Extract coding style metrics from repositories")
    parser.add_argument("repos", nargs="+", help="Paths to repositories to analyze")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")

    args = parser.parse_args()

    valid_repos = validate_repos(args.repos)
    if not valid_repos:
        print("Error: No valid repositories to analyze", file=sys.stderr)
        sys.exit(1)

    final_report = generate_report(valid_repos)
    output_report(final_report, args.output)


if __name__ == "__main__":
    main()
