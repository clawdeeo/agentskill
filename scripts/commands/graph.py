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
from common.languages import language_for_path
from lib.cli_entrypoint import run_command_main

MAX_EDGES = 200
MAX_CYCLES = 20
MAX_MOST_DEPENDED = 10
MIN_MONOREPO_SERVICES = 2

MONOREPO_BOUNDARY_DIRS = ["services", "packages", "apps", "modules"]


def _collect_files(repo: Path, lang: str) -> list[Path]:
    found = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for fn in files:
            fpath = Path(dirpath) / fn
            spec = language_for_path(fpath)

            if spec and spec.id == lang:
                found.append(fpath)

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


def _strip_jvm_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _strip_c_family_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _strip_ruby_comments(source: str) -> str:
    return re.sub(r"#.*", "", source)


def _strip_shell_comments(source: str) -> str:
    lines = source.splitlines()
    stripped: list[str] = []

    for i, line in enumerate(lines):
        if i == 0 and line.startswith("#!"):
            stripped.append(line)
            continue

        stripped.append(re.sub(r"#.*", "", line))

    return "\n".join(stripped)


def _strip_swift_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _extract_jvm_package(content: str) -> str | None:
    stripped = _strip_jvm_comments(content)

    match = re.search(
        r"^[ \t]*package\s+([A-Za-z_][\w.]*)[ \t]*;?[ \t]*$",
        stripped,
        re.MULTILINE,
    )

    return match.group(1) if match else None


def _extract_jvm_imports(content: str) -> list[tuple[str, int]]:
    stripped = _strip_jvm_comments(content)
    imports: list[tuple[str, int]] = []

    pattern = re.compile(
        r"^[ \t]*import\s+(?:static\s+)?([A-Za-z_][\w.]*)(?:\.\*)?[ \t]*;?[ \t]*$",
        re.MULTILINE,
    )

    for match in pattern.finditer(stripped):
        imports.append((match.group(1), stripped[: match.start()].count("\n") + 1))

    return imports


def _jvm_declared_name(path: Path) -> str | None:
    if path.suffix.lower() == ".kts":
        return None

    stem = path.stem

    if stem and stem[0].isupper():
        return stem

    return None


def _build_jvm_package_index(
    files: list[Path], repo: Path
) -> tuple[dict[str, str], dict[str, set[str]]]:
    symbol_index: dict[str, str] = {}
    package_index: dict[str, set[str]] = {}

    for fpath in files:
        rel = str(fpath.relative_to(repo))

        try:
            source = read_text(fpath)
        except Exception:
            continue

        package_name = _extract_jvm_package(source)
        declared_name = _jvm_declared_name(fpath)

        if package_name:
            package_index.setdefault(package_name, set()).add(rel)

            if declared_name:
                symbol_index[f"{package_name}.{declared_name}"] = rel
        elif declared_name:
            symbol_index[declared_name] = rel

    return symbol_index, package_index


def _resolve_jvm_import(
    import_name: str,
    symbol_index: dict[str, str],
    package_index: dict[str, set[str]],
) -> str | None:
    if import_name in symbol_index:
        return symbol_index[import_name]

    package_name = import_name.rsplit(".", 1)[0] if "." in import_name else import_name
    matches = package_index.get(package_name)

    if not matches:
        return None

    if len(matches) == 1:
        return next(iter(matches))

    return None


def _build_jvm_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []
    symbol_index, package_index = _build_jvm_package_index(files, repo)

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for import_name, lineno in _extract_jvm_imports(source):
            resolved = _resolve_jvm_import(import_name, symbol_index, package_index)

            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "line": lineno})
                adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _extract_csharp_namespace(content: str) -> str | None:
    stripped = _strip_c_family_comments(content)

    match = re.search(
        r"^\s*namespace\s+([A-Za-z_][\w.]*)\s*(?:;|\{)",
        stripped,
        re.MULTILINE,
    )

    return match.group(1) if match else None


def _extract_csharp_usings(content: str) -> list[tuple[str, int]]:
    stripped = _strip_c_family_comments(content)
    results: list[tuple[str, int]] = []

    pattern = re.compile(
        r"^\s*using\s+(?:static\s+)?([A-Za-z_][\w.]*)\s*;",
        re.MULTILINE,
    )

    for match in pattern.finditer(stripped):
        results.append((match.group(1), stripped[: match.start()].count("\n") + 1))

    return results


