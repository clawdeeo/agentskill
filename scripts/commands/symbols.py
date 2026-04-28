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
import os
import re
import sys
from collections import Counter
from pathlib import Path

from common.constants import should_skip_dir
from common.fs import read_text, validate_repo
from lib.output import run_and_output

MIN_NAME_LENGTH = 4
MAX_AFFIX_LENGTH = 8
MAX_AFFIX_EXAMPLES = 3
MAX_AFFIX_CANDIDATES = 30
MAX_AFFIXES_RETURNED = 10

SKIP_AFFIXES = {
    "er",
    "ed",
    "ing",
    "ion",
    "al",
    "tion",
    "le",
    "or",
    "is",
    "at",
    "get",
    "set",
    "has",
    "is_",
    "_is",
    "on",
    "re",
    "un",
    "de",
}


def _collect_files(repo: Path, exts: list[str]) -> list[Path]:
    found = []

    for dirpath, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

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


def _collect_affix_counts(
    names: list[str], kind: str, min_len: int
) -> tuple[Counter, dict[str, list[str]]]:
    """Count prefix or suffix occurrences across names. kind is 'prefix' or 'suffix'."""
    counts: Counter = Counter()
    examples: dict[str, list[str]] = {}

    for name in names:
        if len(name) < MIN_NAME_LENGTH or (
            name.startswith("__") and name.endswith("__")
        ):
            continue

        clean = name.lstrip("_")

        for length in range(min_len, min(MAX_AFFIX_LENGTH + 1, len(clean))):
            affix = clean[:length] if kind == "prefix" else clean[-length:]
            valid = affix.isalpha() or (
                "_" in affix
                and (affix.endswith("_") if kind == "prefix" else affix.startswith("_"))
            )
            if valid:
                counts[affix] += 1
                examples.setdefault(affix, [])

                if len(examples[affix]) < MAX_AFFIX_EXAMPLES:
                    examples[affix].append(name)

    return counts, examples


def _affix_entries(
    counts: Counter,
    examples: dict[str, list[str]],
    kind: str,
    min_count: int,
    min_len: int,
) -> list[dict]:
    """Build result dicts for the top affix candidates."""
    entries = []

    for affix, count in counts.most_common(MAX_AFFIX_CANDIDATES):
        if count < min_count or affix.lower() in SKIP_AFFIXES or len(affix) < min_len:
            continue

        if kind == "prefix":
            pattern = (
                f"{affix}_ prefix" if not affix.endswith("_") else f"{affix} prefix"
            )
        else:
            pattern = (
                f"_{affix} suffix" if not affix.startswith("_") else f"{affix} suffix"
            )

        entries.append(
            {"pattern": pattern, "count": count, "examples": examples.get(affix, [])}
        )

    return entries


def _dedupe_sorted(results: list[dict]) -> list[dict]:
    """Deduplicate by pattern key, return top MAX_AFFIXES_RETURNED sorted by count."""
    seen: set[str] = set()
    unique: list[dict] = []

    for r in sorted(results, key=lambda x: -x["count"]):
        if r["pattern"] not in seen:
            seen.add(r["pattern"])
            unique.append(r)

        if len(unique) >= MAX_AFFIXES_RETURNED:
            break

    return unique


def _find_affixes(names: list[str], min_count: int = 5, min_len: int = 2) -> list[dict]:
    """Find recurring prefixes and suffixes appearing in 5+ names."""
    prefix_counts, prefix_examples = _collect_affix_counts(names, "prefix", min_len)
    suffix_counts, suffix_examples = _collect_affix_counts(names, "suffix", min_len)

    results = _affix_entries(
        prefix_counts, prefix_examples, "prefix", min_count, min_len
    ) + _affix_entries(suffix_counts, suffix_examples, "suffix", min_count, min_len)

    return _dedupe_sorted(results)


