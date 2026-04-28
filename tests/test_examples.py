from pathlib import Path

from commands.config import detect
from commands.graph import build_graph
from commands.measure import measure
from commands.scan import scan
from commands.symbols import extract_symbols
from commands.tests import analyze_tests
from test_support import EXAMPLES_DIR

SUPPORTED_EXAMPLE_DIRS = {
    "python",
    "javascript",
    "typescript",
    "go",
    "rust",
    "java",
    "kotlin",
    "csharp",
    "c",
    "cpp",
    "ruby",
    "php",
    "swift",
    "objectivec",
    "bash",
}


def _example_path(name: str) -> Path:
    return EXAMPLES_DIR / name


def _assert_no_error_payload(result):
    assert isinstance(result, dict)
    assert "error" not in result


def _symbol_and_test_lang(example_name: str) -> str:
    return "typescript" if example_name == "javascript" else example_name


def test_examples_include_every_supported_language_directory():
    dirs = {path.name for path in EXAMPLES_DIR.iterdir() if path.is_dir()}

    assert dirs >= SUPPORTED_EXAMPLE_DIRS
    assert "mixed" in dirs


def test_examples_readme_exists():
    assert (EXAMPLES_DIR / "README.md").exists()


def test_all_analyzers_run_on_every_language_example():
    for language in sorted(SUPPORTED_EXAMPLE_DIRS):
        repo = _example_path(language)

        scan_result = scan(str(repo))
        _assert_no_error_payload(scan_result)
        assert language in scan_result["summary"]["by_language"] or (
            language == "objectivec"
            and "objectivec" in scan_result["summary"]["by_language"]
        )

        measure_result = measure(str(repo))
        _assert_no_error_payload(measure_result)
        assert language in measure_result or (
            language == "objectivec" and "objectivec" in measure_result
        )

        graph_result = build_graph(str(repo))
        _assert_no_error_payload(graph_result)
        assert language in graph_result

        symbols_result = extract_symbols(str(repo))
        _assert_no_error_payload(symbols_result)
        assert _symbol_and_test_lang(language) in symbols_result

        tests_result = analyze_tests(str(repo))
        _assert_no_error_payload(tests_result)
        assert _symbol_and_test_lang(language) in tests_result


def test_language_examples_produce_expected_behavioral_signals():
    py_graph = build_graph(str(_example_path("python")))
    assert {"from": "src.app", "to": "src.util", "line": 1} in py_graph["python"][
        "edges"
    ]

    js_graph = build_graph(str(_example_path("javascript")))
    assert {"from": "src/index.js", "to": "src/util.js", "line": 1} in js_graph[
        "javascript"
    ]["edges"]

    ts_graph = build_graph(str(_example_path("typescript")))
    assert {"from": "src/index.ts", "to": "src/user.ts", "line": 1} in ts_graph[
        "typescript"
    ]["edges"]

    go_graph = build_graph(str(_example_path("go")))
    assert {"from": "cmd/app", "to": "internal/service", "line": 3} in go_graph["go"][
        "edges"
    ]

    rust_graph = build_graph(str(_example_path("rust")))
    assert {"from": "src/lib.rs", "to": "src/parser.rs", "line": 1} in rust_graph[
        "rust"
    ]["edges"]

    java_graph = build_graph(str(_example_path("java")))
    assert {
        "from": "src/main/java/com/example/App.java",
        "to": "src/main/java/com/example/service/UserService.java",
        "line": 3,
    } in java_graph["java"]["edges"]

    kotlin_graph = build_graph(str(_example_path("kotlin")))
    assert {
        "from": "src/main/kotlin/com/example/App.kt",
        "to": "src/main/kotlin/com/example/service/UserService.kt",
        "line": 3,
    } in kotlin_graph["kotlin"]["edges"]

    csharp_graph = build_graph(str(_example_path("csharp")))
    assert {
        "from": "src/App.cs",
        "to": "src/Core/UserService.cs",
        "line": 1,
    } in csharp_graph["csharp"]["edges"]

    c_graph = build_graph(str(_example_path("c")))
    assert {"from": "src/main.c", "to": "src/util.h", "line": 1} in c_graph["c"][
        "edges"
    ]

    cpp_graph = build_graph(str(_example_path("cpp")))
    assert {
        "from": "src/app.cpp",
        "to": "include/example/service.hpp",
        "line": 1,
    } in cpp_graph["cpp"]["edges"]

    ruby_graph = build_graph(str(_example_path("ruby")))
    assert {
        "from": "lib/example/service.rb",
        "to": "lib/example/helper.rb",
        "line": 1,
    } in ruby_graph["ruby"]["edges"]

    php_graph = build_graph(str(_example_path("php")))
    assert {
        "from": "src/Service/UserService.php",
        "to": "src/Repository/UserRepository.php",
        "line": 4,
    } in php_graph["php"]["edges"]

    swift_symbols = extract_symbols(str(_example_path("swift")))
    assert swift_symbols["swift"]["structs"]["total"] >= 1

    objc_graph = build_graph(str(_example_path("objectivec")))
    assert {
        "from": "Sources/UserService.m",
        "to": "Sources/UserService.h",
        "line": 1,
    } in objc_graph["objectivec"]["edges"]

    bash_graph = build_graph(str(_example_path("bash")))
    assert {
        "from": "scripts/deploy.sh",
        "to": "scripts/lib/common.sh",
        "line": 3,
    } in bash_graph["bash"]["edges"]


