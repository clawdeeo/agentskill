#!/usr/bin/env python3
"""Exact formatting metrics. No estimation. Count every line.

Measures indentation, line lengths, blank line patterns, trailing newlines,
and trailing whitespace across all source files in the repository.

Usage:
    python scripts/measure.py <repo>
    python scripts/measure.py <repo> --lang python
    python scripts/measure.py <repo> --pretty
"""

import ast
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median

SKIP_DIRS: set[str] = {
    "node_modules", "__pycache__", "dist", "build", "out",
    "target", "vendor", "third_party", ".eggs", "site-packages",
    "venv", ".venv", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov", ".next", ".nuxt", "coverage",
}

EXTENSIONS: dict[str, str] = {
    ".py":   "python",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".mjs":  "javascript",
    ".go":   "go",
    ".rs":   "rust",
    ".rb":   "ruby",
    ".java": "java",
    ".kt":   "kotlin",
    ".swift": "swift",
    ".cpp":  "cpp",
    ".cc":   "cpp",
    ".cxx":  "cpp",
    ".c":    "c",
    ".cs":   "csharp",
}

# Regex patterns for top-level definitions per language
TOP_LEVEL_DEF_RE: dict[str, re.Pattern] = {
    "typescript": re.compile(r"^(export\s+)?(default\s+)?(async\s+)?function\s+\w+|^(export\s+)?(abstract\s+)?class\s+\w+|^(export\s+)?const\s+\w+\s*=\s*(async\s+)?\("),
    "javascript": re.compile(r"^(export\s+)?(default\s+)?(async\s+)?function\s+\w+|^(export\s+)?(abstract\s+)?class\s+\w+|^(export\s+)?const\s+\w+\s*=\s*(async\s+)?\("),
    "go":         re.compile(r"^func\s+"),
    "rust":       re.compile(r"^(pub\s+)?(async\s+)?fn\s+\w+|^(pub\s+)?struct\s+\w+|^(pub\s+)?enum\s+\w+|^(pub\s+)?trait\s+\w+|^impl\s+"),
    "ruby":       re.compile(r"^def\s+\w+|^class\s+\w+|^module\s+\w+"),
    "java":       re.compile(r"^\s*(public|private|protected|static|final|abstract)\s+.*\{$"),
}

METHOD_DEF_RE: dict[str, re.Pattern] = {
    "typescript": re.compile(r"^  (public|private|protected|static|async|abstract|\w+)\s+\w+\s*\("),
    "javascript": re.compile(r"^  (async\s+)?\w+\s*\("),
    "go":         re.compile(r"^\tfunc\s+"),
    "ruby":       re.compile(r"^  def\s+"),
}


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def _collect_files(repo: Path, lang_filter: str | None) -> dict[str, list[Path]]:
    by_lang: dict[str, list[Path]] = {}
    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fn in files:
            ext = Path(fn).suffix.lower()
            lang = EXTENSIONS.get(ext)
            if not lang:
                continue
            if lang_filter and lang != lang_filter:
                continue
            if lang not in by_lang:
                by_lang[lang] = []
            by_lang[lang].append(Path(dirpath) / fn)
    return by_lang


def _percentile(sorted_data: list[int], p: int) -> int:
    if not sorted_data:
        return 0
    idx = max(0, int(len(sorted_data) * p / 100) - 1)
    return sorted_data[min(idx, len(sorted_data) - 1)]


