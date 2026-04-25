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
    NAME_VAR, NAME_FUNCTION, NAME_TYPE, NAME_CONST,
    LANG_RUST, LANG_PYTHON, LANG_JS, LANG_TS, LANG_GO,
    EXTENSIONS, TOOL_FILES, SKIP_DIRS, PYTHON_VAR_KEYWORDS,
    RUST_COMMENT_STYLES, PYTHON_COMMENT_STYLE,
    RUST_ERROR_PATTERNS, RUST_ERROR_KEYS,
    SAMPLE_SIZE_SMALL, SAMPLE_SIZE_MEDIUM, COMMIT_LOG_LIMIT,
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


def make_git_repo(path, commits=None):
    subprocess.run(["git", "init", str(path)], capture_output=True, timeout=10)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t.com"], capture_output=True, timeout=10)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "T"], capture_output=True, timeout=10)
    if commits:
        for msg in commits:
            (path / "f.txt").write_text(msg)
            subprocess.run(["git", "-C", str(path), "add", "."], capture_output=True, timeout=10)
            subprocess.run(["git", "-C", str(path), "commit", "-m", msg], capture_output=True, timeout=10)


def make_source_tree(path, files):
    for rel, content in files.items():
        fpath = path / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content)


# Constants

class TestConstants:
    """Tests for constants module."""

    def test_case_constants_distinct(self):
        cases = [CASE_SCREAMING_SNAKE, CASE_SNAKE, CASE_KEBAB, CASE_CAMEL, CASE_PASCAL, CASE_MIXED]
        assert len(set(cases)) == len(cases)

    def test_name_constants(self):
        assert NAME_VAR == "vars"
        assert NAME_FUNCTION == "functions"
        assert NAME_TYPE == "types"
        assert NAME_CONST == "consts"

    def test_language_constants(self):
        assert LANG_RUST == "rust"
        assert LANG_PYTHON == "python"

    def test_extensions_populated(self):
        assert len(EXTENSIONS) >= 6
        assert "rust" in EXTENSIONS
        assert "python" in EXTENSIONS

    def test_tool_files_populated(self):
        assert len(TOOL_FILES) >= 5
        assert "Cargo.toml" in TOOL_FILES

    def test_skip_dirs(self):
        assert "node_modules" in SKIP_DIRS
        assert "target" in SKIP_DIRS
        assert "__pycache__" in SKIP_DIRS

    def test_rust_error_keys_match_patterns(self):
        assert len(RUST_ERROR_KEYS) == len(RUST_ERROR_PATTERNS)

    def test_sample_sizes(self):
        assert SAMPLE_SIZE_SMALL > 0
        assert SAMPLE_SIZE_MEDIUM > SAMPLE_SIZE_SMALL


# Base analyzer

class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""

    def test_to_dict(self):
        result = AnalysisResult(
            naming_patterns={"a": 1},
            error_handling={"b": 2},
            comments={"c": 3},
            spacing={"d": 4},
            imports={"e": 5},
            metrics={"f": 6.0},
            file_count=3,
        )
        d = result.to_dict()
        assert d["naming"] == {"a": 1}
        assert d["file_count"] == 3
        assert "error_handling" in d

    def test_default_file_count(self):
        result = AnalysisResult(
            naming_patterns={}, error_handling={}, comments={},
            spacing={}, imports={}, metrics={},
        )
        assert result.file_count == 0


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


# Rust analyzer

