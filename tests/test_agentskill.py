#!/usr/bin/env python3
"""Comprehensive test suite for agentskill."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agentskill.constants import (
    CASE_CAMEL, CASE_KEBAB, CASE_MIXED, CASE_PASCAL,
    CASE_SCREAMING_SNAKE, CASE_SNAKE,
    NAME_VAR, NAME_FUNCTION, NAME_TYPE,
    EXTENSIONS, TOOL_FILES, SKIP_DIRS,
)
from agentskill.analyzers.base import LanguageAnalyzer, AnalysisResult
from agentskill.analyzers.language.rust import RustAnalyzer
from agentskill.analyzers.language.python import PythonAnalyzer
from agentskill.analyzers.language.generic import GenericAnalyzer
from agentskill.extractors.git import (
    extract_commit_prefixes,
    extract_branch_prefixes,
    analyze_git_commits,
    analyze_branches,
    analyze_git_config,
    get_remote_info,
)
from agentskill.extractors.filesystem import (
    is_hidden_path,
    should_skip_dir,
    is_git_repo,
    scan_source_files,
    detect_tooling,
    get_project_metadata,
)
from agentskill.extractors.structure import extract_repo_structure
from agentskill.extractors.commands import extract_commands
from agentskill.synthesis import AgentSynthesizer, SynthesisConfig
from agentskill.cli import analyze_repository, get_analyzer, generate_agents_md


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def run(self, test_class):
        print(f"\n{test_class.__doc__ or test_class.__name__}")
        print("-" * 40)
        instance = test_class()
        for name in sorted(dir(test_class)):
            if name.startswith("test_"):
                method = getattr(instance, name)
                try:
                    if hasattr(method, '__code__') and 'tmp_path' in method.__code__.co_varnames:
                        with tempfile.TemporaryDirectory() as td:
                            method(Path(td))
                    else:
                        method()
                    print(f"  PASS  {name}")
                    self.passed += 1
                except AssertionError as e:
                    print(f"  FAIL  {name}: {e}")
                    self.failed += 1
                except Exception as e:
                    print(f"  ERROR {name}: {e}")
                    self.failed += 1

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'=' * 40}")
        print(f"Results: {self.passed}/{total} passed")
        return 1 if self.failed else 0


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_to_dict_with_new_fields(self):
        result = AnalysisResult(
            naming_patterns={"a": 1},
            error_handling={"b": 2},
            comments={"c": 3},
            spacing={"d": 4},
            imports={"e": 5},
            metrics={"f": 6.0},
            type_annotations={"param_density": 0.5},
            import_order={"style": "stdlib_first"},
            file_count=3,
        )
        d = result.to_dict()
        assert d["type_annotations"]["param_density"] == 0.5
        assert d["import_order"]["style"] == "stdlib_first"


class TestLanguageAnalyzerBase:
    """Tests for LanguageAnalyzer base class."""

    def test_calculate_avg(self):
        analyzer = RustAnalyzer()
        assert analyzer._calculate_avg([1, 2, 3]) == 2.0
        assert analyzer._calculate_avg([]) == 0.0
        assert analyzer._calculate_avg([10]) == 10.0

    def test_get_top_items(self):
        analyzer = RustAnalyzer()
        items = {"a": 5, "b": 3, "c": 10, "d": 1}
        top = analyzer._get_top_items(items, 2)
        assert "c" in top
        assert "a" in top
        assert len(top) == 2

    def test_read_file_lines(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3")
        analyzer = RustAnalyzer()
        lines = analyzer._read_file_lines(f)
        assert len(lines) == 3

    def test_read_file_lines_nonexistent(self):
        analyzer = RustAnalyzer()
        lines = analyzer._read_file_lines(Path("/nonexistent/file.txt"))
        assert lines == []


class TestRustAnalyzer:
    """Tests for RustAnalyzer."""

    def test_case_detection(self):
        assert RustAnalyzer().detect_case_style("MAX_SIZE") == CASE_SCREAMING_SNAKE
        assert RustAnalyzer().detect_case_style("max_size") == CASE_SNAKE
        assert RustAnalyzer().detect_case_style("max-size") == CASE_KEBAB
        assert RustAnalyzer().detect_case_style("maxSize") == CASE_CAMEL
        assert RustAnalyzer().detect_case_style("MaxSize") == CASE_PASCAL
        assert RustAnalyzer().detect_case_style("Max-Size") == CASE_MIXED

    def test_language_name(self):
        assert RustAnalyzer().get_language_name() == "rust"

    def test_categorize_import_stdlib(self):
        a = RustAnalyzer()
        assert a.categorize_import("use std::collections::HashMap;") == "stdlib"
        assert a.categorize_import("use core::slice;") == "stdlib"

    def test_categorize_import_local(self):
        a = RustAnalyzer()
        assert a.categorize_import("use crate::utils;") == "local"

    def test_categorize_import_external(self):
        a = RustAnalyzer()
        assert a.categorize_import("use serde::Serialize;") == "third_party"

    def test_analyze_rust_file(self, tmp_path):
        rs_file = tmp_path / "test.rs"
        rs_file.write_text(
            "fn main() {\n"
            "    let x = 1;\n"
            "    let my_var = get_value().unwrap();\n"
            "    let result = do_thing()?;\n"
            "}\n"
            "struct MyStruct { field: i32 }\n"
            "const MAX_SIZE: usize = 100;\n"
            "/// doc comment\n"
            "// normal comment\n"
            "use std::collections::HashMap;\n"
            "use crate::utils;\n"
        )

        analyzer = RustAnalyzer()
        result = analyzer.analyze_files([rs_file])

        assert result.file_count == 1
        assert result.error_handling.get("unwrap", 0) >= 1
        assert result.error_handling.get("?", 0) >= 1

    def test_type_annotations_rust(self, tmp_path):
        rs_file = tmp_path / "test.rs"
        rs_file.write_text(
            "fn foo(a: i32, b: String) -> i32 { 1 }\n"
            "fn bar(x: bool) {}\n"
        )

        analyzer = RustAnalyzer()
        result = analyzer.analyze_files([rs_file])
        assert result.type_annotations.get("param_density", 0) > 0


class TestPythonAnalyzer:
    """Tests for PythonAnalyzer."""

    def test_case_detection(self):
        a = PythonAnalyzer()
        assert a.detect_case_style("my_variable") == CASE_SNAKE
        assert a.detect_case_style("MyClass") == CASE_PASCAL
        assert a.detect_case_style("MAX_SIZE") == CASE_SCREAMING_SNAKE
        assert a.detect_case_style("camelCase") == CASE_CAMEL

    def test_language_name(self):
        assert PythonAnalyzer().get_language_name() == "python"

    def test_categorize_import_stdlib(self):
        a = PythonAnalyzer()
        assert a.categorize_import("import os") == "stdlib"
        assert a.categorize_import("from pathlib import Path") == "stdlib"

    def test_categorize_import_local(self):
        a = PythonAnalyzer()
        assert a.categorize_import("from . import utils") == "local"

    def test_categorize_import_third_party(self):
        a = PythonAnalyzer()
        assert a.categorize_import("import requests") == "third_party"

    def test_analyze_python_file(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "def my_function(x: int) -> int:\n"
            "    my_var = 1\n"
            "    # a comment\n"
            "    return my_var\n"
            "\n"
            "class MyClass:\n"
            "    \"\"\"Docstring.\"\"\"\n"
            "    pass\n"
        )

        analyzer = PythonAnalyzer()
        result = analyzer.analyze_files([py_file])

        assert result.file_count == 1
        assert result.naming_patterns["functions"]["dominant_case"] == CASE_SNAKE

    def test_type_annotations_python(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "def foo(a: int, b: str) -> bool:\n"
            "    return True\n"
        )

        analyzer = PythonAnalyzer()
        result = analyzer.analyze_files([py_file])
        assert result.type_annotations.get("param_density", 0) > 0
        assert result.type_annotations.get("return_density", 0) > 0

    def test_import_order_detection(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "import os\n"
            "import sys\n"
            "\n"
            "import requests\n"
        )

        analyzer = PythonAnalyzer()
        result = analyzer.analyze_files([py_file])
        assert result.import_order.get("style") is not None


class TestGenericAnalyzer:
    """Tests for GenericAnalyzer."""

    def test_language_name(self):
        assert GenericAnalyzer("go").get_language_name() == "go"

    def test_case_detection(self):
        a = GenericAnalyzer("go")
        assert a.detect_case_style("MAX_SIZE") == "SCREAMING_SNAKE_CASE"
        assert a.detect_case_style("myVar") == "camelCase"


if __name__ == "__main__":
    runner = TestRunner()
    runner.run(TestAnalysisResult)
    runner.run(TestLanguageAnalyzerBase)
    runner.run(TestRustAnalyzer)
    runner.run(TestPythonAnalyzer)
    runner.run(TestGenericAnalyzer)
    sys.exit(runner.summary())