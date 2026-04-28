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
    def _ext(self, extension):
        spec = language_for_extension(extension)
        assert spec is not None, f"No language for extension {extension!r}"
        return spec.id

    def test_python(self):
        assert self._ext(".py") == "python"

    def test_python_without_dot(self):
        assert self._ext("py") == "python"

    def test_typescript(self):
        assert self._ext(".ts") == "typescript"

    def test_typescript_tsx(self):
        assert self._ext(".tsx") == "typescript"

    def test_javascript(self):
        assert self._ext(".js") == "javascript"

    def test_javascript_mjs(self):
        assert self._ext(".mjs") == "javascript"

    def test_javascript_cjs(self):
        assert self._ext(".cjs") == "javascript"

    def test_go(self):
        assert self._ext(".go") == "go"

    def test_rust(self):
        assert self._ext(".rs") == "rust"

    def test_java(self):
        assert self._ext(".java") == "java"

    def test_kotlin(self):
        assert self._ext(".kt") == "kotlin"

    def test_csharp(self):
        assert self._ext(".cs") == "csharp"

    def test_c(self):
        assert self._ext(".c") == "c"

    def test_h_is_c(self):
        assert self._ext(".h") == "c"

    def test_cpp(self):
        assert self._ext(".cpp") == "cpp"

    def test_cpp_cc(self):
        assert self._ext(".cc") == "cpp"

    def test_cpp_hpp(self):
        assert self._ext(".hpp") == "cpp"

    def test_ruby(self):
        assert self._ext(".rb") == "ruby"

    def test_php(self):
        assert self._ext(".php") == "php"

    def test_swift(self):
        assert self._ext(".swift") == "swift"

    def test_objectivec(self):
        assert self._ext(".m") == "objectivec"

    def test_bash(self):
        assert self._ext(".sh") == "bash"

    def test_bash_extension(self):
        assert self._ext(".bash") == "bash"

    def test_unknown_returns_none(self):
        assert language_for_extension(".xyz") is None

    def test_case_insensitive(self):
        assert self._ext(".PY") == "python"
        assert self._ext(".Go") == "go"


class TestLanguageForPath:
    def _path(self, p):
        spec = language_for_path(p)
        assert spec is not None, f"No language for path {p!r}"
        return spec.id

    def test_python_path(self):
        assert self._path("src/main.py") == "python"

    def test_go_path(self):
        assert self._path("cmd/server.go") == "go"

    def test_ruby_path(self):
        assert self._path("lib/foo.rb") == "ruby"

    def test_path_object(self):
        assert self._path(Path("app/main.ts")) == "typescript"

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

    def test_unknown_language_id_returns_false(self):
        assert is_test_path("test_app.py", language_id="cobol") is False


class TestScanRegression:
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