class TestRustAnalyzer:
    """Tests for RustAnalyzer."""

    def test_case_screaming_snake(self):
        assert RustAnalyzer().detect_case_style("MAX_SIZE") == CASE_SCREAMING_SNAKE

    def test_case_snake(self):
        assert RustAnalyzer().detect_case_style("max_size") == CASE_SNAKE

    def test_case_kebab(self):
        assert RustAnalyzer().detect_case_style("max-size") == CASE_KEBAB

    def test_case_camel(self):
        assert RustAnalyzer().detect_case_style("maxSize") == CASE_CAMEL

    def test_case_pascal(self):
        assert RustAnalyzer().detect_case_style("MaxSize") == CASE_PASCAL

    def test_case_mixed(self):
        assert RustAnalyzer().detect_case_style("Max-Size") == CASE_MIXED

    def test_language_name(self):
        assert RustAnalyzer().get_language_name() == "rust"

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
        assert result.error_handling["unwrap"] >= 1
        assert result.error_handling["?"] >= 1
        assert result.comments["doc_comments"] >= 1
        assert result.comments["normal_comments"] >= 1
        assert result.imports["std"] >= 1
        assert result.imports["crate"] >= 1

    def test_naming_dominant_case(self, tmp_path):
        rs_file = tmp_path / "test.rs"
        rs_file.write_text(
            "fn my_function() {}\n"
            "fn another_function() {}\n"
            "struct MyStruct {}\n"
            "const MAX_SIZE: usize = 1;\n"
        )

        analyzer = RustAnalyzer()
        result = analyzer.analyze_files([rs_file])

        assert result.naming_patterns["functions"]["dominant_case"] == CASE_SNAKE
        assert result.naming_patterns["types"]["dominant_case"] == CASE_PASCAL
        assert result.naming_patterns["consts"]["dominant_case"] == CASE_SCREAMING_SNAKE

    def test_empty_file(self, tmp_path):
        rs_file = tmp_path / "empty.rs"
        rs_file.write_text("")

        analyzer = RustAnalyzer()
        result = analyzer.analyze_files([rs_file])

        assert result.file_count == 1

    def test_panic_detection(self, tmp_path):
        rs_file = tmp_path / "test.rs"
        rs_file.write_text('panic!("error");\n')

        analyzer = RustAnalyzer()
        result = analyzer.analyze_files([rs_file])
        assert result.error_handling["panic"] >= 1


