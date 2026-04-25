#!/usr/bin/env python3
"""Map test files to source files. Characterize test structure and framework usage.

Identifies what a representative test looks like so an agent can follow the same pattern.

Usage:
    python scripts/tests.py <repo>
    python scripts/tests.py <repo> --pretty
"""

import ast
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from _common import should_skip_dir

FRAMEWORK_DETECTION_SAMPLE = 5
NAMING_DETECTION_SAMPLE = 10
MAX_FIXTURE_NAMES = 20

MAKEFILE_NAMES = ["Makefile", "makefile", "GNUmakefile"]

FRAMEWORK_RUN_DEFAULTS = {
    "pytest":   "pytest",
    "unittest": "python -m unittest discover",
    "jest":     "jest",
    "vitest":   "vitest",
    "mocha":    "mocha",
}

TOP_LEVEL_TEST_DIRS = {"tests", "test", "__tests__", "spec"}

SOURCE_ROOT_CANDIDATES = ["src", "lib", "pkg"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _most_common(lst: list[str]) -> str | None:
    if not lst:
        return None
    return Counter(lst).most_common(1)[0][0]


def _count_lines(path: Path) -> int:
    try:
        with open(path, "rb") as f:
            return f.read().count(b"\n")
    except Exception:
        return 0


def _is_fixture_decorator(decorator: ast.expr) -> bool:
    """Return True if an AST decorator node is a pytest fixture."""
    dec_str = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
    if "fixture" in dec_str:
        return True
    if isinstance(decorator, ast.Attribute) and decorator.attr == "fixture":
        return True
    if isinstance(decorator, ast.Name) and decorator.id == "fixture":
        return True
    return False


def _ts_framework_from_deps(test_cmd: str, dev_deps: dict) -> str | None:
    """Return the TS test framework name inferred from scripts and devDependencies."""
    for name in ("jest", "vitest", "mocha"):
        if name in test_cmd or name in dev_deps:
            return name
    return None


def _mirrors_source_tree(
    test_dirs: Counter, most_common_dir: str, repo: Path, src_root: str
) -> bool:
    """Return True if the test directory structure mirrors a source root."""
    for d in test_dirs:
        if d.startswith(most_common_dir):
            sub = d[len(most_common_dir):].lstrip(os.sep)
            if sub and (repo / src_root / sub).exists():
                return True
    return False


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def _collect_python_files(repo: Path) -> tuple[list[Path], list[Path]]:
    test_files: list[Path] = []
    source_files: list[Path] = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            fpath = Path(dirpath) / fn
            stem = Path(fn).stem
            if (
                stem.startswith("test_")
                or stem.endswith("_test")
                or "tests" in Path(dirpath).parts
                or "test" in Path(dirpath).parts
            ):
                test_files.append(fpath)
            else:
                source_files.append(fpath)

    return test_files, source_files


def _collect_ts_files(repo: Path) -> tuple[list[Path], list[Path]]:
    test_files: list[Path] = []
    source_files: list[Path] = []
    exts = {".ts", ".tsx", ".js", ".jsx", ".mjs"}

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for fn in files:
            if Path(fn).suffix.lower() not in exts:
                continue
            fpath = Path(dirpath) / fn
            stem = Path(fn).stem
            if ".test." in fn or ".spec." in fn or stem.endswith("-test") or stem.endswith("-spec"):
                test_files.append(fpath)
            elif "__tests__" in Path(dirpath).parts or "tests" in Path(dirpath).parts:
                test_files.append(fpath)
            else:
                source_files.append(fpath)

    return test_files, source_files


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------

def _detect_python_framework(repo: Path, test_files: list[Path]) -> str:
    pyproject = repo / "pyproject.toml"
    if pyproject.exists() and "[tool.pytest" in pyproject.read_text(errors="ignore"):
        return "pytest"

    if (repo / "pytest.ini").exists() or (repo / "conftest.py").exists():
        return "pytest"

    setup_cfg = repo / "setup.cfg"
    if setup_cfg.exists() and "[tool:pytest]" in setup_cfg.read_text(errors="ignore"):
        return "pytest"

    for fpath in test_files[:FRAMEWORK_DETECTION_SAMPLE]:
        try:
            content = fpath.read_text(errors="ignore")
            if "import pytest" in content or "from pytest" in content:
                return "pytest"
            if "import unittest" in content:
                return "unittest"
        except Exception:
            continue

    return "pytest"


def _detect_ts_framework(repo: Path) -> tuple[str, str]:
    """Return (framework, run_command)."""
    pkg = repo / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(errors="ignore"))
        except Exception:
            data = {}

        scripts = data.get("scripts", {})
        test_cmd = scripts.get("test", "")
        dev_deps = data.get("devDependencies", {})

        name = _ts_framework_from_deps(test_cmd, dev_deps)
        if name:
            return name, test_cmd or name

    return "jest", "jest"


