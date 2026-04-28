#!/usr/bin/env python3
"""Detect formatters, linters, and type checkers. Extract their exact settings.

Reads config files directly — does not infer from code style.
Covers Python, TypeScript/JavaScript, Go, Rust. Falls back to .editorconfig
for cross-language indentation/line-ending settings.

Usage:
    python scripts/config.py <repo>
    python scripts/config.py <repo> --pretty
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

from common.fs import validate_repo
from lib.output import run_and_output
from lib.parsers import load_toml_safe, load_yaml_safe

MAX_CONFIG_READ_BYTES = 32_000

PRETTIER_CONFIG_FILES = [
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.js",
    ".prettierrc.cjs",
    ".prettierrc.yml",
    ".prettierrc.yaml",
    ".prettierrc.toml",
]

ESLINT_CONFIG_FILES = [
    ".eslintrc.json",
    ".eslintrc.js",
    ".eslintrc.cjs",
    ".eslintrc.yml",
    ".eslintrc.yaml",
    ".eslintrc",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
]


def _get_nested(d: Any, *keys: str) -> Any | None:
    for k in keys:
        if not isinstance(d, dict):
            return None

        d = d.get(k)

    return d


def _parse_by_extension(raw: str, fname: str) -> dict:
    """Parse raw config file content based on file extension."""
    if fname.endswith(".json") or fname in (".prettierrc", ".eslintrc"):
        return _parse_json_safe(raw) if raw.strip().startswith("{") else {}

    if fname.endswith((".yml", ".yaml")):
        return load_yaml_safe(raw)

    if fname.endswith(".toml"):
        return load_toml_safe(raw)

    return {}


def _read(path: Path, max_bytes: int = MAX_CONFIG_READ_BYTES) -> str:
    try:
        return path.read_text(errors="ignore")[:max_bytes]
    except Exception:
        return ""


def _parse_json_safe(content: str) -> dict:
    try:
        return json.loads(content)
    except Exception:
        return {}


def _parse_ini_section(content: str, header: str) -> dict:
    pattern = re.compile(
        r"^" + re.escape(header) + r"(.*?)(?=^\[|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    m = pattern.search(content)

    if not m:
        return {}

    result = {}

    for line in m.group(1).splitlines():
        line = line.strip()

        if not line or line.startswith("#") or line.startswith(";"):
            continue

        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()

    return result


def _parse_editorconfig(path: Path) -> dict:
    content = _read(path)
    sections: dict[str, dict] = {}
    current: dict = {}
    header = None

    for line in content.splitlines():
        s = line.strip()

        if not s or s.startswith("#") or s.startswith(";"):
            continue

        if s.startswith("["):
            if header and current:
                sections[header] = current

            header = s
            current = {}
        elif "=" in s:
            k, _, v = s.partition("=")
            current[k.strip().lower()] = v.strip().lower()

    if header and current:
        sections[header] = current

    return sections


def _parse_editorconfig_for_lang(sections: dict, lang: str) -> dict:
    """Extract editorconfig rules relevant to a language."""
    lang_ext_map = {
        "python": ["*.py"],
        "typescript": ["*.ts", "*.tsx"],
        "javascript": ["*.js", "*.jsx", "*.mjs"],
        "go": ["*.go"],
        "rust": ["*.rs"],
        "java": ["*.java"],
        "kotlin": ["*.kt", "*.kts"],
        "csharp": ["*.cs"],
        "c": ["*.c", "*.h"],
        "cpp": ["*.cpp", "*.cc", "*.cxx", "*.hpp", "*.hh", "*.hxx"],
        "ruby": ["*.rb"],
    }

    exts = lang_ext_map.get(lang, [])
    result = dict(sections.get("[*]", {}))

    for ext in exts:
        result.update(sections.get(f"[{ext}]", {}))

    return result


def _detect_python_formatter(repo: Path, toml_data: dict) -> dict | None:
    ruff_format = _get_nested(toml_data, "tool", "ruff", "format")
    ruff_top = _get_nested(toml_data, "tool", "ruff") or {}
    black_cfg = _get_nested(toml_data, "tool", "black")
    ruff_toml = repo / "ruff.toml"

    if ruff_format or ruff_toml.exists():
        settings = dict(ruff_format) if isinstance(ruff_format, dict) else {}

        for key in ("line-length", "indent-width"):
            if key in ruff_top:
                settings.setdefault(key, ruff_top[key])

        if ruff_toml.exists():
            extra = load_toml_safe(_read(ruff_toml))
            settings.update(extra.get("format", {}))

            if "line-length" in extra:
                settings.setdefault("line-length", extra["line-length"])

        return {"name": "ruff", "config_file": "pyproject.toml", "settings": settings}

    if black_cfg or (repo / ".black").exists():
        settings = dict(black_cfg) if isinstance(black_cfg, dict) else {}
        return {"name": "black", "config_file": "pyproject.toml", "settings": settings}

    black_toml = repo / "black.toml"

    if black_toml.exists():
        return {
            "name": "black",
            "config_file": "black.toml",
            "settings": load_toml_safe(_read(black_toml)),
        }

    return None


def _detect_python_linter(repo: Path, toml_data: dict) -> dict | None:
    ruff_lint = _get_nested(toml_data, "tool", "ruff", "lint")
    ruff_top_cfg = _get_nested(toml_data, "tool", "ruff") or {}
    flake8_cfg = repo / ".flake8"
    setup_cfg = repo / "setup.cfg"

    if ruff_lint or ruff_top_cfg:
        settings = dict(ruff_lint) if isinstance(ruff_lint, dict) else {}

        for k in (
            "select",
            "ignore",
            "extend-select",
            "extend-ignore",
            "per-file-ignores",
        ):
            if k in ruff_top_cfg and k not in settings:
                settings[k] = ruff_top_cfg[k]

        return {"name": "ruff", "config_file": "pyproject.toml", "settings": settings}

    if flake8_cfg.exists():
        return {
            "name": "flake8",
            "config_file": ".flake8",
            "settings": _parse_ini_section(_read(flake8_cfg), "[flake8]"),
        }

    if setup_cfg.exists():
        parsed = _parse_ini_section(_read(setup_cfg), "[flake8]")

        if parsed:
            return {"name": "flake8", "config_file": "setup.cfg", "settings": parsed}

    return None


def _detect_python_type_checker(repo: Path, toml_data: dict) -> dict | None:
    mypy_cfg = _get_nested(toml_data, "tool", "mypy")
    mypy_ini = repo / "mypy.ini"
    mypy_ini2 = repo / ".mypy.ini"
    pyright_json = repo / "pyrightconfig.json"

    if mypy_cfg:
        return {
            "name": "mypy",
            "config_file": "pyproject.toml",
            "settings": dict(mypy_cfg),
        }

    if mypy_ini.exists():
        return {
            "name": "mypy",
            "config_file": "mypy.ini",
            "settings": _parse_ini_section(_read(mypy_ini), "[mypy]"),
        }

    if mypy_ini2.exists():
        return {
            "name": "mypy",
            "config_file": ".mypy.ini",
            "settings": _parse_ini_section(_read(mypy_ini2), "[mypy]"),
        }

    if pyright_json.exists():
        return {
            "name": "pyright",
            "config_file": "pyrightconfig.json",
            "settings": _parse_json_safe(_read(pyright_json)),
        }

    return None


def _detect_python(repo: Path, toml_data: dict) -> dict:
    result: dict = {}

    formatter = _detect_python_formatter(repo, toml_data)
    linter = _detect_python_linter(repo, toml_data)
    type_checker = _detect_python_type_checker(repo, toml_data)

    if formatter:
        result["formatter"] = formatter

    if linter:
        result["linter"] = linter

    if type_checker:
        result["type_checker"] = type_checker

    return result


def _detect_typescript(repo: Path) -> dict:
    result: dict = {}

    for fname in PRETTIER_CONFIG_FILES:
        fp = repo / fname

        if fp.exists():
            result["formatter"] = {
                "name": "prettier",
                "config_file": fname,
                "settings": _parse_by_extension(_read(fp), fname),
            }

            break

    if "formatter" not in result:
        pkg = repo / "package.json"

        if pkg.exists():
            data = _parse_json_safe(_read(pkg))

            if "prettier" in data:
                result["formatter"] = {
                    "name": "prettier",
                    "config_file": "package.json",
                    "settings": data["prettier"],
                }

    for fname in ESLINT_CONFIG_FILES:
        fp = repo / fname

        if fp.exists():
            result["linter"] = {
                "name": "eslint",
                "config_file": fname,
                "settings": _parse_by_extension(_read(fp), fname),
            }

            break

    tsconfig = repo / "tsconfig.json"

    if tsconfig.exists():
        data = _parse_json_safe(_read(tsconfig))

        result["type_checker"] = {
            "name": "tsc",
            "config_file": "tsconfig.json",
            "settings": data.get("compilerOptions", {}),
        }

    return result


def _detect_go(repo: Path) -> dict:
    result: dict = {
        "formatter": {"name": "gofmt", "config_file": None, "settings": {}},
    }

    for fname in [
        ".golangci.yml",
        ".golangci.yaml",
        ".golangci.toml",
        ".golangci.json",
    ]:
        fp = repo / fname

        if fp.exists():
            result["linter"] = {
                "name": "golangci-lint",
                "config_file": fname,
                "settings": _parse_by_extension(_read(fp), fname),
            }

            break

    return result


def _detect_rust(repo: Path) -> dict:
    result: dict = {}

    for fname in ["rustfmt.toml", ".rustfmt.toml"]:
        fp = repo / fname

        if fp.exists():
            result["formatter"] = {
                "name": "rustfmt",
                "config_file": fname,
                "settings": load_toml_safe(_read(fp)),
            }

            break

    clippy = repo / "clippy.toml"

    if clippy.exists():
        result["linter"] = {
            "name": "clippy",
            "config_file": "clippy.toml",
            "settings": load_toml_safe(_read(clippy)),
        }

    return result


def _detect_jvm_markers(repo: Path, language: str) -> dict:
    markers: list[str] = []
    build_files = {
        "java": [
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "settings.gradle.kts",
        ],
        "kotlin": [
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "settings.gradle.kts",
        ],
    }

    source_roots = {
        "java": ["src/main/java", "src/test/java"],
        "kotlin": ["src/main/kotlin", "src/test/kotlin"],
    }

    for marker in build_files.get(language, []):
        if (repo / marker).exists():
            markers.append(marker)

    for root in source_roots.get(language, []):
        if (repo / root).exists():
            markers.append(root)

    if not markers:
        return {}

    build_tool = None

    if language == "java" and "pom.xml" in markers:
        build_tool = "maven"
    elif any(marker.startswith("build.gradle") for marker in markers) or any(
        marker.startswith("settings.gradle") for marker in markers
    ):
        build_tool = "gradle"

    return {
        "project_markers": sorted(markers),
        "build_tool": build_tool,
    }


def _detect_csharp_markers(repo: Path) -> dict:
    markers: list[str] = []

    for pattern in (
        "*.csproj",
        "*.sln",
        "Directory.Build.props",
        "Directory.Build.targets",
    ):
        if "*" in pattern:
            markers.extend(sorted(path.name for path in repo.rglob(pattern)))
        elif (repo / pattern).exists():
            markers.append(pattern)

    if not markers:
        return {}

    return {
        "project_markers": sorted(set(markers)),
        "build_tool": "msbuild",
    }


def _detect_c_family_markers(repo: Path, language: str) -> dict:
    markers: list[str] = []

    for marker in ("CMakeLists.txt", "Makefile", "makefile", "GNUmakefile"):
        if (repo / marker).exists():
            markers.append(marker)

    cmake_files = sorted(path.name for path in repo.rglob("*.cmake"))

    if cmake_files:
        markers.extend(cmake_files)

    vcxproj_files = sorted(path.name for path in repo.rglob("*.vcxproj"))

    if vcxproj_files:
        markers.extend(vcxproj_files)

    if not markers:
        return {}

    build_tool = None

    if "CMakeLists.txt" in markers or cmake_files:
        build_tool = "cmake"
    elif any(marker in markers for marker in ("Makefile", "makefile", "GNUmakefile")):
        build_tool = "make"

    return {
        "project_markers": sorted(set(markers)),
        "build_tool": build_tool,
    }


def _attach_editorconfig(lang_result: dict, ec_sections: dict, lang: str) -> None:
    """Mutate lang_result in place: attach editorconfig entry if one exists."""
    ec = _parse_editorconfig_for_lang(ec_sections, lang)

    if ec:
        lang_result["editorconfig"] = ec


def detect(repo_path: str) -> dict:
    try:
        repo = validate_repo(repo_path)
    except ValueError as exc:
        return {"error": str(exc), "script": "config"}

    toml_data: dict = {}
    pyproject = repo / "pyproject.toml"

    if pyproject.exists():
        toml_data = load_toml_safe(_read(pyproject))

    ec_sections: dict = {}
    ec = repo / ".editorconfig"

    if ec.exists():
        ec_sections = _parse_editorconfig(ec)

    result: dict = {}
    py = _detect_python(repo, toml_data)

    if py:
        _attach_editorconfig(py, ec_sections, "python")
        result["python"] = py

    ts = _detect_typescript(repo)

    if ts:
        _attach_editorconfig(ts, ec_sections, "typescript")
        result["typescript"] = ts

    go = _detect_go(repo)

    if (repo / "go.mod").exists() or list(repo.rglob("*.go")):
        _attach_editorconfig(go, ec_sections, "go")
        result["go"] = go

    rust = _detect_rust(repo)

    if (repo / "Cargo.toml").exists() or list(repo.rglob("*.rs")):
        _attach_editorconfig(rust, ec_sections, "rust")
        result["rust"] = rust

    java = _detect_jvm_markers(repo, "java")

    if java or list(repo.rglob("*.java")):
        _attach_editorconfig(java, ec_sections, "java")
        result["java"] = java

    kotlin = _detect_jvm_markers(repo, "kotlin")

    if kotlin or list(repo.rglob("*.kt")) or list(repo.rglob("*.kts")):
        _attach_editorconfig(kotlin, ec_sections, "kotlin")
        result["kotlin"] = kotlin

    csharp = _detect_csharp_markers(repo)

    if csharp or list(repo.rglob("*.cs")):
        _attach_editorconfig(csharp, ec_sections, "csharp")
        result["csharp"] = csharp

    c_lang = _detect_c_family_markers(repo, "c")

    if c_lang or list(repo.rglob("*.c")) or list(repo.rglob("*.h")):
        _attach_editorconfig(c_lang, ec_sections, "c")
        result["c"] = c_lang

    cpp = _detect_c_family_markers(repo, "cpp")

    if (
        cpp
        or list(repo.rglob("*.cpp"))
        or list(repo.rglob("*.cc"))
        or list(repo.rglob("*.cxx"))
    ):
        _attach_editorconfig(cpp, ec_sections, "cpp")
        result["cpp"] = cpp

    if ec_sections:
        result["editorconfig"] = ec_sections

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

    return run_and_output(
        detect,
        repo=args.repo,
        pretty=args.pretty,
        script_name="config",
    )


if __name__ == "__main__":
    sys.exit(main())
