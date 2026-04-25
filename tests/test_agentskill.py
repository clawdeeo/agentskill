#!/usr/bin/env python3
"""Self-contained test runner for agentskill tests."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from agentskill import (
    CASE_CAMEL,
    CASE_KEBAB,
    CASE_MIXED,
    CASE_PASCAL,
    CASE_SCREAMING_SNAKE,
    CASE_SNAKE,
    LANG_RUST,
    LANG_PYTHON,
    NAME_VAR,
    NAME_FUNCTION,
    NAME_TYPE,
    NAME_CONST,
    detect_case_style,
    extract_commit_prefixes,
    extract_branch_prefixes,
    is_git_repo,
    should_skip_dir,
    is_hidden_path,
)


class TestRunner:
    """Simple test runner that mimics pytest behavior."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def run(self, test_class):
        """Run all test methods in a class."""
        print(f"\n{test_class.__doc__ or test_class.__name__}")
        print("-" * 40)

        for name in dir(test_class):
            if name.startswith("test_"):
                method = getattr(test_class(), name)
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
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'=' * 40}")
        print(f"Results: {self.passed}/{total} passed")
        if self.failed:
            print(f"         {self.failed}/{total} failed")
            return 1
        return 0


class TestDetectCaseStyle:
    """Tests for detect_case_style function."""

    def test_screaming_snake_case(self):
        assert detect_case_style("MAX_SIZE") == CASE_SCREAMING_SNAKE
        assert detect_case_style("API_KEY") == CASE_SCREAMING_SNAKE

    def test_snake_case(self):
        assert detect_case_style("max_size") == CASE_SNAKE
        assert detect_case_style("api_key") == CASE_SNAKE

    def test_kebab_case(self):
        assert detect_case_style("max-size") == CASE_KEBAB
        assert detect_case_style("api-key") == CASE_KEBAB

    def test_camel_case(self):
        assert detect_case_style("maxSize") == CASE_CAMEL
        assert detect_case_style("apiKey") == CASE_CAMEL

    def test_pascal_case(self):
        assert detect_case_style("MaxSize") == CASE_PASCAL
        assert detect_case_style("ApiKey") == CASE_PASCAL

    def test_mixed(self):
        assert detect_case_style("Max-Size") == CASE_MIXED
        assert detect_case_style("max_Size") == CASE_MIXED


class TestExtractCommitPrefixes:
    """Tests for extract_commit_prefixes function."""

    def test_no_prefixes(self):
        commits = ["fix bug", "update readme", "[feat] missing colon"]
        assert extract_commit_prefixes(commits) == {}

    def test_single_prefix(self):
        commits = ["[feat]: add new feature", "[feat]: update logic"]
        result = extract_commit_prefixes(commits)
        assert result == {"[feat]": 2}

    def test_multiple_prefixes(self):
        commits = [
            "[feat]: add new feature",
            "[fix]: resolve bug",
            "[feat]: update logic",
            "[fix]: another fix",
            "[docs]: update readme",
        ]
        result = extract_commit_prefixes(commits)
        assert result["[feat]"] == 2
        assert result["[fix]"] == 2
        assert result["[docs]"] == 1

    def test_empty_commits(self):
        assert extract_commit_prefixes([]) == {}


class TestExtractBranchPrefixes:
    """Tests for extract_branch_prefixes function."""

    def test_single_prefix(self):
        branches = ["feature/add-thing", "feature/update-thing"]
        result = extract_branch_prefixes(branches)
        assert result == {"feature": 2}

    def test_multiple_prefixes(self):
        branches = [
            "feature/add-thing",
            "fix/bug-1",
            "feature/update-thing",
            "fix/bug-2",
        ]
        result = extract_branch_prefixes(branches)
        assert result["feature"] == 2
        assert result["fix"] == 2

    def test_remotes_filtered(self):
        branches = ["remotes/origin/feature/add-thing", "feature/update-thing"]
        result = extract_branch_prefixes(branches)
        assert result["feature"] == 2

    def test_no_prefix(self):
        branches = ["main", "master"]
        assert extract_branch_prefixes(branches) == {}


class TestIsGitRepo:
    """Tests for is_git_repo function."""

    def test_non_git_directory(self, tmp_path):
        assert not is_git_repo(str(tmp_path))

    def test_git_directory(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert is_git_repo(str(tmp_path))


class TestShouldSkipDir:
    """Tests for should_skip_dir function."""

    def test_skip_node_modules(self):
        path = Path("/project/node_modules/some-package")
        assert should_skip_dir(path)

    def test_skip_target(self):
        path = Path("/rust-project/target/debug")
        assert should_skip_dir(path)

    def test_skip_pycache(self):
        path = Path("/python-project/__pycache__")
        assert should_skip_dir(path)

    def test_no_skip(self):
        path = Path("/project/src")
        assert not should_skip_dir(path)


class TestIsHiddenPath:
    """Tests for is_hidden_path function."""

    def test_hidden_directory(self):
        path = Path("/home/user/.config/app")
        assert is_hidden_path(path)

    def test_not_hidden(self):
        path = Path("/home/user/projects/app")
        assert not is_hidden_path(path)

    def test_hidden_file(self):
        path = Path("/home/user/.bashrc")
        assert is_hidden_path(path)


class TestConstants:
    """Tests that constants are properly defined and distinct."""

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


if __name__ == "__main__":
    runner = TestRunner()

    runner.run(TestDetectCaseStyle)
    runner.run(TestExtractCommitPrefixes)
    runner.run(TestExtractBranchPrefixes)
    runner.run(TestIsGitRepo)
    runner.run(TestShouldSkipDir)
    runner.run(TestIsHiddenPath)
    runner.run(TestConstants)

    sys.exit(runner.summary())