def test_language_examples_expose_test_mappings():
    python_tests = analyze_tests(str(_example_path("python")))
    assert python_tests["python"]["coverage_shape"]["mapped"]

    javascript_tests = analyze_tests(str(_example_path("javascript")))
    assert javascript_tests["typescript"]["test_files"] >= 1

    typescript_tests = analyze_tests(str(_example_path("typescript")))
    assert typescript_tests["typescript"]["coverage_shape"]["mapped"]

    go_tests = analyze_tests(str(_example_path("go")))
    assert go_tests["go"]["coverage_shape"]["mapped"]

    rust_tests = analyze_tests(str(_example_path("rust")))
    assert rust_tests["rust"]["test_files"] >= 1

    java_tests = analyze_tests(str(_example_path("java")))
    assert java_tests["java"]["coverage_shape"]["mapped"]

    kotlin_tests = analyze_tests(str(_example_path("kotlin")))
    assert kotlin_tests["kotlin"]["coverage_shape"]["mapped"]

    csharp_tests = analyze_tests(str(_example_path("csharp")))
    assert csharp_tests["csharp"]["coverage_shape"]["mapped"]

    c_tests = analyze_tests(str(_example_path("c")))
    assert c_tests["c"]["coverage_shape"]["mapped"]

    cpp_tests = analyze_tests(str(_example_path("cpp")))
    assert cpp_tests["cpp"]["coverage_shape"]["mapped"]

    ruby_tests = analyze_tests(str(_example_path("ruby")))
    assert ruby_tests["ruby"]["test_files"] >= 1

    php_tests = analyze_tests(str(_example_path("php")))
    assert php_tests["php"]["coverage_shape"]["mapped"]

    swift_tests = analyze_tests(str(_example_path("swift")))
    assert swift_tests["swift"]["coverage_shape"]["mapped"]

    objc_tests = analyze_tests(str(_example_path("objectivec")))
    assert objc_tests["objectivec"]["coverage_shape"]["mapped"]

    bash_tests = analyze_tests(str(_example_path("bash")))
    assert bash_tests["bash"]["test_files"] >= 1


def test_mixed_example_validates_multi_language_behavior():
    repo = _example_path("mixed")

    scan_result = scan(str(repo))
    _assert_no_error_payload(scan_result)
    langs = set(scan_result["summary"]["by_language"])
    assert {"typescript", "go", "bash"} <= langs

    measure_result = measure(str(repo))
    _assert_no_error_payload(measure_result)
    assert {"typescript", "go", "bash"} <= set(measure_result)

    graph_result = build_graph(str(repo))
    _assert_no_error_payload(graph_result)
    assert "typescript" in graph_result
    assert "go" in graph_result
    assert "bash" in graph_result

    symbols_result = extract_symbols(str(repo))
    _assert_no_error_payload(symbols_result)
    assert "typescript" in symbols_result
    assert "go" in symbols_result
    assert "bash" in symbols_result

    tests_result = analyze_tests(str(repo))
    _assert_no_error_payload(tests_result)
    assert "typescript" in tests_result
    assert "go" in tests_result
    assert "bash" in tests_result

    config_result = detect(str(repo))
    _assert_no_error_payload(config_result)
    assert "typescript" in config_result
    assert "go" in config_result
