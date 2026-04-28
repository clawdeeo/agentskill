"""Tests for the shared language registry and detection helpers."""

from pathlib import Path

from common.languages import (
    all_language_specs,
    is_supported_language,
    is_test_path,
    language_by_id,
    language_for_extension,
    language_for_path,
)
from test_support import create_repo

REQUIRED_LANGUAGE_IDS = {
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
    "swift",
    "objectivec",
    "bash",
}


class TestRegistryCompleteness:
    def test_all_required_languages_registered(self):
        ids = {spec.id for spec in all_language_specs()}
        missing = REQUIRED_LANGUAGE_IDS - ids
        assert not missing, f"Missing language IDs: {missing}"

    def test_no_duplicate_ids(self):
        ids = [spec.id for spec in all_language_specs()]
        assert len(ids) == len(set(ids)), "Duplicate language IDs found"

    def test_every_language_has_display_name(self):
        for spec in all_language_specs():
            assert spec.display_name, f"{spec.id} missing display_name"

    def test_every_language_has_at_least_one_extension(self):
        for spec in all_language_specs():
            assert spec.extensions, f"{spec.id} missing extensions"


class TestLanguageById:
    def test_known_ids(self):
        for lang_id in REQUIRED_LANGUAGE_IDS:
            spec = language_by_id(lang_id)
            assert spec is not None, f"{lang_id} not found by ID"
            assert spec.id == lang_id

    def test_unknown_id_returns_none(self):
        assert language_by_id("cobol") is None


class TestLanguageForExtension:
    def test_python(self):
        assert language_for_extension(".py").id == "python"

    def test_python_without_dot(self):
        assert language_for_extension("py").id == "python"

    def test_typescript(self):
        assert language_for_extension(".ts").id == "typescript"

    def test_typescript_tsx(self):
        assert language_for_extension(".tsx").id == "typescript"

    def test_javascript(self):
        assert language_for_extension(".js").id == "javascript"

    def test_javascript_mjs(self):
        assert language_for_extension(".mjs").id == "javascript"

    def test_javascript_cjs(self):
        assert language_for_extension(".cjs").id == "javascript"

    def test_go(self):
        assert language_for_extension(".go").id == "go"

    def test_rust(self):
        assert language_for_extension(".rs").id == "rust"

    def test_java(self):
        assert language_for_extension(".java").id == "java"

    def test_kotlin(self):
        assert language_for_extension(".kt").id == "kotlin"

    def test_csharp(self):
        assert language_for_extension(".cs").id == "csharp"

    def test_c(self):
        assert language_for_extension(".c").id == "c"

    def test_h_is_c(self):
        assert language_for_extension(".h").id == "c"

    def test_cpp(self):
        assert language_for_extension(".cpp").id == "cpp"

    def test_cpp_cc(self):
        assert language_for_extension(".cc").id == "cpp"

    def test_cpp_hpp(self):
        assert language_for_extension(".hpp").id == "cpp"

    def test_ruby(self):
        assert language_for_extension(".rb").id == "ruby"

    def test_php(self):
        assert language_for_extension(".php").id == "php"

    def test_swift(self):
        assert language_for_extension(".swift").id == "swift"

    def test_objectivec(self):
        assert language_for_extension(".m").id == "objectivec"

    def test_bash(self):
        assert language_for_extension(".sh").id == "bash"

    def test_bash_extension(self):
        assert language_for_extension(".bash").id == "bash"

    def test_unknown_returns_none(self):
        assert language_for_extension(".xyz") is None

    def test_case_insensitive(self):
        assert language_for_extension(".PY").id == "python"
        assert language_for_extension(".Go").id == "go"


class TestLanguageForPath:
    def test_python_path(self):
        assert language_for_path("src/main.py").id == "python"

    def test_go_path(self):
        assert language_for_path("cmd/server.go").id == "go"

    def test_ruby_path(self):
        assert language_for_path("lib/foo.rb").id == "ruby"

    def test_path_object(self):
        assert language_for_path(Path("app/main.ts")).id == "typescript"

    def test_unknown_extension(self):
        assert language_for_path("readme.md") is None

    def test_no_extension(self):
        assert language_for_path("Makefile") is None


class TestIsSupportedLanguage:
    def test_known(self):
        assert is_supported_language("python") is True
        assert is_supported_language("go") is True

    def test_unknown(self):
        assert is_supported_language("fortran") is False


class TestIsTestPath:
    def test_python_test_prefix(self):
        assert is_test_path("tests/test_app.py") is True

    def test_python_test_suffix(self):
        assert is_test_path("foo_test.py") is True

    def test_typescript_test(self):
        assert is_test_path("foo.test.ts") is True

    def test_javascript_spec(self):
        assert is_test_path("foo.spec.js") is True

    def test_go_test(self):
        assert is_test_path("service_test.go") is True

    def test_java_test(self):
        assert is_test_path("UserServiceTest.java") is True

    def test_ruby_spec(self):
        assert is_test_path("foo_spec.rb") is True

    def test_php_test(self):
        assert is_test_path("UserTest.php") is True

    def test_bash_test(self):
        assert is_test_path("test_script.sh") is True

    def test_bash_bats(self):
        assert is_test_path("foo.bats") is True

    def test_source_file_is_not_test(self):
        assert is_test_path("src/main.py") is False

    def test_language_id_filter(self):
        assert is_test_path("test_app.py", language_id="python") is True
        assert is_test_path("test_app.py", language_id="go") is False

    def test_unknown_language_id_ignores_filter(self):
        assert is_test_path("test_app.py", language_id="cobol") is False


class TestScanRegression:
    """Ensure scan output shape stays stable after registry migration."""

    def test_scan_detects_languages_from_registry(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "main.py": "print('hello')\n",
                "app.ts": "console.log('hi');\n",
                "server.go": "package main\n",
                "lib.rb": "puts 'hello'\n",
                "style.css": "body {}\n",
            },
        )

        from commands.scan import scan

        result = scan(str(repo))

        langs = set(result["summary"]["by_language"].keys())
        assert "python" in langs
        assert "typescript" in langs
        assert "go" in langs
        assert "ruby" in langs
        assert "css" not in langs

    def test_scan_output_shape_unchanged(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "pkg/__init__.py": "\n",
                "pkg/main.py": "def main(): pass\n",
            },
        )

        from commands.scan import scan

        result = scan(str(repo))

        assert "tree" in result
        assert "summary" in result
        assert "read_order" in result
        assert "total_files" in result["summary"]
        assert "by_language" in result["summary"]

        for entry in result["tree"]:
            assert "path" in entry
            assert "type" in entry
            assert "language" in entry
            assert "size_bytes" in entry
            assert "line_count" in entry
            assert "depth" in entry