def _measure_indentation(lines: list[str]) -> dict:
    tab_lines: list[str] = []
    space_sizes: list[int] = []
    has_spaces = False
    has_tabs = False

    for line in lines:
        if not line.rstrip():
            continue
        if line.startswith("\t"):
            has_tabs = True
            tab_lines.append(line)
        elif line.startswith(" "):
            has_spaces = True
            indent = len(line) - len(line.lstrip(" "))
            if indent > 0:
                space_sizes.append(indent)

    if has_tabs and not has_spaces:
        return {"unit": "tabs", "size": 1}
    if not has_spaces:
        return {"unit": "unknown", "size": 0}

    if not space_sizes:
        return {"unit": "spaces", "size": 4}

    # Mode of small indent values as the unit
    small = [s for s in space_sizes if s <= 8]
    if not small:
        return {"unit": "spaces", "size": 4}

    cnt = Counter(small)
    # Most common indent level ≤ 8 that is a factor of others
    candidates = sorted(cnt.keys())
    unit = candidates[0]
    # Prefer 2 or 4 if dominant
    for s in [2, 4]:
        if cnt[s] > cnt.get(unit, 0) * 0.5:
            unit = s
            break

    return {"unit": "spaces", "size": unit}


def _measure_line_lengths(all_lengths: list[int]) -> dict:
    if len(all_lengths) < 5:
        return {}
    s = sorted(all_lengths)
    return {
        "p50": _percentile(s, 50),
        "p75": _percentile(s, 75),
        "p95": _percentile(s, 95),
        "p99": _percentile(s, 99),
        "max": s[-1],
    }


def _count_blanks_before_line(lines: list[str], i: int) -> int:
    count = 0
    j = i - 1
    while j >= 0 and not lines[j].strip():
        count += 1
        j -= 1
    return count


