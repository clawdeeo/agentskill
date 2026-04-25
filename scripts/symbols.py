#!/usr/bin/env python3
"""Extract all symbol names from the codebase. Cluster by naming pattern.

Detects codebase-specific conventions beyond standard language defaults:
recurring prefixes, suffixes, and naming idioms that appear 5+ times.

Usage:
    python scripts/symbols.py <repo>
    python scripts/symbols.py <repo> --lang python
    python scripts/symbols.py <repo> --pretty
"""

import ast
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

SKIP_DIRS: set[str] = {
    "node_modules", "__pycache__", "dist", "build", "out",
    "target", "vendor", "third_party", ".eggs", "site-packages",
    "venv", ".venv", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov",
}


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def _collect_files(repo: Path, exts: list[str]) -> list[Path]:
    found = []
    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fn in files:
            if Path(fn).suffix.lower() in exts:
                found.append(Path(dirpath) / fn)
    return found


def _classify(name: str) -> str:
    if name.startswith("__") and name.endswith("__"):
        return "dunder"
    if name.startswith("_"):
        return "private"
    if name == name.upper() and "_" in name:
        return "SCREAMING_SNAKE_CASE"
    if "_" in name:
        return "snake_case"
    if name and name[0].isupper():
        return "PascalCase"
    if name and name[0].islower() and any(c.isupper() for c in name[1:]):
        return "camelCase"
    return "other"


def _pattern_summary(names: list[str]) -> dict:
    if not names:
        return {"total": 0, "patterns": {}, "codebase_specific": []}

    total = len(names)
    counts = Counter(_classify(n) for n in names)
    patterns = {
        k: {"count": v, "pct": round(v / total * 100, 1)}
        for k, v in sorted(counts.items(), key=lambda x: -x[1])
    }

    # Codebase-specific affix detection
    codebase_specific = _find_affixes(names)

    return {"total": total, "patterns": patterns, "codebase_specific": codebase_specific}


def _find_affixes(names: list[str], min_count: int = 5, min_len: int = 2) -> list[dict]:
    """Find recurring prefixes and suffixes appearing in 5+ names."""
    prefix_counts: Counter = Counter()
    suffix_counts: Counter = Counter()
    prefix_examples: dict[str, list[str]] = {}
    suffix_examples: dict[str, list[str]] = {}

    for name in names:
        # Skip very short names and dunders
        if len(name) < 4 or (name.startswith("__") and name.endswith("__")):
            continue
        clean = name.lstrip("_")

        # Prefixes of length 2–8
        for length in range(min_len, min(9, len(clean))):
            prefix = clean[:length]
            if prefix.isalpha() or ("_" in prefix and prefix.endswith("_")):
                prefix_counts[prefix] += 1
                prefix_examples.setdefault(prefix, [])
                if len(prefix_examples[prefix]) < 3:
                    prefix_examples[prefix].append(name)

        # Suffixes of length 2–8
        for length in range(min_len, min(9, len(clean))):
            suffix = clean[-length:]
            if suffix.isalpha() or ("_" in suffix and suffix.startswith("_")):
                suffix_counts[suffix] += 1
                suffix_examples.setdefault(suffix, [])
                if len(suffix_examples[suffix]) < 3:
                    suffix_examples[suffix].append(name)

    results = []

    # Filter: must appear 5+ times, must not be a trivially common English substring
    SKIP_AFFIXES = {
        "er", "ed", "ing", "ion", "al", "tion", "le", "or", "is", "at",
        "get", "set", "has", "is_", "_is", "on", "re", "un", "de",
    }

    for prefix, count in prefix_counts.most_common(30):
        if count >= min_count and prefix.lower() not in SKIP_AFFIXES and len(prefix) >= min_len:
            results.append({
                "pattern": f"{prefix}_ prefix" if not prefix.endswith("_") else f"{prefix} prefix",
                "count": count,
                "examples": prefix_examples.get(prefix, []),
            })

    for suffix, count in suffix_counts.most_common(30):
        if count >= min_count and suffix.lower() not in SKIP_AFFIXES and len(suffix) >= min_len:
            results.append({
                "pattern": f"_{suffix} suffix" if not suffix.startswith("_") else f"{suffix} suffix",
                "count": count,
                "examples": suffix_examples.get(suffix, []),
            })

    # Deduplicate and limit
    seen = set()
    deduped = []
    for r in sorted(results, key=lambda x: -x["count"]):
        key = r["pattern"]
        if key not in seen:
            seen.add(key)
            deduped.append(r)
        if len(deduped) >= 10:
            break

    return deduped


