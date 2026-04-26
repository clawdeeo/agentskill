from commands.tests import (
    _detect_python_framework,
    _detect_ts_framework,
    _extract_run_command,
    _find_conftest_files,
    _map_python_tests,
    analyze_tests,
)
from test_support import create_repo, create_sample_repo, write


def test_tests_detects_pytest_and_mappings(tmp_path):
    repo = create_sample_repo(tmp_path)
    result = analyze_tests(str(repo))

    assert result["python"]["framework"] == "pytest"
    assert result["python"]["fixtures"]["uses_conftest"] is False
    assert result["python"]["coverage_shape"]["mapped"]


def test_tests_detect_frameworks_run_command_and_conftest(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "pytest.ini": "[pytest]\n",
            "Makefile": "test:\n\tpython -m pytest -q\n",
            "pkg/mod.py": "def run():\n    return 1\n",
            "tests/test_mod.py": "def test_run():\n    assert True\n",
            "tests/conftest.py": (
                "import pytest\n\n@pytest.fixture\ndef repo_fixture():\n    return 1\n"
            ),
        },
    )

    result = analyze_tests(str(repo))

    assert _detect_python_framework(repo, []) == "pytest"
    assert _extract_run_command(repo, "pytest") == "python -m pytest -q"
    assert _find_conftest_files(repo) == ["tests/conftest.py"]
    assert result["python"]["fixtures"]["fixture_names"] == ["repo_fixture"]


def test_tests_detect_unittest_ts_and_mapping_gaps(tmp_path):
    repo = create_repo(tmp_path)
    write(repo, "pkg/core.py", "def work():\n    return 1\n")
    write(repo, "pkg/extra.py", "def extra():\n    return 2\n")

    write(
        repo,
        "tests/core_test.py",
        "import unittest\n\nclass CoreTest(unittest.TestCase):\n    pass\n",
    )

    write(
        repo,
        "package.json",
        '{"scripts":{"test":"vitest run"},"devDependencies":{"vitest":"1.0.0"}}\n',
    )

    write(repo, "src/app.ts", "export function run() { return 1 }\n")
    write(repo, "src/app.spec.ts", "describe('app', () => { it('works', () => {}) })\n")

    mapping = _map_python_tests(
        [repo / "pkg" / "core.py", repo / "pkg" / "extra.py"],
        [repo / "tests" / "core_test.py"],
        repo,
    )

    result = analyze_tests(str(repo))
    framework, command = _detect_ts_framework(repo)

    assert result["python"]["framework"] == "unittest"

    assert mapping["mapped"] == [
        {"source": "pkg/core.py", "test": "tests/core_test.py"}
    ]

    assert mapping["test_files_without_source_match"] == []
    assert sorted(mapping["untested_source_files"]) == ["pkg/extra.py"]
    assert framework == "vitest"
    assert command == "vitest run"
    assert result["typescript"]["naming"]["file_pattern"] == "<module>.spec.ts"