def _pattern_summary(names: list[str]) -> dict:
    if not names:
        return {"total": 0, "patterns": {}, "codebase_specific": []}

    total = len(names)
    counts = Counter(_classify(n) for n in names)

    patterns = {
        k: {"count": v, "pct": round(v / total * 100, 1)}
        for k, v in sorted(counts.items(), key=lambda x: -x[1])
    }

    return {
        "total": total,
        "patterns": patterns,
        "codebase_specific": _find_affixes(names),
    }


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
            source = read_text(fpath)
            tree = ast.parse(source)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                functions.append(name)

                if name.startswith("__") and not name.endswith("__"):
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
    export_func_re = re.compile(
        r"(?:^|\s)(?:export\s+)(?:async\s+)?function\s+(\w+)",
        re.MULTILINE,
    )
    default_func_re = re.compile(
        r"(?:^|\s)(?:export\s+)?(?:default\s+)(?:async\s+)?function\s+(\w+)",
        re.MULTILINE,
    )
    plain_func_re = re.compile(
        r"(?:^|\s)(?:async\s+)?function\s+(\w+)",
        re.MULTILINE,
    )

    export_class_re = re.compile(
        r"(?:^|\s)(?:export\s+)(?:abstract\s+)?class\s+(\w+)",
        re.MULTILINE,
    )
    default_class_re = re.compile(
        r"(?:^|\s)(?:export\s+)?(?:default\s+)(?:abstract\s+)?class\s+(\w+)",
        re.MULTILINE,
    )
    plain_class_re = re.compile(
        r"(?:^|\s)(?:abstract\s+)?class\s+(\w+)",
        re.MULTILINE,
    )

    export_iface_re = re.compile(
        r"(?:^|\s)(?:export\s+)?interface\s+(\w+)",
        re.MULTILINE,
    )
    export_type_re = re.compile(
        r"(?:^|\s)(?:export\s+)?type\s+(\w+)\s*=",
        re.MULTILINE,
    )

    export_arrow_re = re.compile(
        r"(?:^|\s)export\s+const\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    )
    plain_arrow_re = re.compile(
        r"(?:^|\s)const\s+(\w+)\s*=\s*(?:async\s+)?\(",
        re.MULTILINE,
    )
    export_func_expr_re = re.compile(
        r"(?:^|\s)export\s+const\s+(\w+)\s*=\s*function",
        re.MULTILINE,
    )

    const_re = re.compile(
        r"(?:^|\s)export\s+const\s+([A-Z_][A-Z0-9_]*)\s*[=:]",
        re.MULTILINE,
    )

    functions: list[str] = []
    classes: list[str] = []
    interfaces: list[str] = []
    types: list[str] = []
    constants: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem.replace(".test", "").replace(".spec", ""))

        try:
            source = read_text(fpath)
        except Exception:
            continue

        for m in export_func_re.finditer(source):
            functions.append(m.group(1))
        for m in default_func_re.finditer(source):
            functions.append(m.group(1))
        for m in plain_func_re.finditer(source):
            functions.append(m.group(1))

        for m in export_class_re.finditer(source):
            classes.append(m.group(1))
        for m in default_class_re.finditer(source):
            classes.append(m.group(1))
        for m in plain_class_re.finditer(source):
            classes.append(m.group(1))

        for m in export_iface_re.finditer(source):
            interfaces.append(m.group(1))
        for m in export_type_re.finditer(source):
            types.append(m.group(1))

        for m in export_arrow_re.finditer(source):
            functions.append(m.group(1))
        for m in plain_arrow_re.finditer(source):
            functions.append(m.group(1))
        for m in export_func_expr_re.finditer(source):
            functions.append(m.group(1))

        for m in const_re.finditer(source):
            constants.append(m.group(1))

    result: dict = {
        "functions": _pattern_summary(functions),
        "classes": _pattern_summary(classes),
        "constants": _pattern_summary(constants),
        "files": _pattern_summary(file_names),
    }

    if interfaces:
        result["interfaces"] = _pattern_summary(interfaces)

    if types:
        result["types"] = _pattern_summary(types)

    return result


def _strip_go_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _extract_go(files: list[Path]) -> dict:
    func_re = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(")
    method_re = re.compile(r"^func\s+\((\w+)\s+\*?(\w+)\)\s+(\w+)\s*\(")
    type_struct_re = re.compile(r"^type\s+(\w+)\s+struct")
    type_iface_re = re.compile(r"^type\s+(\w+)\s+interface")
    type_alias_re = re.compile(
        r"^type\s+(\w+)\s+(?:string|int|float64|bool|error|byte|rune|any)"
    )
    const_re = re.compile(r"^\s+(\w+)\s*(?:=|[A-Z])")
    var_re = re.compile(r"^var\s+(\w+)")

    functions: list[str] = []
    methods: list[str] = []
    structs: list[str] = []
    interfaces: list[str] = []
    type_aliases: list[str] = []
    constants: list[str] = []
    variables: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)

        try:
            source = _strip_go_comments(read_text(fpath))
        except Exception:
            continue

        lines = source.splitlines()
        constants.extend(_extract_go_constants(lines, const_re))

        for line in lines:
            m = func_re.match(line)
            if m:
                functions.append(m.group(1))

            m = method_re.match(line)
            if m:
                methods.append(m.group(3))

            m = type_struct_re.match(line)
            if m:
                structs.append(m.group(1))

            m = type_iface_re.match(line)
            if m:
                interfaces.append(m.group(1))

            m = type_alias_re.match(line)
            if m:
                type_aliases.append(m.group(1))

            m = var_re.match(line)
            if m:
                variables.append(m.group(1))

    result: dict = {
        "functions": _pattern_summary(functions),
        "methods": _pattern_summary(methods),
        "types": _pattern_summary(structs),
        "constants": _pattern_summary(constants),
        "files": _pattern_summary(file_names),
    }

    if interfaces:
        result["interfaces"] = _pattern_summary(interfaces)

    if type_aliases:
        result["type_aliases"] = _pattern_summary(type_aliases)

    if variables:
        result["variables"] = _pattern_summary(variables)

    return result


