from commands.tests import (
    _detect_python_framework,
    _detect_ts_framework,
    _extract_run_command,
    _find_conftest_files,
    _map_jvm_tests,
    _map_python_tests,
    _map_stem_tests,
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


def test_tests_detect_java_and_kotlin_mappings(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "pom.xml": "<project/>\n",
            "build.gradle.kts": "plugins {}\n",
            "src/main/java/com/acme/UserService.java": (
                "package com.acme;\npublic class UserService {}\n"
            ),
            "src/test/java/com/acme/UserServiceTest.java": (
                "import org.junit.jupiter.api.Test;\n\n"
                "class UserServiceTest {\n"
                "    @Test\n"
                "    void starts() {}\n"
                "}\n"
            ),
            "src/main/kotlin/com/acme/UserService.kt": (
                "package com.acme\nclass UserService\n"
            ),
            "src/test/kotlin/com/acme/UserServiceTest.kt": (
                "import kotlin.test.Test\n\n"
                "class UserServiceTest {\n"
                "    @Test\n"
                "    fun works() {}\n"
                "}\n"
            ),
        },
    )

    result = analyze_tests(str(repo))
    assert result["java"]["framework"] == "junit"

    assert result["java"]["coverage_shape"]["mapped"] == [
        {
            "source": "src/main/java/com/acme/UserService.java",
            "test": "src/test/java/com/acme/UserServiceTest.java",
        }
    ]

    assert result["kotlin"]["framework"] == "kotlin-test"

    assert result["kotlin"]["coverage_shape"]["mapped"] == [
        {
            "source": "src/main/kotlin/com/acme/UserService.kt",
            "test": "src/test/kotlin/com/acme/UserServiceTest.kt",
        }
    ]


def test_map_jvm_tests_reports_untested_sources(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "src/main/java/com/acme/UserService.java": "public class UserService {}\n",
            "src/main/java/com/acme/Helper.java": "class Helper {}\n",
            "src/test/java/com/acme/UserServiceTests.java": "class UserServiceTests {}\n",
        },
    )

    mapping = _map_jvm_tests(
        [
            repo / "src/main/java/com/acme/UserService.java",
            repo / "src/main/java/com/acme/Helper.java",
        ],
        [repo / "src/test/java/com/acme/UserServiceTests.java"],
        repo,
    )

    assert mapping["mapped"] == [
        {
            "source": "src/main/java/com/acme/UserService.java",
            "test": "src/test/java/com/acme/UserServiceTests.java",
        }
    ]
    assert mapping["untested_source_files"] == ["src/main/java/com/acme/Helper.java"]


def test_tests_detect_csharp_and_c_family_mappings(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "src/UserService.cs": "public class UserService {}\n",
            "tests/UserServiceTests.cs": (
                "using Xunit;\n\n"
                "public class UserServiceTests {\n"
                "    [Fact]\n"
                "    public void Starts() {}\n"
                "}\n"
            ),
            "src/foo.c": "int add(int a, int b) { return a + b; }\n",
            "tests/foo_test.c": '#include "unity.h"\n',
            "src/bar.cpp": "int add(int a, int b) { return a + b; }\n",
            "tests/bar_test.cpp": "#include <gtest/gtest.h>\nTEST(BarTest, Works) {}\n",
        },
    )

    result = analyze_tests(str(repo))

    assert result["csharp"]["framework"] == "xunit"
    assert result["csharp"]["coverage_shape"]["mapped"] == [
        {"source": "src/UserService.cs", "test": "tests/UserServiceTests.cs"}
    ]

    assert result["c"]["framework"] == "unity"
    assert result["c"]["coverage_shape"]["mapped"] == [
        {"source": "src/foo.c", "test": "tests/foo_test.c"}
    ]

    assert result["cpp"]["framework"] == "gtest"
    assert result["cpp"]["coverage_shape"]["mapped"] == [
        {"source": "src/bar.cpp", "test": "tests/bar_test.cpp"}
    ]


def test_map_stem_tests_reports_untested_sources(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "src/foo.c": "int add(int a, int b) { return a + b; }\n",
            "src/helper.c": "int helper(void) { return 1; }\n",
            "tests/foo_test.c": "void test_add(void) {}\n",
        },
    )

    mapping = _map_stem_tests(
        [repo / "src/foo.c", repo / "src/helper.c"],
        [repo / "tests/foo_test.c"],
        repo,
    )

    assert mapping["mapped"] == [{"source": "src/foo.c", "test": "tests/foo_test.c"}]
    assert mapping["untested_source_files"] == ["src/helper.c"]


def test_tests_reports_invalid_repo_paths(tmp_path):
    missing = tmp_path / "missing"

    assert analyze_tests(str(missing)) == {
        "error": f"path does not exist: {missing}",
        "script": "tests",
    }
