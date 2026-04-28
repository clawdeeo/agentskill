from commands.symbols import _classify, _find_affixes, extract_symbols
from test_support import create_repo, create_sample_repo


def test_symbols_extracts_python_patterns(tmp_path):
    repo = create_sample_repo(tmp_path)
    result = extract_symbols(str(repo), "python")

    assert result["python"]["functions"]["total"] >= 3
    assert result["python"]["classes"]["patterns"]["PascalCase"]["count"] >= 1


def test_symbols_classification_and_affixes():
    assert _classify("__init__") == "dunder"
    assert _classify("_hidden") == "private"
    assert _classify("VALUE_NAME") == "SCREAMING_SNAKE_CASE"
    assert _classify("snake_case") == "snake_case"
    assert _classify("PascalCase") == "PascalCase"
    assert _classify("camelCase") == "camelCase"
    assert _classify("misc") == "other"

    affixes = _find_affixes(
        ["buildGraph", "buildTree", "buildValue", "buildNode", "buildThing"]
    )

    assert any(
        entry["pattern"] == "bu_ prefix" or entry["pattern"] == "build_ prefix"
        for entry in affixes
    )


def test_symbols_extracts_typescript_and_go(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "src/app.ts": (
                "export function buildThing() {}\n"
                "const makeWidget = () => {}\n"
                "export class WidgetService {}\n"
                "export interface WidgetShape {}\n"
                "export type WidgetType = string\n"
                "export const VALUE_NAME = 1\n"
            ),
            "pkg/main.go": (
                "package main\n"
                "type Worker struct{}\n"
                "const (\n    MainValue = 1\n)\n"
                "var ExportedValue string\n"
                "func RunThing() {}\n"
            ),
        },
    )

    result = extract_symbols(str(repo))

    assert result["typescript"]["classes"]["total"] >= 2

    assert (
        result["typescript"]["constants"]["patterns"]["SCREAMING_SNAKE_CASE"]["count"]
        >= 1
    )

    assert result["go"]["functions"]["total"] >= 1
    assert result["go"]["constants"]["total"] >= 1
    assert result["go"]["variables"]["total"] >= 1


def test_symbols_extracts_java_and_kotlin(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "src/main/java/com/acme/UserService.java": (
                "package com.acme;\n\n"
                "public class UserService {\n"
                "    public UserService() {}\n"
                "    public void start() {}\n"
                '    private String helper() { return ""; }\n'
                "}\n\n"
                "interface Store {}\n"
                "enum Status {}\n"
                "@interface Marker {}\n"
            ),
            "src/main/kotlin/com/acme/App.kt": (
                "package com.acme\n\n"
                "class UserService\n"
                "data class User(val id: String)\n"
                "sealed class Result\n"
                "interface Store\n"
                "object AppConfig\n"
                "enum class Status { OK }\n\n"
                "fun start() {}\n"
                "private fun helper() {}\n"
                'const val VERSION = "1"\n'
                'val name = "x"\n'
            ),
        },
    )

    result = extract_symbols(str(repo))

    assert result["java"]["classes"]["patterns"]["PascalCase"]["count"] >= 1
    assert result["java"]["methods"]["total"] >= 2
    assert result["java"]["interfaces"]["total"] >= 1
    assert result["java"]["enums"]["total"] >= 1
    assert result["java"]["annotations"]["total"] >= 1
    assert result["java"]["constructors"]["total"] >= 1

    assert result["kotlin"]["classes"]["total"] >= 3
    assert result["kotlin"]["interfaces"]["total"] >= 1
    assert result["kotlin"]["objects"]["total"] >= 1
    assert result["kotlin"]["enums"]["total"] >= 1
    assert result["kotlin"]["functions"]["total"] >= 2
    assert result["kotlin"]["constants"]["total"] >= 1
    assert result["kotlin"]["properties"]["total"] >= 1


def test_symbols_reports_invalid_repo_paths(tmp_path):
    missing = tmp_path / "missing"

    assert extract_symbols(str(missing)) == {
        "error": f"path does not exist: {missing}",
        "script": "symbols",
    }