# Python analyzer

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

    def test_analyze_python_file(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "def my_function():\n"
            "    my_var = 1\n"
            "    # a comment\n"
            "    return my_var\n"
            "\n"
            "class MyClass:\n"
            "    \"\"\"Docstring.\"\"\"\n"
            "    pass\n"
            "\n"
            "try:\n"
            "    x = 1\n"
            "except:\n"
            "    raise ValueError()\n"
        )

        analyzer = PythonAnalyzer()
        result = analyzer.analyze_files([py_file])

        assert result.file_count == 1
        assert result.error_handling["try_except"] >= 1
        assert result.error_handling["raise"] >= 1
        assert result.comments["docstrings"] >= 1
        assert result.comments["normal_comments"] >= 1
        assert result.imports["stdlib"] >= 1

    def test_assert_detection(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text("assert x == 1\n")

        analyzer = PythonAnalyzer()
        result = analyzer.analyze_files([py_file])
        assert result.error_handling["assert"] >= 1

    def test_with_context_detection(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text("with open('f') as fh:\n    pass\n")

        analyzer = PythonAnalyzer()
        result = analyzer.analyze_files([py_file])
        assert result.error_handling["with_context"] >= 1

    def test_skip_keyword_vars(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text("if x:\n    pass\nfor i in range(10):\n    pass\n")

        analyzer = PythonAnalyzer()
        result = analyzer.analyze_files([py_file])
        # 'if' and 'for' should not be counted as vars
        if result.naming_patterns.get("vars", {}).get("counts"):
            for kw in ["if", "for", "while", "self", "cls"]:
                assert kw not in result.naming_patterns["vars"]["counts"]


# Generic analyzer

class TestGenericAnalyzer:
    """Tests for GenericAnalyzer."""

    def test_language_name(self):
        assert GenericAnalyzer("go").get_language_name() == "go"
        assert GenericAnalyzer("java").get_language_name() == "java"

    def test_case_detection(self):
        a = GenericAnalyzer("go")
        assert a.detect_case_style("MAX_SIZE") == "SCREAMING_SNAKE_CASE"
        assert a.detect_case_style("myVar") == "camelCase"
        assert a.detect_case_style("MyClass") == "PascalCase"

    def test_analyze_go_file(self, tmp_path):
        go_file = tmp_path / "main.go"
        go_file.write_text(
            "package main\n"
            "\n"
            "import \"fmt\"\n"
            "\n"
            "func main() {\n"
            "    fmt.Println(\"hello\")\n"
            "}\n"
        )

        analyzer = GenericAnalyzer("go")
        result = analyzer.analyze_files([go_file])

        assert result.file_count == 1
        assert result.metrics["total_lines"] > 0
        assert result.comments["density"] >= 0


# Git extractors

class TestExtractCommitPrefixes:
    """Tests for extract_commit_prefixes."""

    def test_no_prefixes(self):
        assert extract_commit_prefixes(["fix bug", "update readme"]) == {}

    def test_bracket_prefixes(self):
        commits = ["[feat]: add feature", "[feat]: update"]
        result = extract_commit_prefixes(commits)
        assert "feat" in result
        assert result["feat"] == 2

    def test_conventional_prefixes(self):
        commits = ["feat: add feature", "fix: resolve bug", "feat: update"]
        result = extract_commit_prefixes(commits)
        assert "feat" in result

    def test_empty(self):
        assert extract_commit_prefixes([]) == {}


class TestExtractBranchPrefixes:
    """Tests for extract_branch_prefixes."""

    def test_single_prefix(self):
        result = extract_branch_prefixes(["feature/add", "feature/update"])
        assert result == {"feature": 2}

    def test_remotes_filtered(self):
        result = extract_branch_prefixes(["remotes/origin/feature/add", "feature/update"])
        assert result["feature"] == 2

    def test_no_prefix(self):
        assert extract_branch_prefixes(["main", "master"]) == {}


class TestAnalyzeGitCommits:
    """Tests for analyze_git_commits with real git repos."""

    def test_with_commits(self, tmp_path):
        make_git_repo(tmp_path, ["[feat]: initial", "[fix]: bugfix"])
        result = analyze_git_commits(str(tmp_path))
        assert result["count"] >= 2

    def test_empty_repo(self, tmp_path):
        make_git_repo(tmp_path)
        result = analyze_git_commits(str(tmp_path))
        assert result["count"] == 0

    def test_nonexistent_path(self):
        result = analyze_git_commits("/nonexistent/path")
        assert result["count"] == 0


class TestAnalyzeBranches:
    """Tests for analyze_branches."""

    def test_with_branches(self, tmp_path):
        make_git_repo(tmp_path, ["initial"])
        result = analyze_branches(str(tmp_path))
        assert result["count"] >= 1

    def test_nonexistent(self):
        result = analyze_branches("/nonexistent/path")
        assert result["count"] == 0


class TestAnalyzeGitConfig:
    """Tests for analyze_git_config."""

    def test_basic(self, tmp_path):
        make_git_repo(tmp_path)
        result = analyze_git_config(str(tmp_path))
        assert "gpg_signing" in result
        assert "signoff" in result

    def test_nonexistent(self):
        result = analyze_git_config("/nonexistent/dir/xyz")
        assert isinstance(result, dict)


class TestGetRemoteInfo:
    """Tests for get_remote_info."""

    def test_no_remote(self, tmp_path):
        make_git_repo(tmp_path)
        result = get_remote_info(str(tmp_path))
        assert "github" in result

    def test_nonexistent(self):
        result = get_remote_info("/nonexistent/dir/xyz")
        assert isinstance(result, dict)


# Filesystem extractors

class TestIsHiddenPath:
    """Tests for is_hidden_path."""

    def test_hidden(self):
        assert is_hidden_path(Path("/home/.config/app"))

    def test_not_hidden(self):
        assert not is_hidden_path(Path("/home/projects/app"))

    def test_dotfile(self):
        assert is_hidden_path(Path("/home/.bashrc"))


class TestShouldSkipDir:
    """Tests for should_skip_dir."""

    def test_skip_node_modules(self):
        assert should_skip_dir(Path("/project/node_modules/pkg"))

    def test_skip_target(self):
        assert should_skip_dir(Path("/project/target/debug"))

    def test_no_skip(self):
        assert not should_skip_dir(Path("/project/src"))


class TestIsGitRepo:
    """Tests for is_git_repo."""

    def test_non_git(self, tmp_path):
        assert not is_git_repo(str(tmp_path))

    def test_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert is_git_repo(str(tmp_path))


class TestScanSourceFiles:
    """Tests for scan_source_files."""

    def test_find_python(self, tmp_path):
        make_source_tree(tmp_path, {"src/main.py": "x=1", "src/utils.py": "y=2"})
        result = scan_source_files(str(tmp_path))
        assert "python" in result
        assert len(result["python"]) == 2

    def test_find_rust(self, tmp_path):
        make_source_tree(tmp_path, {"src/main.rs": "fn main(){}"})
        result = scan_source_files(str(tmp_path))
        assert "rust" in result

    def test_skip_hidden(self, tmp_path):
        make_source_tree(tmp_path, {".hidden/secret.py": "x=1", "src/visible.py": "y=2"})
        result = scan_source_files(str(tmp_path))
        assert len(result["python"]) == 1

    def test_skip_node_modules(self, tmp_path):
        make_source_tree(tmp_path, {"node_modules/pkg/index.js": "x=1", "src/app.js": "y=2"})
        result = scan_source_files(str(tmp_path))
        assert len(result["javascript"]) == 1

    def test_mixed_languages(self, tmp_path):
        make_source_tree(tmp_path, {
            "a.py": "x=1", "b.rs": "fn m(){}", "c.js": "x=1", "d.go": "func m(){}"
        })
        result = scan_source_files(str(tmp_path))
        assert len(result) >= 4

    def test_many_languages(self, tmp_path):
        make_source_tree(tmp_path, {
            "a.py": "x=1", "b.rs": "fn m(){}", "c.js": "x=1",
            "d.ts": "let x=1", "e.go": "func m(){}", "f.sh": "echo hi",
            "g.c": "int main(){}", "h.java": "class M{}",
            "i.rb": "puts 'hi'", "j.swift": "print(1)",
            "k.kt": "fun main(){}", "l.scala": "object M",
        })
        result = scan_source_files(str(tmp_path))
        assert len(result) >= 6


class TestDetectTooling:
    """Tests for detect_tooling."""

    def test_cargo_toml(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname=\"t\"")
        result = detect_tooling(str(tmp_path))
        assert result.get("cargo")

    def test_github_actions(self, tmp_path):
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push")
        result = detect_tooling(str(tmp_path))
        assert result.get("GitHub Actions CI")

    def test_makefile(self, tmp_path):
        (tmp_path / "Makefile").write_text("all:\n\techo hi")
        result = detect_tooling(str(tmp_path))
        assert result.get("make")

    def test_lockfile(self, tmp_path):
        (tmp_path / "package-lock.json").write_text("{}")
        result = detect_tooling(str(tmp_path))
        assert result.get("npm (locked)")

    def test_empty_dir(self, tmp_path):
        result = detect_tooling(str(tmp_path))
        assert not result.get("cargo")
        assert not result.get("make")

    def test_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
        result = detect_tooling(str(tmp_path))
        assert result.get("poetry/flit")

    def test_dockerfile(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM ubuntu")
        result = detect_tooling(str(tmp_path))
        assert result.get("docker")


class TestGetProjectMetadata:
    """Tests for get_project_metadata."""

    def test_readme_name(self, tmp_path):
        (tmp_path / "README.md").write_text("# My Project\nSome desc")
        result = get_project_metadata(str(tmp_path))
        assert result.get("project_name") == "My Project"

    def test_license_mit(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT License\n\nCopyright...")
        result = get_project_metadata(str(tmp_path))
        assert result.get("license_type") == "MIT"

    def test_license_apache(self, tmp_path):
        (tmp_path / "LICENSE").write_text("Apache License\nVersion 2.0")
        result = get_project_metadata(str(tmp_path))
        assert result.get("license_type") == "Apache-2.0"

    def test_no_metadata(self, tmp_path):
        result = get_project_metadata(str(tmp_path))
        assert "project_name" not in result


# Synthesis

class TestSynthesisOverview:
    """Tests for overview generation."""

    def test_basic_overview(self):
        s = AgentSynthesizer()
        output = s.synthesize([{"languages": {"python": {"file_count": 1}}, "git": {}, "tooling": {}}], ["/tmp/test"])
        assert "Overview" in output

    def test_multi_repo(self):
        s = AgentSynthesizer()
        output = s.synthesize(
            [{"languages": {"rust": {"file_count": 1}}, "git": {}, "tooling": {}}],
            ["/tmp/r1", "/tmp/r2"],
        )
        assert "2 repositories" in output


class TestSynthesisCrossLanguage:
    """Tests for cross-language patterns."""

    def test_common_naming(self):
        s = AgentSynthesizer()
        analyses = [{
            "languages": {
                "python": {"naming": {"vars": {"dominant_case": "snake_case"}}, "file_count": 1, "comments": {}, "error_handling": {}},
                "rust": {"naming": {"vars": {"dominant_case": "snake_case"}}, "file_count": 1, "comments": {}, "error_handling": {}},
            },
            "git": {}, "tooling": {},
        }]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "Cross-Language" in output


class TestSynthesisGit:
    """Tests for git section synthesis."""

    def test_commit_prefixes(self):
        s = AgentSynthesizer()
        analyses = [{
            "languages": {},
            "git": {
                "commits": {"count": 10, "avg_length": 50, "common_prefixes": {"feat": 5, "fix": 3}},
                "branches": {"count": 2, "common_prefixes": {}},
            },
            "tooling": {},
        }]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "feat" in output or "fix" in output

    def test_skip_git(self):
        config = SynthesisConfig(include_git=False)
        s = AgentSynthesizer(config)
        analyses = [{
            "languages": {},
            "git": {"commits": {}, "branches": {}},
            "tooling": {},
        }]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "Git" not in output


class TestSynthesisTooling:
    """Tests for tooling section synthesis."""

    def test_tooling_listed(self):
        s = AgentSynthesizer()
        analyses = [{"languages": {}, "git": {}, "tooling": {"cargo": True, "git": True}}]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "cargo" in output

    def test_skip_tooling(self):
        config = SynthesisConfig(include_tooling=False)
        s = AgentSynthesizer(config)
        analyses = [{"languages": {}, "git": {}, "tooling": {"cargo": True}}]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "Tooling" not in output


class TestSynthesisRedLines:
    """Tests for red lines section."""

    def test_red_lines_present(self):
        s = AgentSynthesizer()
        output = s.synthesize([{"languages": {}, "git": {}, "tooling": {}}], ["/tmp/test"])
        assert "Red Lines" in output

    def test_skip_red_lines(self):
        config = SynthesisConfig(include_red_lines=False)
        s = AgentSynthesizer(config)
        output = s.synthesize([{"languages": {}, "git": {}, "tooling": {}}], ["/tmp/test"])
        assert "Red Lines" not in output


class TestSynthesisFooter:
    """Tests for footer generation."""

    def test_footer_source(self):
        s = AgentSynthesizer()
        output = s.synthesize([{"languages": {}, "git": {}, "tooling": {}}], ["/tmp/myproject"])
        assert "myproject" in output
        assert "Source" in output


class TestSynthesisLanguageSections:
    """Tests for per-language sections."""

    def test_python_section(self):
        s = AgentSynthesizer()
        analyses = [{
            "languages": {
                "python": {
                    "naming": {"vars": {"dominant_case": "snake_case"}},
                    "file_count": 5,
                    "comments": {"doc_style": '"""', "density": 0.05},
                    "error_handling": {},
                    "spacing": {},
                },
            },
            "git": {}, "tooling": {},
        }]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "Python" in output

    def test_rust_section(self):
        s = AgentSynthesizer()
        analyses = [{
            "languages": {
                "rust": {
                    "naming": {"types": {"dominant_case": "PascalCase"}},
                    "file_count": 3,
                    "comments": {},
                    "error_handling": {"unwrap": 5, "?": 10},
                    "spacing": {},
                },
            },
            "git": {}, "tooling": {},
        }]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "Rust" in output
        assert "unwrap" in output


class TestWriteToFile:
    """Tests for write_to_file."""

    def test_write(self, tmp_path):
        s = AgentSynthesizer()
        output = "# AGENTS.md\n\ntest"
        outfile = tmp_path / "AGENTS.md"
        s.write_to_file(output, str(outfile))
        assert outfile.exists()
        assert outfile.read_text() == output


# CLI

class TestGetAnalyzer:
    """Tests for get_analyzer."""

    def test_rust(self):
        a = get_analyzer("rust")
        assert isinstance(a, RustAnalyzer)

    def test_python(self):
        a = get_analyzer("python")
        assert isinstance(a, PythonAnalyzer)

    def test_unknown(self):
        a = get_analyzer("java")
        assert isinstance(a, GenericAnalyzer)
        assert a.get_language_name() == "java"


class TestAnalyzeRepository:
    """Integration tests for analyze_repository."""

    def test_python_repo(self, tmp_path):
        make_git_repo(tmp_path, ["[feat]: initial"])
        make_source_tree(tmp_path, {
            "src/main.py": "def my_function():\n    x = 1\n",
            "src/utils.py": "def helper():\n    pass\n",
        })
        result = analyze_repository(str(tmp_path))
        assert "python" in result["languages"]
        assert result["languages"]["python"]["file_count"] >= 2

    def test_rust_repo(self, tmp_path):
        make_git_repo(tmp_path, ["initial"])
        make_source_tree(tmp_path, {
            "src/main.rs": "fn main() { let x = get().unwrap(); }\n",
            "Cargo.toml": "[package]\nname=\"t\"",
        })
        result = analyze_repository(str(tmp_path))
        assert "rust" in result["languages"]
        assert result["tooling"].get("cargo")

    def test_non_git(self, tmp_path):
        make_source_tree(tmp_path, {"main.py": "x = 1"})
        result = analyze_repository(str(tmp_path))
        assert "path" in result

    def test_empty_repo(self, tmp_path):
        make_git_repo(tmp_path)
        result = analyze_repository(str(tmp_path))
        assert "languages" in result


class TestGenerateAgentsMd:
    """Tests for generate_agents_md."""

    def test_from_analyses(self, tmp_path):
        make_git_repo(tmp_path, ["[feat]: initial"])
        make_source_tree(tmp_path, {"main.py": "x = 1\n"})

        analysis = analyze_repository(str(tmp_path))
        output = generate_agents_md([analysis], [str(tmp_path)])
        assert "AGENTS.md" in output or "Overview" in output


if __name__ == "__main__":
    runner = TestRunner()

    runner.run(TestConstants)
    runner.run(TestAnalysisResult)
    runner.run(TestLanguageAnalyzerBase)
    runner.run(TestRustAnalyzer)
    runner.run(TestPythonAnalyzer)
    runner.run(TestGenericAnalyzer)
    runner.run(TestExtractCommitPrefixes)
    runner.run(TestExtractBranchPrefixes)
    runner.run(TestAnalyzeGitCommits)
    runner.run(TestAnalyzeBranches)
    runner.run(TestAnalyzeGitConfig)
    runner.run(TestGetRemoteInfo)
    runner.run(TestIsHiddenPath)
    runner.run(TestShouldSkipDir)
    runner.run(TestIsGitRepo)
    runner.run(TestScanSourceFiles)
    runner.run(TestDetectTooling)
    runner.run(TestGetProjectMetadata)
    runner.run(TestSynthesisOverview)
    runner.run(TestSynthesisCrossLanguage)
    runner.run(TestSynthesisGit)
    runner.run(TestSynthesisTooling)
    runner.run(TestSynthesisRedLines)
    runner.run(TestSynthesisFooter)
    runner.run(TestSynthesisLanguageSections)
    runner.run(TestWriteToFile)
    runner.run(TestGetAnalyzer)
    runner.run(TestAnalyzeRepository)
    runner.run(TestGenerateAgentsMd)

    sys.exit(runner.summary())