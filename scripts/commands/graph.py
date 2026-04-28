#!/usr/bin/env python3
"""Build the internal import graph. Identify coupling, circular dependencies, monorepo boundaries.

Traces only internal imports — external (stdlib, third-party) are ignored.

Usage:
    python scripts/graph.py <repo>
    python scripts/graph.py <repo> --lang python
    python scripts/graph.py <repo> --pretty
"""

import ast
import os
import re
import sys
from pathlib import Path

from common.constants import should_skip_dir
from common.fs import read_text, validate_repo
from lib.output import run_and_output

MAX_EDGES = 200
MAX_CYCLES = 20
MAX_MOST_DEPENDED = 10
MIN_MONOREPO_SERVICES = 2

MONOREPO_BOUNDARY_DIRS = ["services", "packages", "apps", "modules"]


def _collect_files(repo: Path, lang: str) -> list[Path]:
    ext_map = {
        "python": [".py"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx", ".mjs", ".cjs"],
        "go": [".go"],
        "rust": [".rs"],
    }

    exts = set(ext_map.get(lang, []))
    found = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for fn in files:
            if Path(fn).suffix.lower() in exts:
                found.append(Path(dirpath) / fn)

    return found


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


def _resolve_absolute_import(target: str, module_set: set[str]) -> str | None:
    """Return the internal module name for a bare `import X` statement, or None."""
    if target in module_set:
        return target

    prefix_match = next((m for m in module_set if target.startswith(m + ".")), None)

    if prefix_match:
        return prefix_match

    return None


def _resolve_relative_import(
    node: ast.ImportFrom, mod: str, module_set: set[str]
) -> str | None:
    """Return the internal module name for a `from . import X` statement, or None."""
    if node.module is None:
        return None

    if node.level and node.level > 0:
        parts = mod.split(".")
        base_parts = parts[: max(0, len(parts) - node.level)]

        resolved = (
            ".".join(base_parts + [node.module])
            if node.module
            else ".".join(base_parts)
        )
    else:
        resolved = node.module

    if resolved in module_set or any(resolved.startswith(m) for m in module_set):
        return resolved

    return None


def _build_python_graph(files: list[Path], repo: Path) -> dict:
    modules = {_path_to_module(f, repo): f for f in files}
    module_set = set(modules.keys())
    edges: list[dict] = []
    parse_errors: list[str] = []
    adjacency: dict[str, list[str]] = {m: [] for m in module_set}

    for mod, fpath in modules.items():
        try:
            source = read_text(fpath)
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


def _strip_js_ts_comments(content: str) -> str:
    content = re.sub(r"//.*", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    return content


def _resolve_js_ts_import(
    importer: Path, specifier: str, repo: Path, file_stems: set[str]
) -> str | None:
    if not specifier.startswith("./") and not specifier.startswith("../"):
        return None

    base = importer.parent / specifier

    candidates = [
        base,
        base.with_suffix(".ts"),
        base.with_suffix(".tsx"),
        base.with_suffix(".js"),
        base.with_suffix(".jsx"),
        base.with_suffix(".mjs"),
        base.with_suffix(".cjs"),
        base / "index.ts",
        base / "index.tsx",
        base / "index.js",
        base / "index.jsx",
    ]

    for c in candidates:
        try:
            rel = str(c.relative_to(repo))
        except ValueError:
            continue

        if rel in file_stems:
            return rel

    return None


def _extract_js_ts_imports(content: str) -> list[tuple[str, int]]:
    content = _strip_js_ts_comments(content)
    results: list[tuple[str, int]] = []

    es_import_re = re.compile(
        r"(?:^|\s)import\s+(?:(?:\{[^}]+\}|[^'\"]+)\s+from\s+)?['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )

    reexport_re = re.compile(
        r"(?:^|\s)export\s+(?:\{[^}]+\}|\*\s+)?\s*from\s+['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )

    require_re = re.compile(
        r"(?:^|\s)require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        re.MULTILINE,
    )

    for lineno, line in enumerate(content.splitlines(), 1):
        for pattern in (es_import_re, reexport_re, require_re):
            for m in pattern.finditer(line):
                spec = m.group(1)

                if spec.startswith("./") or spec.startswith("../"):
                    results.append((spec, lineno))

    return results


def _build_ts_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []

    file_stems = {str(f.relative_to(repo)): f for f in files}
    stem_set = set(file_stems.keys())

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for spec, lineno in _extract_js_ts_imports(source):
            resolved = _resolve_js_ts_import(fpath, spec, repo, stem_set)

            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "line": lineno})
                adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _strip_go_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _extract_go_imports(source: str) -> list[tuple[str, int]]:
    source = _strip_go_comments(source)
    results: list[tuple[str, int]] = []

    import_block_re = re.compile(r"import\s*\(([^)]+)\)", re.DOTALL)
    single_import_re = re.compile(r'^\s*import\s+"([^"]+)"')
    quoted_re = re.compile(r'"([^"]+)"')

    for lineno, line in enumerate(source.splitlines(), 1):
        single_match = single_import_re.match(line)
        if single_match:
            results.append((single_match.group(1), lineno))

    for m in import_block_re.finditer(source):
        block_start = source[: m.start()].count("\n") + 1
        for im in quoted_re.findall(m.group(1)):
            results.append((im, block_start))

    return results


def _detect_go_module(repo: Path) -> str:
    gomod = repo / "go.mod"
    if not gomod.exists():
        return ""
    for line in read_text(gomod).splitlines():
        if line.startswith("module "):
            return line.split()[1]
    return ""


def _detect_go_packages(files: list[Path], repo: Path) -> dict[str, str]:
    pkg_map: dict[str, str] = {}
    for fpath in files:
        pkg_dir = str(fpath.parent.relative_to(repo))
        if pkg_dir in pkg_map:
            continue
        try:
            source = read_text(fpath)
        except Exception:
            continue
        for line in source.splitlines():
            m = re.match(r"^package\s+(\w+)", line)
            if m:
                pkg_map[pkg_dir] = m.group(1)
                break
    return pkg_map


def _build_go_graph(files: list[Path], repo: Path) -> dict:
    module_prefix = _detect_go_module(repo)

    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        pkg = str(fpath.parent.relative_to(repo))
        adjacency.setdefault(pkg, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for imp, lineno in _extract_go_imports(source):
            if module_prefix and imp.startswith(module_prefix):
                internal_path = imp[len(module_prefix) :].lstrip("/")
                edges.append({"from": pkg, "to": internal_path, "line": lineno})
                adjacency[pkg].append(internal_path)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _strip_rust_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _extract_rust_mods_and_uses(source: str) -> list[tuple[str, int]]:
    source = _strip_rust_comments(source)
    results: list[tuple[str, int]] = []

    mod_re = re.compile(r"^\s*(?:pub\s+)?mod\s+(\w+)", re.MULTILINE)
    use_re = re.compile(
        r"^\s*(?:pub\s+)?use\s+(crate::[\w:]+|super::[\w:]+|self::[\w:]+)",
        re.MULTILINE,
    )

    for m in mod_re.finditer(source):
        results.append(("mod:" + m.group(1), source[: m.start()].count("\n") + 1))

    for m in use_re.finditer(source):
        results.append(("use:" + m.group(1), source[: m.start()].count("\n") + 1))

    return results


def _resolve_rust_mod(
    mod_name: str, current_file: Path, repo: Path, all_files: set[str]
) -> str | None:
    parent = current_file.parent

    candidates = [
        parent / f"{mod_name}.rs",
        parent / mod_name / "mod.rs",
        parent / "src" / f"{mod_name}.rs",
        parent / "src" / mod_name / "mod.rs",
    ]

    if current_file.name in ("mod.rs", "lib.rs", "main.rs"):
        candidates = [
            parent / f"{mod_name}.rs",
            parent / mod_name / "mod.rs",
        ]

    for c in candidates:
        try:
            rel = str(c.relative_to(repo))
        except ValueError:
            continue
        if rel in all_files:
            return rel

    return None


def _resolve_rust_use_path(
    use_path: str, current_file: Path, repo: Path, all_files: set[str]
) -> str | None:
    path_part = use_path.split("::")[0] if "::" in use_path else use_path

    if path_part in ("crate", "super", "self"):
        return None

    parent = current_file.parent
    candidates = [
        parent / f"{path_part}.rs",
        parent / path_part / "mod.rs",
    ]
    for c in candidates:
        try:
            rel = str(c.relative_to(repo))
        except ValueError:
            continue
        if rel in all_files:
            return rel

    return None


def _build_rust_graph(files: list[Path], repo: Path) -> dict:
    file_set = {str(f.relative_to(repo)): f for f in files}
    file_rel_set = set(file_set.keys())

    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for kind_path, lineno in _extract_rust_mods_and_uses(source):
            if kind_path.startswith("mod:"):
                mod_name = kind_path[4:]
                resolved = _resolve_rust_mod(mod_name, fpath, repo, file_rel_set)
                if resolved and resolved != rel:
                    edges.append({"from": rel, "to": resolved, "line": lineno})
                    adjacency[rel].append(resolved)
            elif kind_path.startswith("use:"):
                use_path = kind_path[4:]
                resolved = _resolve_rust_use_path(use_path, fpath, repo, file_rel_set)
                if resolved and resolved != rel:
                    edges.append({"from": rel, "to": resolved, "line": lineno})
                    adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _compute_most_depended(
    adjacency: dict[str, list[str]],
) -> list[dict[str, str | int]]:
    dep_counts: dict[str, int] = {}

    for deps in adjacency.values():
        for d in deps:
            dep_counts[d] = dep_counts.get(d, 0) + 1

    most_depended = sorted(dep_counts.items(), key=lambda item: -item[1])[
        :MAX_MOST_DEPENDED
    ]

    return [
        {"module": module, "dependents": dependents}
        for module, dependents in most_depended
    ]


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
            d.name
            for d in bd_path.iterdir()
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


def build_graph(repo_path: str, lang_filter: str | None = None) -> dict:
    try:
        repo = validate_repo(repo_path)
    except ValueError as exc:
        return {"error": str(exc), "script": "graph"}

    result: dict = {}

    langs = (
        [lang_filter]
        if lang_filter
        else ["python", "typescript", "javascript", "go", "rust"]
    )

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
            elif lang == "rust":
                result[lang] = _build_rust_graph(files, repo)
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

    return run_and_output(
        build_graph,
        repo=args.repo,
        pretty=args.pretty,
        script_name="graph",
        extra_kwargs={"lang_filter": args.lang},
    )


if __name__ == "__main__":
    sys.exit(main())
