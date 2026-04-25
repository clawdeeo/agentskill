#!/usr/bin/env python3
"""
Extract coding style metrics from one or more repositories.
Outputs JSON report for AGENTS.md synthesis.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class NamingPatterns:
    vars: Dict[str, int] = None
    types: Dict[str, int] = None
    consts: Dict[str, int] = None
    files: Dict[str, int] = None
    branches: Dict[str, int] = None
    
    def __post_init__(self):
        if self.vars is None: self.vars = {}
        if self.types is None: self.types = {}
        if self.consts is None: self.consts = {}
        if self.files is None: self.files = {}
        if self.branches is None: self.branches = {}


@dataclass
class CodeStyle:
    naming_descriptiveness: Dict[str, float] = None  # avg name length by type
    blank_lines: Dict[str, float] = None  # avg blank lines between constructs
    comment_patterns: Dict[str, int] = None  # // vs /* */ vs /// vs //!
    import_organization: Dict[str, str] = None  # how imports are grouped/ordered
    
    def __post_init__(self):
        if self.naming_descriptiveness is None: self.naming_descriptiveness = {}
        if self.blank_lines is None: self.blank_lines = {}
        if self.comment_patterns is None: self.comment_patterns = {}
        if self.import_organization is None: self.import_organization = {}


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
    """Detect naming case style of a string."""
    if s.isupper() and '_' in s:
        return "SCREAMING_SNAKE_CASE"
    if s.islower() and '_' in s:
        return "snake_case"
    if s.islower() and '-' in s:
        return "kebab-case"
    if s[0].islower() and '_' not in s and '-' not in s:
        return "camelCase"
    if s[0].isupper() and '_' not in s and '-' not in s:
        return "PascalCase"
    return "mixed"


def run_cloc(repo_path: str) -> Dict:
    """Run cloc to get language statistics."""
    try:
        result = subprocess.run(
            ["cloc", "--json", repo_path],
            capture_output=True, text=True, timeout=60
        )
        return json.loads(result.stdout) if result.returncode == 0 else {}
    except Exception:
        return {}


def analyze_git_commits(repo_path: str) -> Dict:
    """Analyze git commit message patterns."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", "--pretty=format:%s", "-100"],
            capture_output=True, text=True, timeout=30
        )
        commits = result.stdout.strip().split('\n') if result.stdout else []
        
        prefixes = {}
        lengths = []
        
        for commit in commits:
            if not commit:
                continue
            lengths.append(len(commit))
            
            # Check for conventional commit prefixes
            match = re.match(r'^([\w]+)(?:\(|:)', commit.lower())
            if match:
                prefix = match.group(1)
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        return {
            "count": len(commits),
            "avg_length": sum(lengths) / len(lengths) if lengths else 0,
            "common_prefixes": dict(sorted(prefixes.items(), key=lambda x: -x[1])[:5])
        }
    except Exception:
        return {}


