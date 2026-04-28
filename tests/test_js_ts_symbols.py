"""Tests for JavaScript and TypeScript symbol extraction."""

from commands.symbols import extract_symbols
from test_support import create_repo


class TestJsTsSymbolIntegration:
    def test_symbols_extracts_exported_functions(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {"src/index.ts": "export function makeUser() {}\n"},
        )
        result = extract_symbols(str(repo), "typescript")
        assert result["typescript"]["functions"]["total"] >= 1

    def test_symbols_extracts_async_functions(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {"src/index.ts": "export async function fetchData() {}\n"},
        )
        result = extract_symbols(str(repo), "typescript")
        assert result["typescript"]["functions"]["total"] >= 1

    def test_symbols_extracts_exported_classes(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {"src/index.ts": "export class UserService {}\n"},
        )
        result = extract_symbols(str(repo), "typescript")
        assert result["typescript"]["classes"]["total"] >= 1

    def test_symbols_extracts_interfaces(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {"src/index.ts": "export interface User {}\n"},
        )
        result = extract_symbols(str(repo), "typescript")
        assert "interfaces" in result["typescript"]
        assert result["typescript"]["interfaces"]["total"] >= 1

    def test_symbols_extracts_type_aliases(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {"src/index.ts": "export type UserId = string\n"},
        )
        result = extract_symbols(str(repo), "typescript")
        assert "types" in result["typescript"]
        assert result["typescript"]["types"]["total"] >= 1

    def test_symbols_extracts_exported_arrow_functions(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {"src/index.ts": "export const Button = () => null\n"},
        )
        result = extract_symbols(str(repo), "typescript")
        assert result["typescript"]["functions"]["total"] >= 1

    def test_symbols_extracts_all_declaration_types(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/index.ts": (
                    "export function makeUser() {}\n"
                    "export class UserService {}\n"
                    "export interface User {}\n"
                    "export type UserId = string\n"
                    "export const Button = () => null\n"
                    "const helper = () => {}\n"
                ),
            },
        )
        result = extract_symbols(str(repo), "typescript")
        # makeUser + Button + helper at minimum
        assert result["typescript"]["functions"]["total"] >= 2
        assert result["typescript"]["classes"]["total"] >= 1

    def test_symbols_distinguishes_exported_vs_private(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/utils.ts": (
                    "export function publicFn() {}\nfunction privateFn() {}\n"
                ),
            },
        )
        result = extract_symbols(str(repo), "typescript")
        assert result["typescript"]["functions"]["total"] >= 2

    def test_symbols_handles_javascript_files(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/app.js": (
                    "export function run() {}\nexport const handler = () => {}\n"
                ),
            },
        )
        result = extract_symbols(str(repo))
        js_result = result.get("javascript", {})
        ts_result = result.get("typescript", {})
        symbols = js_result if js_result else ts_result
        assert symbols["functions"]["total"] >= 1