def _measure_blank_lines_python(files: list[Path]) -> dict:
    """Use ast module for Python blank line analysis."""
    between_top_level: list[int] = []
    between_methods: list[int] = []
    after_class_decl: list[int] = []
    after_imports: list[int] = []

    for fp in files:
        try:
            source = fp.read_text(errors="ignore")
            lines = source.splitlines()
            tree = ast.parse(source)
        except Exception:
            continue

        # Top-level definitions
        top_nodes = [
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and n.col_offset == 0
        ]
        top_nodes.sort(key=lambda n: n.lineno)

        for node in top_nodes:
            blanks = _count_blanks_before_line(lines, node.lineno - 1)
            if node.lineno > 1:
                between_top_level.append(blanks)

        # Methods inside classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                # After class declaration line
                if methods:
                    first_method = methods[0]
                    blanks = _count_blanks_before_line(lines, first_method.lineno - 1)
                    after_class_decl.append(blanks)

                for m in methods[1:]:
                    blanks = _count_blanks_before_line(lines, m.lineno - 1)
                    between_methods.append(blanks)

        # After last import
        import_lines = [
            n.lineno for n in ast.walk(tree)
            if isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        if import_lines:
            last_import = max(import_lines)
            if last_import < len(lines):
                count = 0
                j = last_import  # 1-indexed → 0-indexed = last_import
                while j < len(lines) and not lines[j].strip():
                    count += 1
                    j += 1
                after_imports.append(count)

    def _dist_summary(data: list[int]) -> dict:
        if not data:
            return {}
        cnt = Counter(data)
        mode = cnt.most_common(1)[0][0]
        distribution = {str(k): v for k, v in sorted(cnt.items())}
        return {"mode": mode, "distribution": distribution}

    return {
        "between_top_level_defs": _dist_summary(between_top_level),
        "between_methods": _dist_summary(between_methods),
        "after_class_declaration": _dist_summary(after_class_decl),
        "after_imports": _dist_summary(after_imports),
    }


def _measure_blank_lines_generic(files: list[Path], lang: str) -> dict:
    """Regex-based blank line analysis for non-Python languages."""
    pattern = TOP_LEVEL_DEF_RE.get(lang)
    method_pattern = METHOD_DEF_RE.get(lang)

    between_top_level: list[int] = []
    between_methods: list[int] = []

    for fp in files:
        try:
            lines = fp.read_text(errors="ignore").splitlines()
        except Exception:
            continue

        if pattern:
            for i, line in enumerate(lines):
                if pattern.match(line) and i > 0:
                    between_top_level.append(_count_blanks_before_line(lines, i))

        if method_pattern:
            for i, line in enumerate(lines):
                if method_pattern.match(line) and i > 0:
                    between_methods.append(_count_blanks_before_line(lines, i))

    def _dist_summary(data: list[int]) -> dict:
        if not data:
            return {}
        cnt = Counter(data)
        mode = cnt.most_common(1)[0][0]
        return {"mode": mode, "distribution": {str(k): v for k, v in sorted(cnt.items())}}

    result: dict = {}
    if between_top_level:
        result["between_top_level_defs"] = _dist_summary(between_top_level)
    if between_methods:
        result["between_methods"] = _dist_summary(between_methods)
    return result


def _measure_lang(lang: str, files: list[Path]) -> dict:
    all_line_lengths: list[int] = []
    indent_votes: list[dict] = []
    trailing_newline_present = 0
    trailing_newline_absent = 0
    files_with_trailing_ws = 0
    tab_files: list[str] = []
    mixed_files: list[str] = []

    for fp in files:
        try:
            content = fp.read_text(errors="ignore")
        except Exception:
            continue

        raw_lines = content.split("\n")
        # Drop the last empty element from a trailing newline
        lines_for_indent = raw_lines[:-1] if content.endswith("\n") else raw_lines

        # Indentation
        indent = _measure_indentation(lines_for_indent)
        indent_votes.append(indent)

        has_tabs = any(l.startswith("\t") for l in lines_for_indent if l.strip())
        has_spaces = any(l.startswith(" ") for l in lines_for_indent if l.strip())
        if has_tabs and has_spaces:
            mixed_files.append(str(fp))
        elif has_tabs:
            tab_files.append(str(fp))

        # Line lengths (non-blank lines only)
        for line in lines_for_indent:
            stripped = line.rstrip("\n\r")
            if stripped.strip():
                all_line_lengths.append(len(stripped))

        # Trailing newline
        if content.endswith("\n"):
            trailing_newline_present += 1
        else:
            trailing_newline_absent += 1

        # Trailing whitespace
        if any(re.search(r"\s+$", line) for line in lines_for_indent if line.strip()):
            files_with_trailing_ws += 1

    # Consensus indentation
    units = Counter(v["unit"] for v in indent_votes if v["unit"] != "unknown")
    sizes = Counter(v["size"] for v in indent_votes if v["unit"] != "unknown" and v["size"] > 0)
    consensus_unit = units.most_common(1)[0][0] if units else "spaces"
    consensus_size = sizes.most_common(1)[0][0] if sizes else 4

    indentation = {
        "unit": consensus_unit,
        "size": consensus_size,
        "tab_files": tab_files[:10],
        "mixed_files": mixed_files[:10],
    }

    line_length = _measure_line_lengths(all_line_lengths)

    # Blank lines
    if lang == "python":
        blank_lines = _measure_blank_lines_python(files)
    else:
        blank_lines = _measure_blank_lines_generic(files, lang)

    return {
        "indentation": indentation,
        "line_length": line_length,
        "blank_lines": blank_lines,
        "trailing_newline": {
            "present": trailing_newline_present,
            "absent": trailing_newline_absent,
        },
        "trailing_whitespace": {
            "files_with_trailing_ws": files_with_trailing_ws,
        },
    }


def measure(repo_path: str, lang_filter: str | None = None) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "measure"}

    by_lang = _collect_files(repo, lang_filter)
    result: dict = {}

    for lang, files in by_lang.items():
        if not files:
            continue
        try:
            result[lang] = _measure_lang(lang, files)
        except Exception as exc:
            result[lang] = {"error": str(exc)}

    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="Path to repository")
    parser.add_argument("--lang", help="Filter to a single language")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output")
    args = parser.parse_args(argv)

    try:
        result = measure(args.repo, args.lang)
    except Exception as exc:
        result = {"error": str(exc), "script": "measure"}

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
