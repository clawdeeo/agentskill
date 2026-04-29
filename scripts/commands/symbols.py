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
from common.languages import language_for_path
from lib.cli_entrypoint import run_command_main

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
            fpath = Path(dirpath) / fn
            suffix = fpath.suffix.lower()

            if suffix in exts:
                found.append(fpath)
            elif ".sh" in exts and ".bash" in exts:
                spec = language_for_path(fpath)

                if spec and spec.id == "bash":
                    found.append(fpath)

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


def _strip_c_family_comments(source: str) -> str:
    source = re.sub(r"//.*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _strip_swift_comments(source: str) -> str:
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


def _extract_csharp(files: list[Path]) -> dict:
    type_re = re.compile(
        r"^\s*(?:public|private|protected|internal)?\s*(?:abstract\s+|static\s+|sealed\s+|partial\s+)?"
        r"(class|interface|struct|enum|record)\s+([A-Za-z_]\w*)",
        re.MULTILINE,
    )

    method_re = re.compile(
        r"^\s*(?:public|private|protected|internal)\s+(?:static\s+|virtual\s+|override\s+|async\s+)?"
        r"[\w<>\[\], ?]+\s+([A-Za-z_]\w*)\s*\(",
        re.MULTILINE,
    )

    classes: list[str] = []
    interfaces: list[str] = []
    structs: list[str] = []
    enums: list[str] = []
    records: list[str] = []
    methods: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)

        try:
            source = _strip_c_family_comments(read_text(fpath))
        except Exception:
            continue

        for kind, name in type_re.findall(source):
            if kind == "class":
                classes.append(name)
            elif kind == "interface":
                interfaces.append(name)
            elif kind == "struct":
                structs.append(name)
            elif kind == "enum":
                enums.append(name)
            elif kind == "record":
                records.append(name)

        for name in method_re.findall(source):
            if name not in {"if", "for", "while", "switch", "catch", "foreach"}:
                methods.append(name)

    result: dict = {
        "classes": _pattern_summary(classes),
        "methods": _pattern_summary(methods),
        "files": _pattern_summary(file_names),
    }

    if interfaces:
        result["interfaces"] = _pattern_summary(interfaces)

    if structs:
        result["structs"] = _pattern_summary(structs)

    if enums:
        result["enums"] = _pattern_summary(enums)

    if records:
        result["records"] = _pattern_summary(records)

    return result


