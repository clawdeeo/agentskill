#!/usr/bin/env python3
"""Build the internal import graph. Identify coupling, circular dependencies, monorepo boundaries.

Traces only internal imports — external (stdlib, third-party) are ignored.

Usage:
    python scripts/graph.py <repo>
    python scripts/graph.py <repo> --lang python
    python scripts/graph.py <repo> --pretty
"""

import ast
import json
import os
import re
import sys
from pathlib import Path

from _common import SKIP_DIRS, should_skip_dir

MAX_EDGES = 200
MAX_CYCLES = 20
MAX_MOST_DEPENDED = 10
MIN_MONOREPO_SERVICES = 2

MONOREPO_BOUNDARY_DIRS = ["services", "packages", "apps", "modules"]


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def _collect_files(repo: Path, lang: str) -> list[Path]:
    ext_map = {
        "python":     [".py"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx", ".mjs"],
        "go":         [".go"],
    }
    exts = set(ext_map.get(lang, []))
    found = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for fn in files:
            if Path(fn).suffix.lower() in exts:
                found.append(Path(dirpath) / fn)

    return found


# ---------------------------------------------------------------------------
# Module name helpers
# ---------------------------------------------------------------------------

def _path_to_module(path: Path, repo: Path) -> str:
    rel = path.relative_to(repo)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = Path(parts[-1]).stem
    return ".".join(parts)


def _file_for_module(module: str, repo: Path) -> Path | None:
    parts = module.split(".")
    candidates = [
        repo / Path(*parts).with_suffix(".py"),
        repo / Path(*parts) / "__init__.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


# ---------------------------------------------------------------------------
# Import resolution (Python)
# ---------------------------------------------------------------------------

def _resolve_absolute_import(target: str, module_set: set[str]) -> str | None:
    """Return the internal module name for a bare `import X` statement, or None."""
    if target in module_set:
        return target
    prefix_match = next((m for m in module_set if target.startswith(m + ".")), None)
    if prefix_match:
        return prefix_match
    return None


def _resolve_relative_import(node: ast.ImportFrom, mod: str, module_set: set[str]) -> str | None:
    """Return the internal module name for a `from . import X` statement, or None."""
    if node.module is None:
        return None

    if node.level and node.level > 0:
        parts = mod.split(".")
        base_parts = parts[:max(0, len(parts) - node.level)]
        resolved = ".".join(base_parts + [node.module]) if node.module else ".".join(base_parts)
    else:
        resolved = node.module

    if resolved in module_set or any(resolved.startswith(m) for m in module_set):
        return resolved

    return None


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------

def _build_python_graph(files: list[Path], repo: Path) -> dict:
    modules = {_path_to_module(f, repo): f for f in files}
    module_set = set(modules.keys())
    edges: list[dict] = []
    parse_errors: list[str] = []
    adjacency: dict[str, list[str]] = {m: [] for m in module_set}

    for mod, fpath in modules.items():
        try:
            source = fpath.read_text(errors="ignore")
            tree = ast.parse(source)
        except Exception:
            parse_errors.append(str(fpath.relative_to(repo)))
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = _resolve_absolute_import(alias.name, module_set)
                    if resolved:
                        edges.append({"from": mod, "to": resolved, "line": node.lineno})
                        adjacency[mod].append(resolved)

            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_relative_import(node, mod, module_set)
                if resolved:
                    edges.append({"from": mod, "to": resolved, "line": node.lineno})
                    if resolved in adjacency:
                        adjacency[mod].append(resolved)

    return _graph_result(sorted(module_set), edges, adjacency, parse_errors)


def _build_ts_graph(files: list[Path], repo: Path) -> dict:
    import_re  = re.compile(r"""(?:import|from)\s+['"]([^'"]+)['"]""")
    require_re = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")

    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []

    file_stems = {str(f.relative_to(repo).with_suffix("")): f for f in files}

    for fpath in files:
        rel = str(fpath.relative_to(repo).with_suffix(""))
        adjacency.setdefault(rel, [])

        try:
            source = fpath.read_text(errors="ignore")
        except Exception:
            parse_errors.append(str(fpath.relative_to(repo)))
            continue

        for lineno, line in enumerate(source.splitlines(), 1):
            for pattern in (import_re, require_re):
                for m in pattern.finditer(line):
                    target = m.group(1)
                    if not target.startswith("."):
                        continue

                    resolved = (fpath.parent / target).resolve()
                    try:
                        rel_resolved = str(resolved.relative_to(repo))
                    except ValueError:
                        continue

                    rel_resolved = re.sub(r"\.(ts|tsx|js|jsx|mjs)$", "", rel_resolved)
                    if rel_resolved in file_stems:
                        edges.append({"from": rel, "to": rel_resolved, "line": lineno})
                        adjacency[rel].append(rel_resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _extract_go_imports(source: str) -> list[str]:
    """Return all import paths found in a Go source file."""
    import_block_re = re.compile(r'import\s*\(([^)]+)\)', re.DOTALL)
    single_import_re = re.compile(r'^import\s+"([^"]+)"')
    quoted_re = re.compile(r'"([^"]+)"')

    imports: list[str] = []

    for m in import_block_re.finditer(source):
        for im in quoted_re.findall(m.group(1)):
            imports.append(im)

    for line in source.splitlines():
        m = single_import_re.match(line.strip())
        if m:
            imports.append(m.group(1))

    return imports


def _build_go_graph(files: list[Path], repo: Path) -> dict:
    module_prefix = ""
    gomod = repo / "go.mod"
    if gomod.exists():
        for line in gomod.read_text(errors="ignore").splitlines():
            if line.startswith("module "):
                module_prefix = line.split()[1]
                break

    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        pkg = str(fpath.parent.relative_to(repo))
        adjacency.setdefault(pkg, [])

        try:
            source = fpath.read_text(errors="ignore")
        except Exception:
            parse_errors.append(rel)
            continue

        for imp in _extract_go_imports(source):
            if module_prefix and imp.startswith(module_prefix):
                internal_path = imp[len(module_prefix):].lstrip("/")
                edges.append({"from": pkg, "to": internal_path, "line": 0})
                adjacency[pkg].append(internal_path)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


# ---------------------------------------------------------------------------
# Graph analysis
# ---------------------------------------------------------------------------

def _compute_most_depended(adjacency: dict[str, list[str]]) -> list[dict]:
    dep_counts: dict[str, int] = {}
    for deps in adjacency.values():
        for d in deps:
            dep_counts[d] = dep_counts.get(d, 0) + 1

    return sorted(
        [{"module": m, "dependents": c} for m, c in dep_counts.items()],
        key=lambda x: -x["dependents"],
    )[:MAX_MOST_DEPENDED]


def _find_cycles(adjacency: dict[str, list[str]]) -> list[list[str]]:
    """DFS cycle detection. Returns list of cycles as ordered node lists."""
    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles: list[list[str]] = []
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])

        path.pop()
        rec_stack.discard(node)

    for node in list(adjacency.keys()):
        if node not in visited:
            dfs(node)

    return cycles


def _graph_result(
    modules: list[str],
    edges: list[dict],
    adjacency: dict[str, list[str]],
    parse_errors: list[str],
) -> dict:
    return {
        "modules": sorted(modules),
        "edges": edges[:MAX_EDGES],
        "boundary_violations": [],
        "circular_dependencies": _find_cycles(adjacency)[:MAX_CYCLES],
        "most_depended_on": _compute_most_depended(adjacency),
        "parse_errors": parse_errors,
    }


def _detect_monorepo_boundaries(repo: Path) -> dict:
    for bd in MONOREPO_BOUNDARY_DIRS:
        bd_path = repo / bd
        if not bd_path.is_dir():
            continue

        services = [
            d.name for d in bd_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        if len(services) >= MIN_MONOREPO_SERVICES:
            return {
                "detected": True,
                "boundary_dir": bd,
                "services": services,
                "cross_service_imports": [],
            }

    return {"detected": False, "services": [], "cross_service_imports": []}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_graph(repo_path: str, lang_filter: str | None = None) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "graph"}

    result: dict = {}
    langs = [lang_filter] if lang_filter else ["python", "typescript", "javascript", "go"]

    for lang in langs:
        files = _collect_files(repo, lang)
        if not files:
            continue
        try:
            if lang == "python":
                result[lang] = _build_python_graph(files, repo)
            elif lang in ("typescript", "javascript"):
                result[lang] = _build_ts_graph(files, repo)
            elif lang == "go":
                result[lang] = _build_go_graph(files, repo)
        except Exception as exc:
            result[lang] = {"error": str(exc)}

    result["monorepo_boundaries"] = _detect_monorepo_boundaries(repo)
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
        result = build_graph(args.repo, args.lang)
    except Exception as exc:
        result = {"error": str(exc), "script": "graph"}

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
