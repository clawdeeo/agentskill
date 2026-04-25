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
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal TOML parser — covers the subset used by formatter/linter configs.
# Handles: [sections], key = value, key = "string", key = 123, key = true,
#          key = ["a", "b"], multi-line arrays, inline tables {k = v}.
# Does NOT handle: dotted keys, multi-line strings, datetime, hex/octal.
# ---------------------------------------------------------------------------

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
        inner = s[1:s.rfind("]")]
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

        # Skip comments and blanks
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Section header [a.b.c] or [[array]]
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

        # Key = value
        if "=" in stripped and not stripped.startswith("#"):
            key, _, rest = stripped.partition("=")
            key = key.strip()
            rest = rest.strip()

            # Multi-line array
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


# ---------------------------------------------------------------------------
# Minimal YAML scalar parser for simple flat/nested configs
# (.golangci.yml, .prettierrc.yml, etc.)
# Handles: scalars, sequences (- item), mappings (key: value)
# Does NOT handle: anchors, aliases, multi-document, block scalars
# ---------------------------------------------------------------------------

def _parse_yaml_simple(content: str) -> dict:
    result: dict = {}
    stack: list[tuple[int, dict | list]] = [(-1, result)]
    list_key_stack: list[str | None] = [None]

    for line in content.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # Pop stack to current indent level
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
                    # Pre-create list for sequences
        elif stripped.startswith("- "):
            pass

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


# ---------------------------------------------------------------------------
# Config file discovery and parsing
# ---------------------------------------------------------------------------

def _read(path: Path, max_bytes: int = 32_000) -> str:
    try:
        return path.read_text(errors="ignore")[:max_bytes]
    except Exception:
        return ""


def _parse_json_safe(content: str) -> dict:
    try:
        return json.loads(content)
    except Exception:
        return {}


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


def _settings_from_pyproject(tool_path: list[str], toml_data: dict) -> dict:
    node = toml_data
    for key in tool_path:
        if not isinstance(node, dict):
            return {}
        node = node.get(key, {})
    return node if isinstance(node, dict) else {}


def _detect_python(repo: Path, toml_data: dict) -> dict:
    result: dict = {}

    # --- Formatter ---
    # Priority: ruff.format > black
    ruff_format = _get_nested(toml_data, "tool", "ruff", "format")
    black_cfg = _get_nested(toml_data, "tool", "black")
    ruff_toml_path = repo / "ruff.toml"
    black_toml_path = repo / ".black"

    if ruff_format or ruff_toml_path.exists():
        settings = dict(ruff_format) if isinstance(ruff_format, dict) else {}
        # Pull line-length from top-level ruff config too
        ruff_top = _get_nested(toml_data, "tool", "ruff") or {}
        if "line-length" in ruff_top:
            settings.setdefault("line-length", ruff_top["line-length"])
        if "indent-width" in ruff_top:
            settings.setdefault("indent-width", ruff_top["indent-width"])
        if ruff_toml_path.exists():
            extra = _parse_toml(_read(ruff_toml_path))
            settings.update(extra.get("format", {}))
            if "line-length" in extra:
                settings.setdefault("line-length", extra["line-length"])
        result["formatter"] = {"name": "ruff", "config_file": "pyproject.toml", "settings": settings}
    elif black_cfg or black_toml_path.exists():
        settings = dict(black_cfg) if isinstance(black_cfg, dict) else {}
        result["formatter"] = {"name": "black", "config_file": "pyproject.toml", "settings": settings}
    else:
        # Check standalone black.toml
        for fname in ["black.toml"]:
            fp = repo / fname
            if fp.exists():
                result["formatter"] = {"name": "black", "config_file": fname,
                                       "settings": _parse_toml(_read(fp))}
                break

    # --- Linter ---
    ruff_lint = _get_nested(toml_data, "tool", "ruff", "lint")
    ruff_top2 = _get_nested(toml_data, "tool", "ruff") or {}
    flake8_cfg = repo / ".flake8"
    setup_cfg = repo / "setup.cfg"

    if ruff_lint or _get_nested(toml_data, "tool", "ruff"):
        settings = dict(ruff_lint) if isinstance(ruff_lint, dict) else {}
        # Include top-level ruff select/ignore if present
        for k in ("select", "ignore", "extend-select", "extend-ignore", "per-file-ignores"):
            if k in ruff_top2 and k not in settings:
                settings[k] = ruff_top2[k]
        result["linter"] = {"name": "ruff", "config_file": "pyproject.toml", "settings": settings}
    elif flake8_cfg.exists():
        raw = _read(flake8_cfg)
        parsed = _parse_ini_section(raw, "[flake8]")
        result["linter"] = {"name": "flake8", "config_file": ".flake8", "settings": parsed}
    elif setup_cfg.exists():
        raw = _read(setup_cfg)
        parsed = _parse_ini_section(raw, "[flake8]")
        if parsed:
            result["linter"] = {"name": "flake8", "config_file": "setup.cfg", "settings": parsed}

    # --- Type checker ---
    mypy_cfg = _get_nested(toml_data, "tool", "mypy")
    mypy_ini = repo / "mypy.ini"
    mypy_ini2 = repo / ".mypy.ini"
    pyright_json = repo / "pyrightconfig.json"

    if mypy_cfg:
        result["type_checker"] = {"name": "mypy", "config_file": "pyproject.toml",
                                   "settings": dict(mypy_cfg)}
    elif mypy_ini.exists():
        raw = _read(mypy_ini)
        result["type_checker"] = {"name": "mypy", "config_file": "mypy.ini",
                                   "settings": _parse_ini_section(raw, "[mypy]")}
    elif mypy_ini2.exists():
        raw = _read(mypy_ini2)
        result["type_checker"] = {"name": "mypy", "config_file": ".mypy.ini",
                                   "settings": _parse_ini_section(raw, "[mypy]")}
    elif pyright_json.exists():
        result["type_checker"] = {"name": "pyright", "config_file": "pyrightconfig.json",
                                   "settings": _parse_json_safe(_read(pyright_json))}

    return result


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


