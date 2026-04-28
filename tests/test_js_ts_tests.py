"""Tests for JavaScript and TypeScript test mapping."""

from commands.tests import _map_ts_tests, analyze_tests
from test_support import create_repo, write


class TestJsTsTestDetection:
    def test_detects_test_ts_files(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/foo.ts": "export function foo() {}\n",
                "src/foo.test.ts": "test('foo', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert result["typescript"]["test_files"] == 1
        assert result["typescript"]["source_files"] == 1

    def test_detects_spec_tsx_files(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/Button.tsx": "export const Button = () => {}\n",
                "src/Button.spec.tsx": "describe('Button', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert result["typescript"]["test_files"] == 1

    def test_detects_test_js_files(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/util.js": "module.exports = {}\n",
                "src/util.test.js": "test('util', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        # JavaScript files may be categorized under typescript or javascript
        ts_count = result.get("typescript", {}).get("test_files", 0)
        js_count = result.get("javascript", {}).get("test_files", 0)
        assert ts_count + js_count >= 1

    def test_detects_cjs_test_files(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/util.cjs": "module.exports = {}\n",
                "src/util.test.cjs": "test('util', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        # .cjs files should be detected
        assert (
            result["typescript"]["test_files"] >= 1
            or result.get("javascript", {}).get("test_files", 0) >= 1
        )


class TestJsTsTestMapping:
    def test_maps_test_to_source_file(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/foo.ts": "export function foo() {}\n",
                "src/foo.test.ts": "test('foo', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        coverage = result["typescript"]["coverage_shape"]
        assert len(coverage["mapped"]) == 1
        assert coverage["mapped"][0]["source"] == "src/foo.ts"
        assert coverage["mapped"][0]["test"] == "src/foo.test.ts"

    def test_maps_spec_to_source_file(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/components/Button.tsx": "export const Button = () => {}\n",
                "src/components/Button.spec.tsx": "describe('Button', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        coverage = result["typescript"]["coverage_shape"]
        mapped_sources = [m["source"] for m in coverage["mapped"]]
        assert "src/components/Button.tsx" in mapped_sources

    def test_identifies_untested_source_files(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/covered.ts": "export function covered() {}\n",
                "src/covered.test.ts": "test('covered', () => {})\n",
                "src/uncovered.ts": "export function uncovered() {}\n",
            },
        )

        result = analyze_tests(str(repo))

        coverage = result["typescript"]["coverage_shape"]
        assert "src/uncovered.ts" in coverage["untested_source_files"]
        assert "src/covered.ts" not in coverage["untested_source_files"]

    def test_handles_colocated_tests(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/utils.ts": "export function util() {}\n",
                "src/utils.spec.ts": "describe('util', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        coverage = result["typescript"]["coverage_shape"]
        assert len(coverage["mapped"]) == 1


class TestJsTsFrameworkDetection:
    def test_detects_jest_from_package_json(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "package.json": '{"scripts": {"test": "jest"}}\n',
                "src/app.test.ts": "test('app', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert result["typescript"]["framework"] == "jest"

    def test_detects_vitest_from_package_json(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "package.json": '{"devDependencies": {"vitest": "^1.0.0"}}\n',
                "src/app.test.ts": "test('app', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert result["typescript"]["framework"] == "vitest"

    def test_detects_mocha_from_package_json(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "package.json": '{"scripts": {"test": "mocha"}}\n',
                "src/app.test.ts": "describe('app', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert result["typescript"]["framework"] == "mocha"

    def test_falls_back_to_jest(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "package.json": "{}\n",
                "src/app.test.ts": "test('app', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert result["typescript"]["framework"] == "jest"


class TestJsTsNamingPatterns:
    def test_detects_test_naming_pattern(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/foo.test.ts": "test('foo works', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert result["typescript"]["naming"]["file_pattern"] == "<module>.test.ts"

    def test_detects_spec_naming_pattern(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/bar.spec.ts": "describe('bar', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert result["typescript"]["naming"]["file_pattern"] == "<module>.spec.ts"

    def test_detects_it_pattern(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/app.test.ts": "it('should work', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert (
            result["typescript"]["naming"]["function_pattern"] == "it('<description>')"
        )

    def test_detects_describe_pattern(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/app.test.ts": "describe('App', () => {})\n",
            },
        )

        result = analyze_tests(str(repo))

        assert (
            result["typescript"]["naming"]["class_pattern"] == "describe('<Subject>')"
        )
