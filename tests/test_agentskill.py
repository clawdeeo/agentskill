#!/usr/bin/env python3
"""Comprehensive test suite for agentskill."""

import sys
import tempfile
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from agentskill.constants import (
    CASE_CAMEL, CASE_KEBAB, CASE_MIXED, CASE_PASCAL,
    CASE_SCREAMING_SNAKE, CASE_SNAKE,
    EXTENSIONS, TOOL_FILES, SKIP_DIRS,
)
from agentskill.engine import (
    AnalysisResult,
    detect_case_style,
    extract_identifiers,
    analyze_file_content,
    analyze_codebase,
    extract_code_examples,
)
from agentskill.extractors.git import (
    extract_commit_prefixes,
    extract_branch_prefixes,
    analyze_git_commits,
    analyze_branches,
)
from agentskill.extractors.filesystem import (
    is_hidden_path,
    should_skip_dir,
    is_git_repo,
    scan_source_files,
    detect_tooling,
    get_project_metadata,
    analyze_dependency_philosophy,
)
from agentskill.extractors.structure import extract_repo_structure
from agentskill.extractors.commands import extract_commands
from agentskill.synthesis import AgentSynthesizer, SynthesisConfig
from agentskill.cli import analyze_repository, generate_agents_md


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

    def test_creation(self):
        result = AnalysisResult(
            languages={"python": {"naming": {}}},
            examples=["sample code"],
        )
        assert result.languages["python"] == {"naming": {}}
        assert result.examples == ["sample code"]

    def test_to_dict(self):
        result = AnalysisResult(
            languages={"python": {"naming": {}}},
            examples=["sample code"],
        )
        d = asdict(result)
        assert "languages" in d
        assert "examples" in d
        assert "git" in d
        assert "structure" in d


class TestDetectCaseStyle:
    """Tests for case style detection."""

    def test_screaming_snake(self):
        assert detect_case_style("MAX_SIZE") == CASE_SCREAMING_SNAKE

    def test_snake_case(self):
        assert detect_case_style("max_size") == CASE_SNAKE

    def test_kebab_case(self):
        assert detect_case_style("max-size") == CASE_KEBAB

    def test_camel_case(self):
        assert detect_case_style("maxSize") == CASE_CAMEL

    def test_pascal_case(self):
        assert detect_case_style("MaxSize") == CASE_PASCAL

    def test_mixed(self):
        assert detect_case_style("Max-Size") == CASE_MIXED

    def test_empty(self):
        assert detect_case_style("") == "unknown"


class TestExtractIdentifiers:
    """Tests for identifier extraction."""

    def test_function_def(self):
        line = "def my_function():"
        ids = extract_identifiers(line)
        assert "my_function" in ids

    def test_class_def(self):
        line = "class MyClass:"
        ids = extract_identifiers(line)
        assert "MyClass" in ids

    def test_use_import(self):
        line = "use std::collections::HashMap"
        ids = extract_identifiers(line)
        assert "std" in ids
        assert "collections" in ids

    def test_let_binding(self):
        line = "let my_variable = 1;"
        ids = extract_identifiers(line)
        assert "my_variable" in ids


class TestAnalyzeFileContent:
    """Tests for file content analysis."""

    def test_python_file(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "def my_function():\n"
            "    my_var = 1\n"
            "    # comment\n"
            "    return my_var"
        )

        content = py_file.read_text()
        result = analyze_file_content(py_file, content)

        assert "naming" in result
        assert "comments" in result
        assert result["metrics"]["total_lines"] == 4

    def test_rust_file(self, tmp_path):
        rs_file = tmp_path / "test.rs"
        rs_file.write_text(
            "fn my_function() {\n"
            "    let my_var = 1;\n"
            "    // comment\n"
            "}\n"
        )

        content = rs_file.read_text()
        result = analyze_file_content(rs_file, content)

        assert "naming" in result
        assert "comments" in result

    def test_error_patterns(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "def foo():\n"
            "    try:\n"
            "        x = 1\n"
            "    except:\n"
            "        raise ValueError()\n"
        )

        content = py_file.read_text()
        result = analyze_file_content(py_file, content)

        assert "error_handling" in result
        assert result["error_handling"].get("try_block", 0) > 0


class TestExtractCodeExamples:
    """Tests for code example extraction."""

    def test_extract_examples(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "def example_function():\n"
            "    pass\n"
            "\n"
            "class ExampleClass:\n"
            "    pass\n"
        )

        examples = extract_code_examples([py_file], max_examples=5)
        assert len(examples) > 0
        assert "example_function" in examples[0] or "ExampleClass" in examples[0]


class TestAnalyzeCodebase:
    """Tests for codebase analysis."""

    def test_single_language(self, tmp_path):
        py_file = tmp_path / "main.py"
        py_file.write_text("def main(): pass\n")

        files_by_ext = {".py": [py_file]}
        result = analyze_codebase(str(tmp_path), files_by_ext)

        assert "python" in result.languages

    def test_multiple_languages(self, tmp_path):
        py_file = tmp_path / "main.py"
        py_file.write_text("def main(): pass\n")
        rs_file = tmp_path / "main.rs"
        rs_file.write_text("fn main() {}\n")

        files_by_ext = {".py": [py_file], ".rs": [rs_file]}
        result = analyze_codebase(str(tmp_path), files_by_ext)

        assert len(result.languages) >= 1