def _build_csharp_index(
    files: list[Path], repo: Path
) -> tuple[dict[str, str], dict[str, set[str]]]:
    symbol_index: dict[str, str] = {}
    namespace_index: dict[str, set[str]] = {}

    for fpath in files:
        rel = str(fpath.relative_to(repo))

        try:
            source = read_text(fpath)
        except Exception:
            continue

        namespace_name = _extract_csharp_namespace(source)

        if namespace_name:
            namespace_index.setdefault(namespace_name, set()).add(rel)
            symbol_index[f"{namespace_name}.{fpath.stem}"] = rel
        else:
            symbol_index[fpath.stem] = rel

    return symbol_index, namespace_index


def _resolve_csharp_using(
    using_name: str,
    symbol_index: dict[str, str],
    namespace_index: dict[str, set[str]],
) -> str | None:
    if using_name in symbol_index:
        return symbol_index[using_name]

    matches = namespace_index.get(using_name)

    if matches and len(matches) == 1:
        return next(iter(matches))

    for namespace_name, files in namespace_index.items():
        if using_name.startswith(namespace_name + ".") and len(files) == 1:
            return next(iter(files))

    return None


def _build_csharp_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []
    symbol_index, namespace_index = _build_csharp_index(files, repo)

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for using_name, lineno in _extract_csharp_usings(source):
            resolved = _resolve_csharp_using(using_name, symbol_index, namespace_index)

            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "line": lineno})
                adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _extract_c_cpp_includes(content: str) -> list[tuple[str, str, int]]:
    stripped = _strip_c_family_comments(content)
    results: list[tuple[str, str, int]] = []
    pattern = re.compile(r'^\s*#include\s*([<"])([^>"]+)[>"]', re.MULTILINE)

    for match in pattern.finditer(stripped):
        delim = match.group(1)
        include_name = match.group(2).strip()
        line = stripped[: match.start()].count("\n") + 1
        results.append((include_name, delim, line))

    return results


def _build_include_lookup(repo: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for fn in files:
            fpath = Path(dirpath) / fn
            rel = str(fpath.relative_to(repo))
            posix_rel = Path(rel).as_posix()
            key = posix_rel.lower()
            lookup.setdefault(key, rel)
            lookup.setdefault(fpath.name.lower(), rel)

            parts = fpath.parts
            for root_name in ("include", "src", "lib"):
                if root_name in parts:
                    idx = parts.index(root_name)
                    subpath = Path(*parts[idx + 1 :]).as_posix().lower()

                    if subpath:
                        lookup.setdefault(subpath, rel)

    return lookup


def _resolve_c_cpp_include(
    importer: Path,
    include_name: str,
    repo: Path,
    include_lookup: dict[str, str],
) -> str | None:
    normalized = Path(include_name).as_posix().lower()

    path_candidates = [
        importer.parent / include_name,
        repo / include_name,
        repo / "include" / include_name,
        repo / "src" / include_name,
        repo / "lib" / include_name,
    ]

    for candidate_path in path_candidates:
        if candidate_path.exists():
            try:
                return str(candidate_path.resolve().relative_to(repo.resolve()))
            except ValueError:
                continue

    candidates: list[str] = [normalized]

    candidates.extend(
        [f"include/{normalized}", f"src/{normalized}", f"lib/{normalized}"]
    )

    for candidate in candidates:
        if candidate in include_lookup:
            return include_lookup[candidate]

    return None


def _build_c_cpp_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []
    include_lookup = _build_include_lookup(repo)

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for include_name, _delim, lineno in _extract_c_cpp_includes(source):
            resolved = _resolve_c_cpp_include(fpath, include_name, repo, include_lookup)

            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "line": lineno})
                adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _extract_ruby_requires(content: str) -> list[tuple[str, str, int]]:
    stripped = _strip_ruby_comments(content)
    results: list[tuple[str, str, int]] = []
    pattern = re.compile(
        r'^\s*(require_relative|require)\s+["\']([^"\']+)["\']',
        re.MULTILINE,
    )

    for match in pattern.finditer(stripped):
        results.append(
            (
                match.group(1),
                match.group(2),
                stripped[: match.start()].count("\n") + 1,
            )
        )

    return results


def _resolve_ruby_require(
    importer: Path, kind: str, target: str, repo: Path, file_set: set[str]
) -> str | None:
    candidates: list[Path] = []

    if kind == "require_relative":
        base = importer.parent / target
        candidates.extend([base, base.with_suffix(".rb"), base / "index.rb"])
    else:
        for prefix in (repo / "lib", repo / "app", repo):
            base = prefix / target
            candidates.extend([base, base.with_suffix(".rb"), base / "index.rb"])

    for candidate in candidates:
        try:
            rel = str(candidate.resolve().relative_to(repo.resolve()))
        except ValueError:
            continue

        if rel in file_set:
            return rel

    return None


