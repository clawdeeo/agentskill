"""Tests for Rust module graph extraction."""

from commands.graph import (
    _extract_rust_mods_and_uses,
    _resolve_rust_mod,
    _strip_rust_comments,
    build_graph,
)
from test_support import create_repo


class TestRustCommentStripping:
    def test_strip_line_comments(self):
        source = "mod parser; // comment"
        result = _strip_rust_comments(source)
        assert "//" not in result
        assert "mod parser" in result

    def test_strip_block_comments(self):
        source = "/* comment */ mod parser;"
        result = _strip_rust_comments(source)
        assert "/*" not in result
        assert "mod parser" in result


class TestRustModExtraction:
    def test_extract_mod_declarations(self):
        source = "pub mod parser;\nmod config;\n"
        results = _extract_rust_mods_and_uses(source)
        mods = [r for r in results if r[0].startswith("mod:")]
        mod_names = [r[0][4:] for r in mods]
        assert "parser" in mod_names
        assert "config" in mod_names

    def test_extract_use_statements(self):
        source = "use crate::parser::parse;\nuse super::utils;\n"
        results = _extract_rust_mods_and_uses(source)
        uses = [r for r in results if r[0].startswith("use:")]
        use_paths = [r[0][4:] for r in uses]
        assert "crate::parser::parse" in use_paths
        assert "super::utils" in use_paths

    def test_ignores_external_crates(self):
        source = "use std::collections::HashMap;\nuse serde::Deserialize;\n"
        results = _extract_rust_mods_and_uses(source)
        uses = [r for r in results if r[0].startswith("use:")]
        assert len(uses) == 0

    def test_ignores_mods_in_comments(self):
        source = "// mod ignored;\n/* mod also_ignored; */\n"
        results = _extract_rust_mods_and_uses(source)
        assert len(results) == 0


class TestRustModResolution:
    def test_resolve_sibling_file(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "parser.rs").write_text("")

        files = {"src/parser.rs"}
        result = _resolve_rust_mod(
            "parser", tmp_path / "src" / "lib.rs", tmp_path, files
        )
        assert result == "src/parser.rs"

    def test_resolve_mod_rs_file(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "parser").mkdir()
        (tmp_path / "src" / "parser" / "mod.rs").write_text("")

        files = {"src/parser/mod.rs"}
        result = _resolve_rust_mod(
            "parser", tmp_path / "src" / "lib.rs", tmp_path, files
        )
        assert result == "src/parser/mod.rs"

    def test_returns_none_for_missing(self, tmp_path):
        files: set[str] = set()
        result = _resolve_rust_mod(
            "missing", tmp_path / "src" / "lib.rs", tmp_path, files
        )
        assert result is None


class TestRustGraphIntegration:
    def test_graph_resolves_mod_declarations(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "Cargo.toml": '[package]\nname = "demo"\nversion = "0.1.0"\nedition = "2021"\n',
                "src/lib.rs": "pub mod parser;\nmod config;\n",
                "src/parser.rs": "pub fn parse() {}\n",
                "src/config.rs": "fn load() {}\n",
            },
        )

        result = build_graph(str(repo), "rust")

        assert any(
            e["from"] == "src/lib.rs" and e["to"] == "src/parser.rs"
            for e in result["rust"]["edges"]
        )
        assert any(
            e["from"] == "src/lib.rs" and e["to"] == "src/config.rs"
            for e in result["rust"]["edges"]
        )

    def test_graph_ignores_external_use_paths(self, tmp_path):
        repo = create_repo(
            tmp_path,
            {
                "Cargo.toml": '[package]\nname = "demo"\n',
                "src/lib.rs": "use std::collections::HashMap;\n",
            },
        )

        result = build_graph(str(repo), "rust")
        assert len(result["rust"]["edges"]) == 0