def analyze_branches(repo_path: str) -> Dict:
    """Analyze branch naming patterns."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "branch", "-a"],
            capture_output=True, text=True, timeout=30
        )
        branches = [b.strip().strip('* ') for b in result.stdout.split('\n') if b.strip()]
        
        prefixes = {}
        for branch in branches:
            # Skip remote prefixes
            branch = branch.replace('remotes/origin/', '')
            parts = branch.split('/')
            if len(parts) > 1:
                prefix = parts[0]
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        return {
            "count": len(branches),
            "common_prefixes": dict(sorted(prefixes.items(), key=lambda x: -x[1])[:10])
        }
    except Exception:
        return {}


def scan_source_files(repo_path: str) -> Dict[str, List[Path]]:
    """Scan for source files by language."""
    extensions = {
        "rust": [".rs"],
        "python": [".py"],
        "javascript": [".js", ".mjs"],
        "typescript": [".ts", ".tsx"],
        "go": [".go"],
        "bash": [".sh"],
    }
    
    files_by_lang = {lang: [] for lang in extensions}
    
    for root, _, files in os.walk(repo_path):
        # Skip hidden dirs and common non-source directories
        if any(part.startswith('.') for part in Path(root).parts):
            continue
        if 'node_modules' in root or 'target' in root or '__pycache__' in root:
            continue
        
        for file in files:
            filepath = Path(root) / file
            for lang, exts in extensions.items():
                if any(file.endswith(ext) for ext in exts):
                    files_by_lang[lang].append(filepath)
    
    return {k: v for k, v in files_by_lang.items() if v}


def analyze_code_style(files: List[Path], language: str) -> CodeStyle:
    """Analyze code style patterns: naming descriptiveness, spacing, comments."""
    style = CodeStyle()
    
    name_lengths = {"vars": [], "types": [], "functions": [], "consts": []}
    blank_line_counts = []
    comment_styles = {"//": 0, "/*": 0, "///": 0, "//!": 0, "#": 0, "//": 0}
    
    for filepath in files[:30]:  # Sample
        try:
            content = filepath.read_text(errors='ignore')
            lines = content.split('\n')
            
            prev_was_code = False
            blank_streak = 0
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Track blank lines between code blocks
                if not stripped:
                    blank_streak += 1
                elif prev_was_code and blank_streak > 0:
                    blank_line_counts.append(blank_streak)
                    blank_streak = 0
                    prev_was_code = True
                else:
                    prev_was_code = True
                    blank_streak = 0
                
                # Comment style detection
                if stripped.startswith('///') or stripped.startswith('/**'):
                    comment_styles['///'] += 1
                elif stripped.startswith('//!'):
                    comment_styles['//!'] += 1
                elif stripped.startswith('//') or stripped.startswith('#'):
                    comment_styles['//'] += 1
                elif stripped.startswith('/*'):
                    comment_styles['/*'] += 1
                
                # Name length tracking
                if language == "rust":
                    if 'let ' in line:
                        match = re.search(r'let\s+(?:mut\s+)?(\w+)', line)
                        if match:
                            name_lengths["vars"].append(len(match.group(1)))
                    if 'fn ' in line:
                        match = re.search(r'fn\s+(\w+)', line)
                        if match:
                            name_lengths["functions"].append(len(match.group(1)))
                    if re.search(r'(?:struct|enum|trait|type)\s+\w+', line):
                        match = re.search(r'(?:struct|enum|trait|type)\s+(\w+)', line)
                        if match:
                            name_lengths["types"].append(len(match.group(1)))
                    if 'const ' in line:
                        match = re.search(r'const\s+(\w+)', line)
                        if match:
                            name_lengths["consts"].append(len(match.group(1)))
                
                elif language == "python":
                    if re.match(r'^\s*\w+\s*=\s*', line) and not line.strip().startswith('#'):
                        match = re.match(r'^\s*(\w+)\s*=', line)
                        if match and match.group(1) not in ['self', 'cls', 'if', 'for', 'while']:
                            name_lengths["vars"].append(len(match.group(1)))
                    if re.match(r'^def\s+\w+', line):
                        match = re.search(r'def\s+(\w+)', line)
                        if match:
                            name_lengths["functions"].append(len(match.group(1)))
                    if re.match(r'^class\s+\w+', line):
                        match = re.search(r'class\s+(\w+)', line)
                        if match:
                            name_lengths["types"].append(len(match.group(1)))
        except Exception:
            continue
    
    # Calculate averages
    for key, lengths in name_lengths.items():
        if lengths:
            style.naming_descriptiveness[key] = sum(lengths) / len(lengths)
    
    if blank_line_counts:
        style.blank_lines["avg_between_blocks"] = sum(blank_line_counts) / len(blank_line_counts)
        style.blank_lines["max_consecutive"] = max(blank_line_counts)
    
    style.comment_patterns = comment_styles
    
    return style


def analyze_rust_files(files: List[Path]) -> Dict:
    """Analyze Rust-specific patterns."""
    naming = {"vars": {}, "types": {}, "consts": {}, "functions": {}}
    error_patterns = {"unwrap": 0, "expect": 0, "?": 0, "Result": 0, "panic": 0}
    comment_lines = 0
    code_lines = 0
    
    for filepath in files[:50]:  # Sample first 50 files
        try:
            content = filepath.read_text(errors='ignore')
            lines = content.split('\n')
            
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('//'):
                    comment_lines += 1
                elif stripped:
                    code_lines += 1
                    
                    # Error patterns
                    if 'unwrap()' in line:
                        error_patterns["unwrap"] += 1
                    if 'expect(' in line:
                        error_patterns["expect"] += 1
                    if '?' in line and not line.strip().startswith('//'):
                        error_patterns["?"] += 1
                    if 'panic!' in line:
                        error_patterns["panic"] += 1
                    if 'Result<' in line:
                        error_patterns["Result"] += 1
                    
                    # Naming patterns
                    if 'let ' in line:
                        var_match = re.search(r'let\s+(?:mut\s+)?(\w+)', line)
                        if var_match:
                            style = detect_case_style(var_match.group(1))
                            naming["vars"][style] = naming["vars"].get(style, 0) + 1
                    
                    if 'fn ' in line:
                        fn_match = re.search(r'fn\s+(\w+)', line)
                        if fn_match:
                            style = detect_case_style(fn_match.group(1))
                            naming["functions"][style] = naming["functions"].get(style, 0) + 1
                    
                    if 'struct ' in line or 'enum ' in line or 'trait ' in line:
                        type_match = re.search(r'(?:struct|enum|trait)\s+(\w+)', line)
                        if type_match:
                            style = detect_case_style(type_match.group(1))
                            naming["types"][style] = naming["types"].get(style, 0) + 1
                    
                    if 'const ' in line:
                        const_match = re.search(r'const\s+(\w+)', line)
                        if const_match:
                            style = detect_case_style(const_match.group(1))
                            naming["consts"][style] = naming["consts"].get(style, 0) + 1
        except Exception:
            continue
    
    return {
        "naming": naming,
        "error_handling": error_patterns,
        "comments": {
            "comment_lines": comment_lines,
            "code_lines": code_lines,
            "density": comment_lines / code_lines if code_lines > 0 else 0
        }
    }


def detect_tooling(repo_path: str) -> Dict:
    """Detect tooling configs (linters, formatters, CI)."""
    repo = Path(repo_path)
    
    tool_files = {
        "rustfmt.toml": "rustfmt",
        ".rustfmt.toml": "rustfmt",
        "Cargo.toml": "cargo",
        ".github/workflows": "GitHub Actions",
        ".gitignore": "git",
        "Makefile": "make",
        "justfile": "just",
        ".pre-commit-config.yaml": "pre-commit",
    }
    
    detected = {}
    for file_pattern, tool in tool_files.items():
        if (repo / file_pattern).exists():
            detected[tool] = True
    
    # Check for CI directory
    if (repo / ".github" / "workflows").exists():
        detected["GitHub Actions CI"] = True
    
    return detected


def analyze_repo(repo_path: str) -> Dict:
    """Analyze a single repository and return report data."""
    abs_path = os.path.abspath(repo_path)
    
    if not os.path.isdir(os.path.join(abs_path, '.git')):
        print(f"Warning: {repo_path} may not be a git repository", file=sys.stderr)
    
    report = {
        "path": abs_path,
        "cloc": run_cloc(abs_path),
        "git": {
            "commits": analyze_git_commits(abs_path),
            "branches": analyze_branches(abs_path)
        },
        "tooling": detect_tooling(abs_path),
        "languages": {}
    }
    
    # Analyze source files by language
    files_by_lang = scan_source_files(abs_path)
    
    # Analyze code style for each language
    code_styles = {}
    for lang, files in files_by_lang.items():
        code_styles[lang] = analyze_code_style(files, lang)
    
    report["code_style"] = code_styles
    
    if "rust" in files_by_lang:
        report["languages"]["rust"] = analyze_rust_files(files_by_lang["rust"])
    
    # Add file count info
    for lang, files in files_by_lang.items():
        if lang not in report["languages"]:
            report["languages"][lang] = {}
        report["languages"][lang]["file_count"] = len(files)
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Extract coding style metrics from repositories"
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
    
    args = parser.parse_args()
    
    # Validate repos
    valid_repos = []
    for repo in args.repos:
        if os.path.isdir(repo):
            valid_repos.append(repo)
        else:
            print(f"Error: Not a directory: {repo}", file=sys.stderr)
    
    if not valid_repos:
        print("Error: No valid repositories to analyze", file=sys.stderr)
        sys.exit(1)
    
    # Analyze each repo
    reports = []
    for repo in valid_repos:
        print(f"Analyzing {repo}...", file=sys.stderr)
        reports.append(analyze_repo(repo))
    
    # Build final report
    final_report = {
        "repos": valid_repos,
        "analyses": [asdict(r) if hasattr(r, '__dataclass_fields__') else r for r in reports]
    }
    
    # Recursively convert any nested dataclasses
    def convert_dataclasses(obj):
        if isinstance(obj, dict):
            return {k: convert_dataclasses(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_dataclasses(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return convert_dataclasses(asdict(obj))
        return obj
    
    final_report = convert_dataclasses(final_report)
    
    output = json.dumps(final_report, indent=2)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