def _extract_run_command(repo: Path, framework: str) -> str:
    """Check Makefile for test targets first, fall back to framework default."""
    for makefile in MAKEFILE_NAMES:
        mk = repo / makefile
        if not mk.exists():
            continue
        content = mk.read_text(errors="ignore")
        m = re.search(r"^(?:test|test-all|tests)\s*:.*\n\t+(.+)", content, re.MULTILINE)
        if m:
            return m.group(1).strip()

    return FRAMEWORK_RUN_DEFAULTS.get(framework, framework)


# ---------------------------------------------------------------------------
# Test mapping
# ---------------------------------------------------------------------------

def _map_python_tests(
    source_files: list[Path], test_files: list[Path], repo: Path
) -> dict:
    mapped: list[dict] = []
    untested: list[str] = []
    unmatched_tests: list[str] = []

    source_by_stem: dict[str, Path] = {sf.stem.lower(): sf for sf in source_files}
    matched_tests: set[str] = set()

    for tf in test_files:
        stem = tf.stem.lower()
        candidate = re.sub(r"^test_|_test$", "", stem)
        match = source_by_stem.get(candidate) or source_by_stem.get(stem)

        if match:
            matched_tests.add(str(match.relative_to(repo)))
            mapped.append({
                "source": str(match.relative_to(repo)),
                "test":   str(tf.relative_to(repo)),
            })
        else:
            unmatched_tests.append(str(tf.relative_to(repo)))

    for sf in source_files:
        rel = str(sf.relative_to(repo))
        if rel not in matched_tests:
            untested.append(rel)

    return {
        "mapped": mapped,
        "untested_source_files": untested,
        "test_files_without_source_match": unmatched_tests,
    }


# ---------------------------------------------------------------------------
# Structure + naming + fixtures
# ---------------------------------------------------------------------------

def _detect_test_structure(repo: Path, test_files: list[Path]) -> dict:
    if not test_files:
        return {"location": "unknown", "test_dir": None, "mirrors_source": False}

    test_dirs = Counter(str(f.parent.relative_to(repo)) for f in test_files)
    top_test_dirs = [d for d in test_dirs if d.split(os.sep)[0] in TOP_LEVEL_TEST_DIRS]

    if not top_test_dirs:
        return {"location": "colocated", "test_dir": None, "mirrors_source": False}

    most_common_dir = Counter(d.split(os.sep)[0] for d in test_dirs).most_common(1)[0][0]
    test_dir = most_common_dir + "/"

    src_root = next((c for c in SOURCE_ROOT_CANDIDATES if (repo / c).exists()), None)
    mirrors = _mirrors_source_tree(test_dirs, most_common_dir, repo, src_root) if src_root else False

    return {
        "location": "separate_dirs",
        "test_dir": test_dir,
        "mirrors_source": mirrors,
    }


def _detect_naming_patterns(test_files: list[Path]) -> dict:
    func_patterns: list[str] = []
    class_patterns: list[str] = []
    file_patterns: list[str] = []

    for fpath in test_files[:NAMING_DETECTION_SAMPLE]:
        stem = fpath.stem
        if stem.startswith("test_"):
            file_patterns.append("test_<module>.py")
        elif stem.endswith("_test"):
            file_patterns.append("<module>_test.py")
        elif ".test." in fpath.name:
            file_patterns.append("<module>.test.ts")
        elif ".spec." in fpath.name:
            file_patterns.append("<module>.spec.ts")

        try:
            source = fpath.read_text(errors="ignore")
        except Exception:
            continue

        if re.search(r"def (test_\w+)\s*\(", source):
            func_patterns.append("test_<description>")
        if re.search(r"(?:it|test)\s*\(\s*['\"]([^'\"]+)['\"]", source):
            func_patterns.append("it('<description>')")

        if re.search(r"class (Test\w+)", source):
            class_patterns.append("Test<Subject>")
        if re.search(r"class (\w+Test)", source):
            class_patterns.append("<Subject>Test")
        if re.search(r"describe\s*\(\s*['\"]([^'\"]+)['\"]", source):
            class_patterns.append("describe('<Subject>')")

    return {
        "file_pattern":     _most_common(file_patterns),
        "function_pattern": _most_common(func_patterns),
        "class_pattern":    _most_common(class_patterns),
    }