def _extract_c(files: list[Path]) -> dict:
    source_files = [f for f in files if f.suffix.lower() == ".c"]
    all_files = files if source_files else files

    function_re = re.compile(
        r"^\s*(?!if\b|for\b|while\b|switch\b|return\b)(?:[A-Za-z_][\w\s\*]+)\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{",
        re.MULTILINE,
    )

    struct_re = re.compile(r"^\s*struct\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)
    enum_re = re.compile(r"^\s*enum\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)

    typedef_re = re.compile(
        r"^\s*typedef\s+(?:struct|enum|union)?\s*[A-Za-z_]*\s*([A-Za-z_]\w*)\s*;",
        re.MULTILINE,
    )

    macro_re = re.compile(r"^\s*#define\s+([A-Z_][A-Z0-9_]*)\b", re.MULTILINE)

    functions: list[str] = []
    structs: list[str] = []
    enums: list[str] = []
    typedefs: list[str] = []
    macros: list[str] = []
    file_names: list[str] = []

    for fpath in all_files:
        file_names.append(fpath.stem)

        try:
            source = _strip_c_family_comments(read_text(fpath))
        except Exception:
            continue

        if fpath.suffix.lower() == ".c":
            functions.extend(function_re.findall(source))

        structs.extend(struct_re.findall(source))
        enums.extend(enum_re.findall(source))
        typedefs.extend(typedef_re.findall(source))
        macros.extend(macro_re.findall(source))

    result: dict = {
        "functions": _pattern_summary(functions),
        "files": _pattern_summary(file_names),
    }

    if structs:
        result["structs"] = _pattern_summary(structs)

    if enums:
        result["enums"] = _pattern_summary(enums)

    if typedefs:
        result["typedefs"] = _pattern_summary(typedefs)

    if macros:
        result["macros"] = _pattern_summary(macros)

    return result


def _extract_cpp(files: list[Path]) -> dict:
    source_files = [
        f
        for f in files
        if f.suffix.lower() in {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"}
    ]

    namespace_re = re.compile(r"^\s*namespace\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)

    template_re = re.compile(
        r"^\s*template\s*<[^>]+>\s*(?:class|struct)?\s*([A-Za-z_]\w*)?",
        re.MULTILINE,
    )

    class_re = re.compile(r"^\s*class\s+([A-Za-z_]\w*)", re.MULTILINE)
    struct_re = re.compile(r"^\s*struct\s+([A-Za-z_]\w*)", re.MULTILINE)
    enum_re = re.compile(r"^\s*enum(?:\s+class)?\s+([A-Za-z_]\w*)", re.MULTILINE)

    function_re = re.compile(
        r"^\s*(?!if\b|for\b|while\b|switch\b|return\b)(?:[A-Za-z_][\w:\s<>\*&]+)\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{",
        re.MULTILINE,
    )

    namespaces: list[str] = []
    classes: list[str] = []
    structs: list[str] = []
    enums: list[str] = []
    functions: list[str] = []
    templates: list[str] = []
    file_names: list[str] = []

    for fpath in source_files:
        file_names.append(fpath.stem)

        try:
            source = _strip_c_family_comments(read_text(fpath))
        except Exception:
            continue

        namespaces.extend(namespace_re.findall(source))
        classes.extend(class_re.findall(source))
        structs.extend(struct_re.findall(source))
        enums.extend(enum_re.findall(source))
        functions.extend(function_re.findall(source))

        for name in template_re.findall(source):
            if name:
                templates.append(name)

    result: dict = {
        "functions": _pattern_summary(functions),
        "files": _pattern_summary(file_names),
    }

    if namespaces:
        result["namespaces"] = _pattern_summary(namespaces)

    if classes:
        result["classes"] = _pattern_summary(classes)

    if structs:
        result["structs"] = _pattern_summary(structs)

    if enums:
        result["enums"] = _pattern_summary(enums)

    if templates:
        result["templates"] = _pattern_summary(templates)

    return result


def _extract_ruby(files: list[Path]) -> dict:
    source_files = files
    module_re = re.compile(r"^\s*module\s+([A-Za-z_]\w*)", re.MULTILINE)
    class_re = re.compile(r"^\s*class\s+([A-Za-z_]\w*)", re.MULTILINE)
    method_re = re.compile(r"^\s*def\s+([A-Za-z_]\w*[!?=]?)", re.MULTILINE)
    class_method_re = re.compile(r"^\s*def\s+self\.([A-Za-z_]\w*[!?=]?)", re.MULTILINE)

    modules: list[str] = []
    classes: list[str] = []
    methods: list[str] = []
    class_methods: list[str] = []
    file_names: list[str] = []

    for fpath in source_files:
        file_names.append(fpath.stem)

        try:
            source = re.sub(r"#.*", "", read_text(fpath))
        except Exception:
            continue

        modules.extend(module_re.findall(source))
        classes.extend(class_re.findall(source))
        class_methods.extend(class_method_re.findall(source))

        for name in method_re.findall(source):
            if not any(name == method for method in class_methods):
                methods.append(name)

    result: dict = {
        "classes": _pattern_summary(classes),
        "methods": _pattern_summary(methods),
        "files": _pattern_summary(file_names),
    }

    if modules:
        result["modules"] = _pattern_summary(modules)

    if class_methods:
        result["class_methods"] = _pattern_summary(class_methods)

    return result


def _extract_php(files: list[Path]) -> dict:
    type_re = re.compile(
        r"^\s*(class|interface|trait|enum)\s+([A-Za-z_]\w*)",
        re.MULTILINE,
    )

    function_re = re.compile(r"^\s*function\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE)

    method_re = re.compile(
        r"^\s*(?:public|protected|private)\s+function\s+([A-Za-z_]\w*)\s*\(",
        re.MULTILINE,
    )

    classes: list[str] = []
    interfaces: list[str] = []
    traits: list[str] = []
    enums: list[str] = []
    functions: list[str] = []
    methods: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)

        try:
            source = _strip_c_family_comments(read_text(fpath))
        except Exception:
            continue

        for kind, name in type_re.findall(source):
            if kind == "class":
                classes.append(name)
            elif kind == "interface":
                interfaces.append(name)
            elif kind == "trait":
                traits.append(name)
            elif kind == "enum":
                enums.append(name)

        methods.extend(method_re.findall(source))

        for name in function_re.findall(source):
            if name not in methods:
                functions.append(name)

    result: dict = {
        "classes": _pattern_summary(classes),
        "functions": _pattern_summary(functions),
        "methods": _pattern_summary(methods),
        "files": _pattern_summary(file_names),
    }

    if interfaces:
        result["interfaces"] = _pattern_summary(interfaces)

    if traits:
        result["traits"] = _pattern_summary(traits)

    if enums:
        result["enums"] = _pattern_summary(enums)

    return result


def _extract_bash(files: list[Path]) -> dict:
    function_re = re.compile(
        r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{", re.MULTILINE
    )

    functions: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem or fpath.name)

        try:
            source = read_text(fpath)
        except Exception:
            continue

        functions.extend(function_re.findall(source))

    return {
        "functions": _pattern_summary(functions),
        "files": _pattern_summary(file_names),
    }


def _extract_swift(files: list[Path]) -> dict:
    type_re = re.compile(
        r"^\s*(?:public|open|internal|private|fileprivate)?\s*(?:final\s+)?(struct|class|enum|protocol)\s+([A-Za-z_]\w*)",
        re.MULTILINE,
    )

    function_re = re.compile(
        r"^\s*(?:public|open|internal|private|fileprivate)?\s*func\s+([A-Za-z_]\w*)\s*\(",
        re.MULTILINE,
    )

    extension_re = re.compile(r"^\s*extension\s+([A-Za-z_]\w*)", re.MULTILINE)

    structs: list[str] = []
    classes: list[str] = []
    enums: list[str] = []
    protocols: list[str] = []
    functions: list[str] = []
    extensions: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)

        try:
            source = _strip_swift_comments(read_text(fpath))
        except Exception:
            continue

        for kind, name in type_re.findall(source):
            if kind == "struct":
                structs.append(name)
            elif kind == "class":
                classes.append(name)
            elif kind == "enum":
                enums.append(name)
            elif kind == "protocol":
                protocols.append(name)

        functions.extend(function_re.findall(source))
        extensions.extend(extension_re.findall(source))

    result: dict = {
        "functions": _pattern_summary(functions),
        "files": _pattern_summary(file_names),
    }

    if structs:
        result["structs"] = _pattern_summary(structs)

    if classes:
        result["classes"] = _pattern_summary(classes)

    if enums:
        result["enums"] = _pattern_summary(enums)

    if protocols:
        result["protocols"] = _pattern_summary(protocols)

    if extensions:
        result["extensions"] = _pattern_summary(extensions)

    return result


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


def _extract_objectivec(files: list[Path]) -> dict:
    interface_re = re.compile(r"^\s*@interface\s+([A-Za-z_]\w*)", re.MULTILINE)

    implementation_re = re.compile(
        r"^\s*@implementation\s+([A-Za-z_]\w*)", re.MULTILINE
    )

    protocol_re = re.compile(r"^\s*@protocol\s+([A-Za-z_]\w*)", re.MULTILINE)
    method_re = re.compile(r"^\s*-\s*\([^)]+\)\s*([A-Za-z_]\w*)", re.MULTILINE)
    class_method_re = re.compile(r"^\s*\+\s*\([^)]+\)\s*([A-Za-z_]\w*)", re.MULTILINE)

    enum_re = re.compile(
        r"NS_ENUM\s*\([^)]+,\s*([A-Za-z_]\w*)\)|^\s*typedef\s+enum\s+[A-Za-z_]*\s*\{",
        re.MULTILINE,
    )

    interfaces: list[str] = []
    implementations: list[str] = []
    protocols: list[str] = []
    methods: list[str] = []
    class_methods: list[str] = []
    enums: list[str] = []
    file_names: list[str] = []

    for fpath in files:
        file_names.append(fpath.stem)

        try:
            source = _strip_c_family_comments(read_text(fpath))
        except Exception:
            continue

        interfaces.extend(interface_re.findall(source))
        implementations.extend(implementation_re.findall(source))
        protocols.extend(protocol_re.findall(source))
        methods.extend(method_re.findall(source))
        class_methods.extend(class_method_re.findall(source))

        for match in enum_re.findall(source):
            if match:
                enums.append(match)

    result: dict = {
        "files": _pattern_summary(file_names),
        "methods": _pattern_summary(methods),
    }

    if interfaces:
        result["interfaces"] = _pattern_summary(interfaces)

    if implementations:
        result["implementations"] = _pattern_summary(implementations)

    if protocols:
        result["protocols"] = _pattern_summary(protocols)

    if class_methods:
        result["class_methods"] = _pattern_summary(class_methods)

    if enums:
        result["enums"] = _pattern_summary(enums)

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

    if not lang_filter or lang_filter == "csharp":
        _run("csharp", [".cs"], _extract_csharp)

    if not lang_filter or lang_filter == "c":
        _run("c", [".c", ".h"], _extract_c)

    if not lang_filter or lang_filter == "cpp":
        _run("cpp", [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"], _extract_cpp)

    if not lang_filter or lang_filter == "ruby":
        _run("ruby", [".rb"], _extract_ruby)

    if not lang_filter or lang_filter == "php":
        _run("php", [".php"], _extract_php)

    if not lang_filter or lang_filter == "bash":
        _run("bash", [".sh", ".bash"], _extract_bash)

    if not lang_filter or lang_filter == "swift":
        _run("swift", [".swift"], _extract_swift)

    if not lang_filter or lang_filter == "objectivec":
        files = _collect_objectivec_files(repo)

        if files:
            try:
                result["objectivec"] = _extract_objectivec(files)
            except Exception as exc:
                result["objectivec"] = {"error": str(exc)}

    return result


def main(argv: list[str] | None = None) -> int:
    return run_command_main(
        argv=argv,
        description=__doc__,
        command_fn=extract_symbols,
        script_name="symbols",
        supports_lang=True,
    )


if __name__ == "__main__":
    sys.exit(main())