def _extract_go_constants(lines: list[str], const_re: re.Pattern) -> list[str]:
    constants: list[str] = []
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

    return constants


def _strip_rust_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _strip_jvm_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _extract_java(files: list[Path]) -> dict:
    decl_re = re.compile(
        r"^\s*(?P<mods>(?:public|private|protected|static|final|abstract)\s+)*"
        r"(?P<kind>class|interface|enum|@interface)\s+"
        r"(?P<name>[A-Za-z_]\w*)",
        re.MULTILINE,
    )

    method_re = re.compile(
        r"^\s*(?P<mods>(?:public|private|protected|static|final|abstract|synchronized)\s+)*"
        r"(?:(?P<return>[A-Za-z_][\w<>\[\], ?]*)\s+)?"
        r"(?P<name>[A-Za-z_]\w*)\s*\(",
        re.MULTILINE,
    )

    classes: list[str] = []
    interfaces: list[str] = []
    enums: list[str] = []
    annotations: list[str] = []
    methods: list[str] = []
    constructors: list[str] = []
    constants: list[str] = []
    file_names: list[str] = []
    declared_types: set[str] = set()

    for fpath in files:
        file_names.append(fpath.stem)

        try:
            source = _strip_jvm_comments(read_text(fpath))
        except Exception:
            continue

        for match in decl_re.finditer(source):
            kind = match.group("kind")
            name = match.group("name")
            declared_types.add(name)

            if kind == "class":
                classes.append(name)
            elif kind == "interface":
                interfaces.append(name)
            elif kind == "enum":
                enums.append(name)
            elif kind == "@interface":
                annotations.append(name)

        for match in method_re.finditer(source):
            name = match.group("name")
            return_type = match.group("return")

            if name in {"if", "for", "while", "switch", "catch", "return", "new"}:
                continue

            if return_type is None and name in declared_types:
                constructors.append(name)
            elif return_type is not None:
                methods.append(name)

        for match in re.finditer(
            r"^\s*(?:public|private|protected)?\s*static\s+final\s+[\w<>\[\], ?]+\s+([A-Z_][A-Z0-9_]*)\b",
            source,
            re.MULTILINE,
        ):
            constants.append(match.group(1))

    result: dict = {
        "classes": _pattern_summary(classes),
        "methods": _pattern_summary(methods),
        "constants": _pattern_summary(constants),
        "files": _pattern_summary(file_names),
    }

    if interfaces:
        result["interfaces"] = _pattern_summary(interfaces)

    if enums:
        result["enums"] = _pattern_summary(enums)

    if annotations:
        result["annotations"] = _pattern_summary(annotations)

    if constructors:
        result["constructors"] = _pattern_summary(constructors)

    return result