def _find_conftest_files(repo: Path) -> list[str]:
    """Walk repo and return repo-relative paths of all conftest.py files."""
    found = []
    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for fn in files:
            if fn == "conftest.py":
                found.append(str((Path(dirpath) / fn).relative_to(repo)))
    return found


def _extract_fixtures_from_conftest(repo: Path, conftest_paths: list[str]) -> list[str]:
    """Parse each conftest.py and return the names of all fixture functions."""
    fixture_names: list[str] = []
    for conftest_path in conftest_paths:
        try:
            source = (repo / conftest_path).read_text(errors="ignore")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if any(_is_fixture_decorator(d) for d in node.decorator_list):
                        fixture_names.append(node.name)
        except Exception:
            continue
    return fixture_names


def _detect_python_fixtures(repo: Path, test_files: list[Path]) -> dict:
    conftest_files = _find_conftest_files(repo)
    fixture_names = _extract_fixtures_from_conftest(repo, conftest_files)

    return {
        "uses_conftest": bool(conftest_files),
        "conftest_locations": conftest_files,
        "fixture_names": fixture_names[:MAX_FIXTURE_NAMES],
    }


def _pick_representative(test_files: list[Path]) -> str | None:
    if not test_files:
        return None
    sizes = sorted([(f, _count_lines(f)) for f in test_files], key=lambda x: x[1])
    return str(sizes[len(sizes) // 2][0])


# ---------------------------------------------------------------------------
# Per-language analysis
# ---------------------------------------------------------------------------

def _analyze_python(repo: Path) -> dict | None:
    test_files, source_files = _collect_python_files(repo)
    if not test_files and not source_files:
        return None

    framework  = _detect_python_framework(repo, test_files)
    run_cmd    = _extract_run_command(repo, framework)
    coverage   = _map_python_tests(source_files, test_files, repo)
    structure  = _detect_test_structure(repo, test_files)
    naming     = _detect_naming_patterns(test_files)
    fixtures   = _detect_python_fixtures(repo, test_files)
    rep_test   = _pick_representative(test_files)

    return {
        "framework":          framework,
        "run_command":        run_cmd,
        "test_files":         len(test_files),
        "source_files":       len(source_files),
        "coverage_shape":     coverage,
        "structure":          structure,
        "naming":             naming,
        "fixtures":           fixtures,
        "representative_test": str(Path(rep_test).relative_to(repo)) if rep_test else None,
    }


def _analyze_typescript(repo: Path) -> dict | None:
    test_files, source_files = _collect_ts_files(repo)
    if not test_files and not source_files:
        return None

    framework, run_cmd = _detect_ts_framework(repo)
    run_cmd   = _extract_run_command(repo, framework) or run_cmd
    structure = _detect_test_structure(repo, test_files)
    naming    = _detect_naming_patterns(test_files)
    rep_test  = _pick_representative(test_files)

    return {
        "framework":          framework,
        "run_command":        run_cmd,
        "test_files":         len(test_files),
        "source_files":       len(source_files),
        "structure":          structure,
        "naming":             naming,
        "representative_test": str(Path(rep_test).relative_to(repo)) if rep_test else None,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def analyze_tests(repo_path: str) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "tests"}

    result: dict = {}

    try:
        py = _analyze_python(repo)
        if py:
            result["python"] = py
    except Exception as exc:
        result["python"] = {"error": str(exc)}

    try:
        ts = _analyze_typescript(repo)
        if ts:
            result["typescript"] = ts
    except Exception as exc:
        result["typescript"] = {"error": str(exc)}

    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="Path to repository")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output")
    args = parser.parse_args(argv)

    try:
        result = analyze_tests(args.repo)
    except Exception as exc:
        result = {"error": str(exc), "script": "tests"}

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