def _build_ruby_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []
    file_set = {str(f.relative_to(repo)) for f in files}

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for kind, target, lineno in _extract_ruby_requires(source):
            resolved = _resolve_ruby_require(fpath, kind, target, repo, file_set)

            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "line": lineno})
                adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _extract_php_namespace(content: str) -> str | None:
    stripped = _strip_c_family_comments(content)
    match = re.search(r"^\s*namespace\s+([A-Za-z_][\w\\]*)\s*;", stripped, re.MULTILINE)
    return match.group(1) if match else None


def _extract_php_uses(content: str) -> list[tuple[str, int]]:
    stripped = _strip_c_family_comments(content)
    results: list[tuple[str, int]] = []
    pattern = re.compile(r"^[ \t]*use\s+([A-Za-z_][\w\\]*)[ \t]*;", re.MULTILINE)

    for match in pattern.finditer(stripped):
        results.append((match.group(1), stripped[: match.start()].count("\n") + 1))

    return results


def _build_php_index(
    files: list[Path], repo: Path
) -> tuple[dict[str, str], dict[str, set[str]]]:
    symbol_index: dict[str, str] = {}
    namespace_index: dict[str, set[str]] = {}

    for fpath in files:
        rel = str(fpath.relative_to(repo))

        try:
            source = read_text(fpath)
        except Exception:
            continue

        namespace_name = _extract_php_namespace(source)

        if namespace_name:
            namespace_index.setdefault(namespace_name, set()).add(rel)
            symbol_index[f"{namespace_name}\\{fpath.stem}"] = rel
        else:
            symbol_index[fpath.stem] = rel

    return symbol_index, namespace_index


def _resolve_php_use(
    use_name: str, symbol_index: dict[str, str], namespace_index: dict[str, set[str]]
) -> str | None:
    if use_name in symbol_index:
        return symbol_index[use_name]

    namespace_name = use_name.rsplit("\\", 1)[0] if "\\" in use_name else use_name
    matches = namespace_index.get(namespace_name)

    if matches and len(matches) == 1:
        return next(iter(matches))

    return None


def _build_php_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []
    symbol_index, namespace_index = _build_php_index(files, repo)

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for use_name, lineno in _extract_php_uses(source):
            resolved = _resolve_php_use(use_name, symbol_index, namespace_index)

            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "line": lineno})
                adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _extract_shell_sources(content: str) -> list[tuple[str, int]]:
    stripped = _strip_shell_comments(content)
    results: list[tuple[str, int]] = []
    pattern = re.compile(
        r'^[ \t]*(?:source|\.)\s+([^\s"\']+|["\'][^"\']+["\'])',
        re.MULTILINE,
    )

    for match in pattern.finditer(stripped):
        target = match.group(1).strip("\"'")

        if "$" in target or "{" in target:
            continue

        results.append((target, stripped[: match.start()].count("\n") + 1))

    return results


def _resolve_shell_source(
    importer: Path, target: str, repo: Path, file_set: set[str]
) -> str | None:
    base = importer.parent / target
    candidates = [base, repo / target]

    for candidate in candidates:
        try:
            rel = str(candidate.relative_to(repo))
        except ValueError:
            continue

        if rel in file_set:
            return rel

    return None


def _build_shell_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []
    file_set = {str(f.relative_to(repo)) for f in files}

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for target, lineno in _extract_shell_sources(source):
            resolved = _resolve_shell_source(fpath, target, repo, file_set)

            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "line": lineno})
                adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _extract_swift_imports(content: str) -> list[tuple[str, int]]:
    stripped = _strip_swift_comments(content)
    results: list[tuple[str, int]] = []

    pattern = re.compile(
        r"^[ \t]*(?:@testable\s+)?import\s+([A-Za-z_]\w*)",
        re.MULTILINE,
    )

    for match in pattern.finditer(stripped):
        results.append((match.group(1), stripped[: match.start()].count("\n") + 1))

    return results


def _swift_module_name(path: Path, repo: Path) -> str | None:
    rel = path.relative_to(repo)
    parts = rel.parts

    if len(parts) >= 2 and parts[0] == "Sources":
        return parts[1]

    if len(parts) >= 2 and parts[0] == "Tests":
        return parts[1].removesuffix("Tests")

    return None