def _extract_kotlin(files: list[Path]) -> dict:
    type_re = re.compile(
        r"^\s*(?P<enum_mods>(?:public|private|protected|internal)\s+)*enum\s+class\s+(?P<enum_name>[A-Za-z_]\w*)|"
        r"^\s*(?P<mods>(?:public|private|protected|internal|open|abstract|sealed|data)\s+)*"
        r"(?P<kind>class|interface|object)\s+(?P<name>[A-Za-z_]\w*)",
        re.MULTILINE,
    )

    function_re = re.compile(
        r"^\s*(?P<mods>(?:public|private|protected|internal|override|suspend|inline|tailrec|operator|infix)\s+)*"
        r"fun\s+(?:[A-Za-z_][\w.<>?, ]+\.)?(?P<name>[A-Za-z_]\w*)\s*\(",
        re.MULTILINE,
    )

    property_re = re.compile(
        r"^\s*(?P<mods>(?:public|private|protected|internal|lateinit|override)\s+)*"
        r"(?P<const>const\s+)?(?:val|var)\s+(?P<name>[A-Za-z_]\w*)\b",
        re.MULTILINE,
    )

    classes: list[str] = []
    interfaces: list[str] = []
    objects: list[str] = []
    enums: list[str] = []
    functions: list[str] = []
    properties: list[str] = []
    constants: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)

        try:
            source = _strip_jvm_comments(read_text(fpath))
        except Exception:
            continue

        for match in type_re.finditer(source):
            kind = match.group("kind")

            if match.group("enum_name"):
                enums.append(match.group("enum_name"))
                continue

            name = match.group("name")
            if not kind or not name:
                continue

            if kind == "class":
                classes.append(name)
            elif kind == "interface":
                interfaces.append(name)
            elif kind == "object":
                objects.append(name)

        for match in function_re.finditer(source):
            functions.append(match.group("name"))

        for match in property_re.finditer(source):
            name = match.group("name")

            if match.group("const"):
                constants.append(name)
            else:
                properties.append(name)

    result: dict = {
        "classes": _pattern_summary(classes),
        "functions": _pattern_summary(functions),
        "constants": _pattern_summary(constants),
        "files": _pattern_summary(file_names),
    }

    if interfaces:
        result["interfaces"] = _pattern_summary(interfaces)

    if objects:
        result["objects"] = _pattern_summary(objects)

    if enums:
        result["enums"] = _pattern_summary(enums)

    if properties:
        result["properties"] = _pattern_summary(properties)

    return result


def _extract_rust(files: list[Path]) -> dict:
    func_re = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE)
    struct_re = re.compile(r"^\s*(?:pub\s+)?struct\s+(\w+)", re.MULTILINE)
    enum_re = re.compile(r"^\s*(?:pub\s+)?enum\s+(\w+)", re.MULTILINE)
    trait_re = re.compile(r"^\s*(?:pub\s+)?trait\s+(\w+)", re.MULTILINE)
    impl_re = re.compile(r"^\s*impl\s+(?:(?:\w+)\s+for\s+)?(\w+)", re.MULTILINE)
    const_re = re.compile(r"^\s*(?:pub\s+)?const\s+(\w+)", re.MULTILINE)
    static_re = re.compile(r"^\s*(?:pub\s+)?static\s+(\w+)", re.MULTILINE)

    functions: list[str] = []
    structs: list[str] = []
    enums: list[str] = []
    traits: list[str] = []
    impls: list[str] = []
    constants: list[str] = []
    statics: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)

        try:
            source = _strip_rust_comments(read_text(fpath))
        except Exception:
            continue

        for m in func_re.finditer(source):
            functions.append(m.group(1))

        for m in struct_re.finditer(source):
            structs.append(m.group(1))

        for m in enum_re.finditer(source):
            enums.append(m.group(1))

        for m in trait_re.finditer(source):
            traits.append(m.group(1))

        for m in impl_re.finditer(source):
            impls.append(m.group(1))

        for m in const_re.finditer(source):
            constants.append(m.group(1))

        for m in static_re.finditer(source):
            statics.append(m.group(1))

    result: dict = {
        "functions": _pattern_summary(functions),
        "structs": _pattern_summary(structs),
        "enums": _pattern_summary(enums),
        "constants": _pattern_summary(constants),
        "files": _pattern_summary(file_names),
    }

    if traits:
        result["traits"] = _pattern_summary(traits)

    if impls:
        result["impls"] = _pattern_summary(impls)

    if statics:
        result["statics"] = _pattern_summary(statics)

    return result


def extract_symbols(repo_path: str, lang_filter: str | None = None) -> dict:
    try:
        repo = validate_repo(repo_path)
    except ValueError as exc:
        return {"error": str(exc), "script": "symbols"}

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
        _run(
            lang,
            [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"],
            lambda files: _extract_ts(files, lang),
        )

    if not lang_filter or lang_filter == "go":
        _run("go", [".go"], _extract_go)

    if not lang_filter or lang_filter == "rust":
        _run("rust", [".rs"], _extract_rust)

    if not lang_filter or lang_filter == "java":
        _run("java", [".java"], _extract_java)

    if not lang_filter or lang_filter == "kotlin":
        _run("kotlin", [".kt", ".kts"], _extract_kotlin)

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
        extract_symbols,
        repo=args.repo,
        pretty=args.pretty,
        script_name="symbols",
        extra_kwargs={"lang_filter": args.lang},
    )


if __name__ == "__main__":
    sys.exit(main())