class TestExtractCommitPrefixes:
    """Tests for commit prefix extraction."""

    def test_no_prefixes(self):
        assert extract_commit_prefixes(["fix bug", "update readme"]) == {}

    def test_conventional_prefixes(self):
        commits = ["feat: add feature", "fix: resolve bug", "feat: update"]
        result = extract_commit_prefixes(commits)
        assert "feat" in result


class TestExtractBranchPrefixes:
    """Tests for branch prefix extraction."""

    def test_single_prefix(self):
        result = extract_branch_prefixes(["feature/add", "feature/update"])
        assert result == {"feature": 2}


class TestIsHiddenPath:
    """Tests for hidden path detection."""

    def test_hidden(self):
        assert is_hidden_path(Path("/home/.config/app")) is True

    def test_not_hidden(self):
        assert is_hidden_path(Path("/home/projects/app")) is False


class TestShouldSkipDir:
    """Tests for skip directory detection."""

    def test_skip_node_modules(self):
        assert should_skip_dir(Path("/project/node_modules/pkg")) is True

    def test_no_skip(self):
        assert should_skip_dir(Path("/project/src")) is False


class TestIsGitRepo:
    """Tests for git repository detection."""

    def test_non_git(self, tmp_path):
        assert is_git_repo(str(tmp_path)) is False

    def test_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert is_git_repo(str(tmp_path)) is True


class TestExtractRepoStructure:
    """Tests for repository structure extraction."""

    def test_structure(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("x=1")

        result = extract_repo_structure(str(tmp_path))
        assert "structure" in result
        assert "file_naming" in result
        assert "test_patterns" in result

    def test_file_naming_detection(self, tmp_path):
        (tmp_path / "my_module.py").write_text("x=1")
        (tmp_path / "myUtils.js").write_text("x=1")

        result = extract_repo_structure(str(tmp_path))
        assert result["file_naming"]["dominant"] is not None


class TestExtractCommands:
    """Tests for command extraction."""

    def test_package_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text('{"scripts": {"test": "jest", "build": "tsc"}}')

        result = extract_commands(str(tmp_path))
        assert "test" in result or "build" in result

    def test_makefile(self, tmp_path):
        makefile = tmp_path / "Makefile"
        makefile.write_text("test:\n\tpytest\n")

        result = extract_commands(str(tmp_path))
        assert "test" in result


class TestDependencyPhilosophy:
    """Tests for dependency philosophy extraction."""

    def test_detect_lockfile(self, tmp_path):
        (tmp_path / "Cargo.lock").write_text("")

        result = analyze_dependency_philosophy(str(tmp_path))
        assert "Cargo.lock" in result["lockfiles"]
        assert result["manager"] == "cargo"

    def test_detect_package_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text('{"dependencies": {"lodash": "^4.0.0"}}')

        result = analyze_dependency_philosophy(str(tmp_path))
        assert result["manager"] == "npm"
        assert result["total_deps"] == 1


class TestSynthesis:
    """Tests for AGENTS.md synthesis."""

    def test_synthesize_basic(self):
        s = AgentSynthesizer()
        analyses = [{"languages": {"python": {"naming": {}}}, "examples": [],
                     "git": {}, "tooling": {}, "structure": {}, "dependencies": {}, "commands": {}}]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "Overview" in output

    def test_synthesize_with_structure(self):
        s = AgentSynthesizer()
        analyses = [{
            "languages": {},
            "examples": [],
            "git": {},
            "tooling": {},
            "structure": {
                "file_naming": {"dominant": "snake_case"},
                "depth_stats": {"max": 3, "avg": 1.5},
            },
            "dependencies": {},
            "commands": {},
        }]
        output = s.synthesize(analyses, ["/tmp/test"])
        assert "Repository Structure" in output or "snake_case" in output


class TestSynthesisConfig:
    """Tests for synthesis configuration."""

    def test_default_config(self):
        config = SynthesisConfig()
        assert config.include_overview is True
        assert config.include_git is True

    def test_custom_config(self):
        config = SynthesisConfig(include_git=False, include_red_lines=False)
        assert config.include_git is False
        assert config.include_red_lines is False


if __name__ == "__main__":
    runner = TestRunner()
    runner.run(TestAnalysisResult)
    runner.run(TestDetectCaseStyle)
    runner.run(TestExtractIdentifiers)
    runner.run(TestAnalyzeFileContent)
    runner.run(TestExtractCodeExamples)
    runner.run(TestAnalyzeCodebase)
    runner.run(TestExtractCommitPrefixes)
    runner.run(TestExtractBranchPrefixes)
    runner.run(TestIsHiddenPath)
    runner.run(TestShouldSkipDir)
    runner.run(TestIsGitRepo)
    runner.run(TestExtractRepoStructure)
    runner.run(TestExtractCommands)
    runner.run(TestDependencyPhilosophy)
    runner.run(TestSynthesis)
    runner.run(TestSynthesisConfig)
    sys.exit(runner.summary())
