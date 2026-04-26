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

from lib.output import run_and_output

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


def _parse_toml_value(s: str):
    s = s.strip()

    if not s:
        return None

    if s.startswith('"') or s.startswith("'"):
        q = s[0]
        return s.strip(q)

    if s.lower() == "true":
        return True

    if s.lower() == "false":
        return False

    if s.startswith("["):
        inner = s[1 : s.rfind("]")]
        items = [_parse_toml_value(x.strip()) for x in _split_toml_array(inner)]
        return [i for i in items if i is not None or i == ""]

    try:
        if "." in s:
            return float(s)

        return int(s)
    except ValueError:
        return s


def _split_toml_array(s: str) -> list[str]:
    items = []
    depth = 0
    current = []

    for ch in s:
        if ch in "([{":
            depth += 1
            current.append(ch)
        elif ch in ")]}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        items.append("".join(current).strip())

    return [i for i in items if i]


def _parse_toml(content: str) -> dict:
    result: dict = {}
    current_section: list[str] = []
    lines = content.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if stripped.startswith("[["):
            m = re.match(r"^\[\[([^\]]+)\]\]", stripped)

            if m:
                current_section = m.group(1).split(".")

            i += 1
            continue

        if stripped.startswith("["):
            m = re.match(r"^\[([^\]]+)\]", stripped)

            if m:
                current_section = m.group(1).split(".")

            i += 1
            continue

        if "=" in stripped and not stripped.startswith("#"):
            key, _, rest = stripped.partition("=")
            key = key.strip()
            rest = rest.strip()

            if rest.startswith("[") and "]" not in rest:
                parts = [rest]
                i += 1

                while i < len(lines):
                    part = lines[i].strip()
                    parts.append(part)

                    if "]" in part:
                        break

                    i += 1

                rest = " ".join(parts)

            value = _parse_toml_value(rest)
            node = result

            for part in current_section:
                node = node.setdefault(part, {})

            node[key] = value

        i += 1

    return result


def _get_nested(d: dict, *keys: str):
    for k in keys:
        if not isinstance(d, dict):
            return None

        d = d.get(k)

    return d


def _parse_yaml_simple(content: str) -> dict:
    result: dict = {}
    stack: list[tuple[int, dict | list]] = [(-1, result)]
    list_key_stack: list[str | None] = [None]

    for line in content.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
            list_key_stack.pop()

        parent = stack[-1][1]

        if stripped.startswith("- "):
            value = stripped[2:].strip()

            if isinstance(parent, dict):
                last_key = list_key_stack[-1]

                if last_key and isinstance(parent.get(last_key), list):
                    parent[last_key].append(_yaml_scalar(value))
        elif ":" in stripped:
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()

            if rest:
                if isinstance(parent, dict):
                    parent[key] = _yaml_scalar(rest)
                    list_key_stack[-1] = key
            else:
                if isinstance(parent, dict):
                    child: dict = {}
                    parent[key] = child
                    stack.append((indent, child))
                    list_key_stack.append(key)

    return result


def _yaml_scalar(s: str):
    s = s.strip().strip('"').strip("'")

    if s.lower() == "true":
        return True

    if s.lower() == "false":
        return False

    try:
        return int(s)
    except ValueError:
        pass

    try:
        return float(s)
    except ValueError:
        pass

    return s


def _parse_by_extension(raw: str, fname: str) -> dict:
    """Parse raw config file content based on file extension."""
    if fname.endswith(".json") or fname in (".prettierrc", ".eslintrc"):
        return _parse_json_safe(raw) if raw.strip().startswith("{") else {}

    if fname.endswith((".yml", ".yaml")):
        return _parse_yaml_simple(raw)

    if fname.endswith(".toml"):
        return _parse_toml(raw)

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
            extra = _parse_toml(_read(ruff_toml))
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
            "settings": _parse_toml(_read(black_toml)),
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
                "settings": _parse_toml(_read(fp)),
            }

            break

    clippy = repo / "clippy.toml"

    if clippy.exists():
        result["linter"] = {
            "name": "clippy",
            "config_file": "clippy.toml",
            "settings": _parse_toml(_read(clippy)),
        }

    return result


def _attach_editorconfig(lang_result: dict, ec_sections: dict, lang: str) -> None:
    """Mutate lang_result in place: attach editorconfig entry if one exists."""
    ec = _parse_editorconfig_for_lang(ec_sections, lang)

    if ec:
        lang_result["editorconfig"] = ec


def detect(repo_path: str) -> dict:
    repo = Path(repo_path).resolve()

    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "config"}

    toml_data: dict = {}
    pyproject = repo / "pyproject.toml"

    if pyproject.exists():
        toml_data = _parse_toml(_read(pyproject))

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