def _extract_python(files: list[Path]) -> dict:
    functions: list[str] = []
    classes: list[str] = []
    constants: list[str] = []
    private_single: list[str] = []
    private_double: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)
        try:
            source = fpath.read_text(errors="ignore")
            tree = ast.parse(source)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                functions.append(name)
                if name.startswith("__") and name.endswith("__"):
                    pass  # dunder, already in functions
                elif name.startswith("__"):
                    private_double.append(name)
                elif name.startswith("_"):
                    private_single.append(name)

            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

            elif (
                isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and node.col_offset == 0
            ):
                target = node.targets[0].id
                if target == target.upper() and "_" in target:
                    constants.append(target)

    return {
        "functions": _pattern_summary(functions),
        "classes": _pattern_summary(classes),
        "constants": _pattern_summary(constants),
        "private_members": {
            "single_underscore": len(private_single),
            "double_underscore": len(private_double),
            "examples": (private_single + private_double)[:10],
        },
        "files": _pattern_summary(file_names),
    }


def _extract_ts(files: list[Path], lang: str) -> dict:
    func_re = re.compile(
        r"(?:^|\s)(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)"
        r"|(?:^|\s)const\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    )
    class_re = re.compile(r"(?:^|\s)(?:export\s+)?(?:abstract\s+)?class\s+(\w+)")
    iface_re = re.compile(r"(?:^|\s)(?:export\s+)?interface\s+(\w+)")
    type_re  = re.compile(r"(?:^|\s)(?:export\s+)?type\s+(\w+)\s*=")
    const_re = re.compile(r"^(?:export\s+)?const\s+([A-Z_][A-Z0-9_]+)\s*=", re.MULTILINE)

    functions: list[str] = []
    classes: list[str] = []
    constants: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem.replace(".test", "").replace(".spec", ""))
        try:
            source = fpath.read_text(errors="ignore")
        except Exception:
            continue

        for m in func_re.finditer(source):
            name = m.group(1) or m.group(2)
            if name:
                functions.append(name)
        for m in class_re.finditer(source):
            classes.append(m.group(1))
        for m in iface_re.finditer(source):
            classes.append(m.group(1))
        for m in type_re.finditer(source):
            classes.append(m.group(1))
        for m in const_re.finditer(source):
            constants.append(m.group(1))

    return {
        "functions": _pattern_summary(functions),
        "classes": _pattern_summary(classes),
        "constants": _pattern_summary(constants),
        "files": _pattern_summary(file_names),
    }


def _extract_go(files: list[Path]) -> dict:
    func_re    = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(")
    type_re    = re.compile(r"^type\s+(\w+)\s+(?:struct|interface)")
    const_re   = re.compile(r"^\s+(\w+)\s*(?:=|[A-Z])")
    var_re     = re.compile(r"^var\s+(\w+)\s+")

    functions: list[str] = []
    classes: list[str] = []
    constants: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)
        try:
            lines = fpath.read_text(errors="ignore").splitlines()
        except Exception:
            continue

        in_const = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("const ("):
                in_const = True
                continue
            if in_const and stripped == ")":
                in_const = False
                continue
            if in_const:
                m = const_re.match(line)
                if m:
                    constants.append(m.group(1))

            m = func_re.match(line)
            if m:
                functions.append(m.group(1))
            m = type_re.match(line)
            if m:
                classes.append(m.group(1))
            m = var_re.match(line)
            if m and m.group(1)[0].isupper():
                constants.append(m.group(1))

    return {
        "functions": _pattern_summary(functions),
        "types": _pattern_summary(classes),
        "constants": _pattern_summary(constants),
        "files": _pattern_summary(file_names),
    }


def extract_symbols(repo_path: str, lang_filter: str | None = None) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "symbols"}

    result: dict = {}

    def _run(lang: str, exts: list[str], extractor):
        files = _collect_files(repo, exts)
        if not files:
            return
        try:
            result[lang] = extractor(files)
        except Exception as exc:
            result[lang] = {"error": str(exc)}

    if not lang_filter or lang_filter == "python":
        _run("python", [".py"], _extract_python)

    if not lang_filter or lang_filter in ("typescript", "javascript"):
        lang = lang_filter or "typescript"
        _run(lang, [".ts", ".tsx", ".js", ".jsx", ".mjs"],
             lambda files: _extract_ts(files, lang))

    if not lang_filter or lang_filter == "go":
        _run("go", [".go"], _extract_go)

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
        result = extract_symbols(args.repo, args.lang)
    except Exception as exc:
        result = {"error": str(exc), "script": "symbols"}

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
