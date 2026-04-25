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

SKIP_DIRS: set[str] = {
    "node_modules", "__pycache__", "dist", "build", "out",
    "target", "vendor", "third_party", ".eggs", "site-packages",
    "venv", ".venv", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov",
}


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def _count_lines(path: Path) -> int:
    try:
        with open(path, "rb") as f:
            return f.read().count(b"\n")
    except Exception:
        return 0


def _collect_python_files(repo: Path) -> tuple[list[Path], list[Path]]:
    test_files: list[Path] = []
    source_files: list[Path] = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
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
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
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


def _detect_python_framework(repo: Path, test_files: list[Path]) -> str:
    # Check pyproject.toml
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(errors="ignore")
        if "[tool.pytest" in content:
            return "pytest"

    # Check pytest.ini
    if (repo / "pytest.ini").exists() or (repo / "conftest.py").exists():
        return "pytest"

    # Check setup.cfg
    setup_cfg = repo / "setup.cfg"
    if setup_cfg.exists() and "[tool:pytest]" in setup_cfg.read_text(errors="ignore"):
        return "pytest"

    # Check imports in test files
    for fpath in test_files[:5]:
        try:
            content = fpath.read_text(errors="ignore")
            if "import pytest" in content or "from pytest" in content:
                return "pytest"
            if "import unittest" in content:
                return "unittest"
        except Exception:
            continue

    return "pytest"  # default


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

        if "jest" in test_cmd or "jest" in data.get("devDependencies", {}):
            return "jest", test_cmd or "jest"
        if "vitest" in test_cmd or "vitest" in data.get("devDependencies", {}):
            return "vitest", test_cmd or "vitest"
        if "mocha" in test_cmd or "mocha" in data.get("devDependencies", {}):
            return "mocha", test_cmd or "mocha"

    return "jest", "jest"


def _extract_run_command(repo: Path, framework: str) -> str:
    """Check Makefile for test targets first."""
    for makefile in ["Makefile", "makefile", "GNUmakefile"]:
        mk = repo / makefile
        if not mk.exists():
            continue
        content = mk.read_text(errors="ignore")
        # Look for test: or test-all: targets
        m = re.search(r"^(?:test|test-all|tests)\s*:.*\n\t+(.+)", content, re.MULTILINE)
        if m:
            return m.group(1).strip()

    defaults = {
        "pytest": "pytest",
        "unittest": "python -m unittest discover",
        "jest": "jest",
        "vitest": "vitest",
        "mocha": "mocha",
    }
    return defaults.get(framework, framework)


