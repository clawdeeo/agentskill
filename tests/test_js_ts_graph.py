"""Tests for JavaScript and TypeScript graph extraction."""

from commands.graph import (
    _extract_js_ts_imports,
    _resolve_js_ts_import,
    _strip_js_ts_comments,
    build_graph,
)
from test_support import create_repo


class TestJsTsCommentStripping:
    def test_strip_line_comments(self):
        source = "import foo from './foo' // import comment"
        result = _strip_js_ts_comments(source)
        assert "//" not in result
        assert "import foo" in result

    def test_strip_block_comments(self):
        source = """/* block comment */ import foo from './foo'"""
        result = _strip_js_ts_comments(source)
        assert "/*" not in result
        assert "*/" not in result
        assert "import foo" in result


class TestJsTsImportExtraction:
    def test_extract_es_imports(self):
        source = "import foo from './foo'\nimport { bar } from '../bar'"
        imports = _extract_js_ts_imports(source)
        specs = [spec for spec, _ in imports]
        assert "./foo" in specs
        assert "../bar" in specs

    def test_extract_re_exports(self):
        source = "export { foo } from './foo'\nexport * from './bar'"
        imports = _extract_js_ts_imports(source)
        specs = [spec for spec, _ in imports]
        assert "./foo" in specs
        assert "./bar" in specs

    def test_extract_require_calls(self):
        source = "const foo = require('./foo')\nrequire('./setup')"
        imports = _extract_js_ts_imports(source)
        specs = [spec for spec, _ in imports]
        assert "./foo" in specs
        assert "./setup" in specs

    def test_ignores_external_imports(self):
        source = "import React from 'react'\nimport lodash from 'lodash'"
        imports = _extract_js_ts_imports(source)
        assert len(imports) == 0

    def test_ignores_imports_in_comments(self):
        source = "// import foo from './foo'\n/* import bar from './bar' */"
        imports = _extract_js_ts_imports(source)
        assert len(imports) == 0


class TestJsTsImportResolution:
    def test_resolve_exact_path(self, tmp_path):
        foo_file = tmp_path / "foo.ts"
        foo_file.write_text("")
        files = {"foo.ts"}
        result = _resolve_js_ts_import(tmp_path / "index.ts", "./foo", tmp_path, files)
        assert result == "foo.ts"

    def test_resolve_with_extension(self, tmp_path):
        foo_file = tmp_path / "foo.ts"
        foo_file.write_text("")
        files = {"foo.ts"}
        result = _resolve_js_ts_import(
            tmp_path / "index.ts", "./foo.ts", tmp_path, files
        )
        assert result == "foo.ts"

    def test_resolve_index_file(self, tmp_path):
        (tmp_path / "utils").mkdir()
        index_file = tmp_path / "utils" / "index.ts"
        index_file.write_text("")
        files = {"utils/index.ts"}
        result = _resolve_js_ts_import(tmp_path / "app.ts", "./utils", tmp_path, files)
        assert result == "utils/index.ts"

    def test_returns_none_for_external(self, tmp_path):
        files: set[str] = set()
        result = _resolve_js_ts_import(tmp_path / "index.ts", "react", tmp_path, files)
        assert result is None


class TestJsTsGraphIntegration:
    def test_graph_extracts_es_imports(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/index.ts": "import foo from './foo'\n",
                "src/foo.ts": "export const foo = 1\n",
            },
        )

        result = build_graph(str(repo), "typescript")

        assert {"from": "src/index.ts", "to": "src/foo.ts", "line": 1} in result[
            "typescript"
        ]["edges"]

    def test_graph_extracts_re_exports(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/index.ts": "export { bar } from './bar'\n",
                "src/bar.ts": "export const bar = 1\n",
            },
        )

        result = build_graph(str(repo), "typescript")

        assert {"from": "src/index.ts", "to": "src/bar.ts", "line": 1} in result[
            "typescript"
        ]["edges"]

    def test_graph_extracts_commonjs_requires(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/util.js": "module.exports = {}\n",
                "src/app.js": "const util = require('./util')\n",
            },
        )

        result = build_graph(str(repo), "javascript")

        assert {"from": "src/app.js", "to": "src/util.js", "line": 1} in result[
            "javascript"
        ]["edges"]

    def test_graph_ignores_external_packages(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/app.ts": "import React from 'react'\nimport lodash from 'lodash'\n",
            },
        )

        result = build_graph(str(repo), "typescript")

        assert len(result["typescript"]["edges"]) == 0

    def test_graph_handles_jsx_tsx_files(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/App.tsx": "import { Button } from './Button'\n",
                "src/Button.tsx": "export const Button = () => {}\n",
            },
        )

        result = build_graph(str(repo), "typescript")

        assert {"from": "src/App.tsx", "to": "src/Button.tsx", "line": 1} in result[
            "typescript"
        ]["edges"]

    def test_graph_handles_mjs_cjs_files(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "src/util.mjs": "export const util = 1\n",
                "src/main.cjs": "const { util } = require('./util')\n",
            },
        )

        result = build_graph(str(repo))

        # JS-only repos are categorized under "javascript" key
        key = "javascript" if "javascript" in result else "typescript"
        assert key in result
        edges = result[key].get("edges", [])
        assert any(e["from"] == "src/main.cjs" for e in edges)