def _detect_typescript(repo: Path) -> dict:
    result: dict = {}

    # --- Formatter: prettier ---
    prettier_files = [
        ".prettierrc", ".prettierrc.json", ".prettierrc.js",
        ".prettierrc.cjs", ".prettierrc.yml", ".prettierrc.yaml",
        ".prettierrc.toml",
    ]
    for fname in prettier_files:
        fp = repo / fname
        if fp.exists():
            raw = _read(fp)
            if fname.endswith(".json") or fname == ".prettierrc":
                settings = _parse_json_safe(raw) if raw.strip().startswith("{") else {}
            elif fname.endswith((".yml", ".yaml")):
                settings = _parse_yaml_simple(raw)
            elif fname.endswith(".toml"):
                settings = _parse_toml(raw)
            else:
                settings = {}
            result["formatter"] = {"name": "prettier", "config_file": fname, "settings": settings}
            break

    # Also check package.json "prettier" key
    if "formatter" not in result:
        pkg = repo / "package.json"
        if pkg.exists():
            data = _parse_json_safe(_read(pkg))
            if "prettier" in data:
                result["formatter"] = {"name": "prettier", "config_file": "package.json",
                                       "settings": data["prettier"]}

    # --- Linter: eslint ---
    eslint_files = [
        ".eslintrc.json", ".eslintrc.js", ".eslintrc.cjs",
        ".eslintrc.yml", ".eslintrc.yaml", ".eslintrc",
        "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    ]
    for fname in eslint_files:
        fp = repo / fname
        if fp.exists():
            raw = _read(fp)
            settings: dict = {}
            if fname.endswith(".json") or fname == ".eslintrc":
                settings = _parse_json_safe(raw) if raw.strip().startswith("{") else {}
            elif fname.endswith((".yml", ".yaml")):
                settings = _parse_yaml_simple(raw)
            result["linter"] = {"name": "eslint", "config_file": fname, "settings": settings}
            break

    # --- Type checker: tsc ---
    tsconfig = repo / "tsconfig.json"
    if tsconfig.exists():
        data = _parse_json_safe(_read(tsconfig))
        compiler_opts = data.get("compilerOptions", {})
        result["type_checker"] = {"name": "tsc", "config_file": "tsconfig.json",
                                   "settings": compiler_opts}

    return result


def _detect_go(repo: Path) -> dict:
    result: dict = {
        "formatter": {"name": "gofmt", "config_file": None, "settings": {}},
    }

    for fname in [".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json"]:
        fp = repo / fname
        if fp.exists():
            raw = _read(fp)
            if fname.endswith(".json"):
                settings = _parse_json_safe(raw)
            elif fname.endswith((".yml", ".yaml")):
                settings = _parse_yaml_simple(raw)
            else:
                settings = _parse_toml(raw)
            result["linter"] = {"name": "golangci-lint", "config_file": fname,
                                 "settings": settings}
            break

    return result


def _detect_rust(repo: Path) -> dict:
    result: dict = {}

    for fname in ["rustfmt.toml", ".rustfmt.toml"]:
        fp = repo / fname
        if fp.exists():
            result["formatter"] = {"name": "rustfmt", "config_file": fname,
                                   "settings": _parse_toml(_read(fp))}
            break

    clippy = repo / "clippy.toml"
    if clippy.exists():
        result["linter"] = {"name": "clippy", "config_file": "clippy.toml",
                             "settings": _parse_toml(_read(clippy))}

    return result


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
        key = f"[{ext}]"
        result.update(sections.get(key, {}))
    return result


def detect(repo_path: str) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "config"}

    # Load pyproject.toml once
    toml_data: dict = {}
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        toml_data = _parse_toml(_read(pyproject))

    # Load .editorconfig
    editorconfig_sections: dict = {}
    ec = repo / ".editorconfig"
    if ec.exists():
        editorconfig_sections = _parse_editorconfig(ec)

    result: dict = {}

    # Python
    py = _detect_python(repo, toml_data)
    if py:
        ec_py = _parse_editorconfig_for_lang(editorconfig_sections, "python")
        if ec_py:
            py["editorconfig"] = ec_py
        result["python"] = py

    # TypeScript / JavaScript (share config files, reported under "typescript")
    ts = _detect_typescript(repo)
    if ts:
        ec_ts = _parse_editorconfig_for_lang(editorconfig_sections, "typescript")
        if ec_ts:
            ts["editorconfig"] = ec_ts
        result["typescript"] = ts

    # Go
    go = _detect_go(repo)
    if (repo / "go.mod").exists() or list(repo.rglob("*.go")):
        ec_go = _parse_editorconfig_for_lang(editorconfig_sections, "go")
        if ec_go:
            go["editorconfig"] = ec_go
        result["go"] = go

    # Rust
    rust = _detect_rust(repo)
    if (repo / "Cargo.toml").exists() or list(repo.rglob("*.rs")):
        ec_rs = _parse_editorconfig_for_lang(editorconfig_sections, "rust")
        if ec_rs:
            rust["editorconfig"] = ec_rs
        result["rust"] = rust

    # Global editorconfig
    if editorconfig_sections:
        result["editorconfig"] = editorconfig_sections

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
        result = detect(args.repo)
    except Exception as exc:
        result = {"error": str(exc), "script": "config"}

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