def _map_python_tests(
    source_files: list[Path], test_files: list[Path], repo: Path
) -> dict:
    mapped: list[dict] = []
    untested: list[str] = []
    unmatched_tests: list[str] = []

    source_by_stem: dict[str, Path] = {}
    for sf in source_files:
        source_by_stem[sf.stem.lower()] = sf

    matched_tests: set[str] = set()

    for tf in test_files:
        stem = tf.stem.lower()
        # Strip test_ prefix or _test suffix
        candidate = re.sub(r"^test_|_test$", "", stem)
        match = source_by_stem.get(candidate) or source_by_stem.get(stem)

        if match:
            matched_tests.add(str(match.relative_to(repo)))
            mapped.append({
                "source": str(match.relative_to(repo)),
                "test": str(tf.relative_to(repo)),
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


def _detect_test_structure(repo: Path, test_files: list[Path]) -> dict:
    if not test_files:
        return {"location": "unknown", "test_dir": None, "mirrors_source": False}

    test_dirs = Counter(
        str(f.parent.relative_to(repo)) for f in test_files
    )
    top_test_dirs = [d for d in test_dirs if d.split(os.sep)[0] in ("tests", "test", "__tests__", "spec")]

    if top_test_dirs:
        most_common_dir = Counter(
            d.split(os.sep)[0] for d in test_dirs
        ).most_common(1)[0][0]
        test_dir = most_common_dir + "/"

        # Check if mirrors source
        src_root = None
        for candidate in ["src", "lib", "pkg"]:
            if (repo / candidate).exists():
                src_root = candidate
                break

        mirrors = False
        if src_root:
            for d in test_dirs:
                if d.startswith(most_common_dir):
                    sub = d[len(most_common_dir):].lstrip(os.sep)
                    if sub and (repo / src_root / sub).exists():
                        mirrors = True
                        break

        return {
            "location": "separate_dirs",
            "test_dir": test_dir,
            "mirrors_source": mirrors,
        }

    # Colocated
    return {"location": "colocated", "test_dir": None, "mirrors_source": False}


def _detect_naming_patterns(test_files: list[Path]) -> dict:
    func_patterns: list[str] = []
    class_patterns: list[str] = []
    file_patterns: list[str] = []

    for fpath in test_files[:10]:
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

        # Function patterns
        for m in re.finditer(r"def (test_\w+)\s*\(", source):
            func_patterns.append("test_<description>")
            break
        for m in re.finditer(r"(?:it|test)\s*\(\s*['\"]([^'\"]+)['\"]", source):
            func_patterns.append("it('<description>')")
            break

        # Class patterns
        for m in re.finditer(r"class (Test\w+)", source):
            class_patterns.append("Test<Subject>")
            break
        for m in re.finditer(r"class (\w+Test)", source):
            class_patterns.append("<Subject>Test")
            break
        for m in re.finditer(r"describe\s*\(\s*['\"]([^'\"]+)['\"]", source):
            class_patterns.append("describe('<Subject>')")
            break

    def _most_common(lst: list[str]) -> str | None:
        if not lst:
            return None
        return Counter(lst).most_common(1)[0][0]

    return {
        "file_pattern": _most_common(file_patterns),
        "function_pattern": _most_common(func_patterns),
        "class_pattern": _most_common(class_patterns),
    }


def _detect_python_fixtures(repo: Path, test_files: list[Path]) -> dict:
    conftest_files = []
    fixture_names: list[str] = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fn in files:
            if fn == "conftest.py":
                conftest_files.append(str((Path(dirpath) / fn).relative_to(repo)))

    for conftest_path in conftest_files:
        try:
            source = (repo / conftest_path).read_text(errors="ignore")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        dec_str = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                        if "fixture" in dec_str or (
                            isinstance(decorator, ast.Attribute)
                            and decorator.attr == "fixture"
                        ) or (
                            isinstance(decorator, ast.Name)
                            and decorator.id == "fixture"
                        ):
                            fixture_names.append(node.name)
                            break
        except Exception:
            continue

    return {
        "uses_conftest": bool(conftest_files),
        "conftest_locations": conftest_files,
        "fixture_names": fixture_names[:20],
    }


def _pick_representative(test_files: list[Path]) -> str | None:
    if not test_files:
        return None
    sizes = [(f, _count_lines(f)) for f in test_files]
    sizes.sort(key=lambda x: x[1])
    mid = sizes[len(sizes) // 2]
    return str(mid[0])


def analyze_tests(repo_path: str) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "tests"}

    result: dict = {}

    # --- Python ---
    py_test_files, py_source_files = _collect_python_files(repo)
    if py_test_files or py_source_files:
        try:
            framework = _detect_python_framework(repo, py_test_files)
            run_cmd = _extract_run_command(repo, framework)
            coverage_shape = _map_python_tests(py_source_files, py_test_files, repo)
            structure = _detect_test_structure(repo, py_test_files)
            naming = _detect_naming_patterns(py_test_files)
            fixtures = _detect_python_fixtures(repo, py_test_files)
            rep_test = _pick_representative(py_test_files)

            result["python"] = {
                "framework": framework,
                "run_command": run_cmd,
                "test_files": len(py_test_files),
                "source_files": len(py_source_files),
                "coverage_shape": coverage_shape,
                "structure": structure,
                "naming": naming,
                "fixtures": fixtures,
                "representative_test": str(
                    Path(rep_test).relative_to(repo)
                ) if rep_test else None,
            }
        except Exception as exc:
            result["python"] = {"error": str(exc)}

    # --- TypeScript / JavaScript ---
    ts_test_files, ts_source_files = _collect_ts_files(repo)
    if ts_test_files or ts_source_files:
        try:
            framework, run_cmd = _detect_ts_framework(repo)
            run_cmd = _extract_run_command(repo, framework) or run_cmd
            structure = _detect_test_structure(repo, ts_test_files)
            naming = _detect_naming_patterns(ts_test_files)
            rep_test = _pick_representative(ts_test_files)

            result["typescript"] = {
                "framework": framework,
                "run_command": run_cmd,
                "test_files": len(ts_test_files),
                "source_files": len(ts_source_files),
                "structure": structure,
                "naming": naming,
                "representative_test": str(
                    Path(rep_test).relative_to(repo)
                ) if rep_test else None,
            }
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