def _build_swift_module_index(files: list[Path], repo: Path) -> dict[str, str]:
    index: dict[str, str] = {}

    for fpath in files:
        module_name = _swift_module_name(fpath, repo)

        if not module_name:
            continue

        index.setdefault(module_name, str(fpath.relative_to(repo)))

    return index


def _build_swift_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []
    module_index = _build_swift_module_index(files, repo)

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for module_name, lineno in _extract_swift_imports(source):
            resolved = module_index.get(module_name)

            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "line": lineno})
                adjacency[rel].append(resolved)

    return _graph_result(sorted(adjacency.keys()), edges, adjacency, parse_errors)


def _is_objectivec_header(path: Path) -> bool:
    if path.suffix.lower() != ".h":
        return False

    content = read_text(path)

    return any(
        marker in content
        for marker in ("@interface", "@protocol", "@implementation", "#import")
    )


def _collect_objectivec_files(repo: Path) -> list[Path]:
    found: list[Path] = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for fn in files:
            fpath = Path(dirpath) / fn
            suffix = fpath.suffix.lower()

            if suffix in {".m", ".mm"} or (
                suffix == ".h" and _is_objectivec_header(fpath)
            ):
                found.append(fpath)

    return found


def _extract_objc_imports(content: str) -> list[tuple[str, int]]:
    stripped = _strip_c_family_comments(content)
    results: list[tuple[str, int]] = []
    pattern = re.compile(r'^[ \t]*#(?:import|include)\s*[<"]([^>"]+)[>"]', re.MULTILINE)

    for match in pattern.finditer(stripped):
        results.append(
            (match.group(1).strip(), stripped[: match.start()].count("\n") + 1)
        )

    return results


def _resolve_objc_import(
    importer: Path, import_name: str, repo: Path, include_lookup: dict[str, str]
) -> str | None:
    normalized = Path(import_name).as_posix().lower()

    path_candidates = [
        importer.parent / import_name,
        repo / import_name,
        repo / "include" / import_name,
        repo / "Headers" / import_name,
        repo / "Sources" / import_name,
    ]

    for candidate_path in path_candidates:
        if candidate_path.exists():
            try:
                return str(candidate_path.resolve().relative_to(repo.resolve()))
            except ValueError:
                continue

    candidates = [
        normalized,
        f"include/{normalized}",
        f"headers/{normalized}",
        f"sources/{normalized}",
    ]

    for candidate in candidates:
        if candidate in include_lookup:
            return include_lookup[candidate]

    return None


def _build_objectivec_graph(files: list[Path], repo: Path) -> dict:
    edges: list[dict] = []
    adjacency: dict[str, list[str]] = {}
    parse_errors: list[str] = []
    include_lookup = _build_include_lookup(repo)

    for fpath in files:
        rel = str(fpath.relative_to(repo))
        adjacency.setdefault(rel, [])

        try:
            source = read_text(fpath)
        except Exception:
            parse_errors.append(rel)
            continue

        for import_name, lineno in _extract_objc_imports(source):
            resolved = _resolve_objc_import(fpath, import_name, repo, include_lookup)

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
        else [
            "python",
            "typescript",
            "javascript",
            "go",
            "rust",
            "java",
            "kotlin",
            "csharp",
            "c",
            "cpp",
            "ruby",
            "php",
            "bash",
            "swift",
            "objectivec",
        ]
    )

    for lang in langs:
        files = (
            _collect_objectivec_files(repo)
            if lang == "objectivec"
            else _collect_files(repo, lang)
        )

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
            elif lang in ("java", "kotlin"):
                result[lang] = _build_jvm_graph(files, repo)
            elif lang == "csharp":
                result[lang] = _build_csharp_graph(files, repo)
            elif lang in ("c", "cpp"):
                result[lang] = _build_c_cpp_graph(files, repo)
            elif lang == "ruby":
                result[lang] = _build_ruby_graph(files, repo)
            elif lang == "php":
                result[lang] = _build_php_graph(files, repo)
            elif lang == "bash":
                result[lang] = _build_shell_graph(files, repo)
            elif lang == "swift":
                result[lang] = _build_swift_graph(files, repo)
            elif lang == "objectivec":
                result[lang] = _build_objectivec_graph(files, repo)
        except Exception as exc:
            result[lang] = {"error": str(exc)}

    result["monorepo_boundaries"] = _detect_monorepo_boundaries(repo)
    return result


def main(argv: list[str] | None = None) -> int:
    return run_command_main(
        argv=argv,
        description=__doc__,
        command_fn=build_graph,
        script_name="graph",
        supports_lang=True,
    )


if __name__ == "__main__":
    sys.exit(main())
