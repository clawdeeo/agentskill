from pathlib import Path

from commands.config import (
    _parse_editorconfig,
    _parse_editorconfig_for_lang,
    _parse_ini_section,
    detect,
)
from lib.parsers import load_toml_safe, load_yaml_safe
from test_support import create_repo, create_sample_repo


def test_config_detects_python_tooling(tmp_path):
    repo = create_sample_repo(tmp_path)
    result = detect(str(repo))

    assert "python" in result
    assert result["python"]["linter"]["name"] == "ruff"
    assert "editorconfig" in result


def test_config_parsers_cover_toml_yaml_ini_and_editorconfig(tmp_path):
    parsed_toml = load_toml_safe(
        '[tool.demo]\nenabled = true\nnames = [\n  "a",\n  "b",\n]\n'
    )

    parsed_yaml = load_yaml_safe("tool:\n  enabled: true\n  count: 3\n")
    parsed_ini = _parse_ini_section("[flake8]\nmax-line-length = 88\n", "[flake8]")

    ec_path = tmp_path / ".editorconfig"
    ec_path.write_text("[*]\nindent_style = space\n[*.py]\nindent_size = 4\n")
    sections = _parse_editorconfig(ec_path)

    assert parsed_toml["tool"]["demo"]["enabled"] is True
    assert parsed_toml["tool"]["demo"]["names"] == ["a", "b"]
    assert parsed_yaml["tool"]["enabled"] is True
    assert parsed_ini == {"max-line-length": "88"}

    assert _parse_editorconfig_for_lang(sections, "python") == {
        "indent_style": "space",
        "indent_size": "4",
    }


def test_config_detects_typescript_go_and_rust_tooling(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            ".prettierrc.json": '{"semi": false}\n',
            ".eslintrc.yml": "rules:\n  semi: off\n",
            "tsconfig.json": '{"compilerOptions":{"strict":true}}\n',
            "go.mod": "module example.com/demo\n",
            ".golangci.yml": "run:\n  timeout: 2m\n",
            "Cargo.toml": '[package]\nname = "demo"\n',
            "rustfmt.toml": "max_width = 100\n",
            "clippy.toml": 'msrv = "1.70"\n',
        },
    )

    result = detect(str(repo))

    assert result["typescript"]["formatter"]["name"] == "prettier"
    assert result["typescript"]["linter"]["name"] == "eslint"
    assert result["typescript"]["type_checker"]["name"] == "tsc"
    assert result["go"]["formatter"]["name"] == "gofmt"
    assert result["go"]["linter"]["name"] == "golangci-lint"
    assert result["rust"]["formatter"]["name"] == "rustfmt"
    assert result["rust"]["linter"]["name"] == "clippy"


def test_config_reports_invalid_repo_paths(tmp_path):
    missing = tmp_path / "missing"

    assert detect(str(missing)) == {
        "error": f"path does not exist: {missing}",
        "script": "config",
    }


def test_config_load_toml_safe_handles_invalid_toml():
    assert load_toml_safe("invalid = [this is wrong") == {}


def test_config_load_toml_safe_normalizes_non_dict_output():
    assert load_toml_safe('key = "value"') == {"key": "value"}
    assert load_toml_safe("[section]\nkey = 1") == {"section": {"key": 1}}


def test_config_load_toml_safe_returns_empty_on_unavailable(monkeypatch):
    import lib.parsers as parsers_mod

    monkeypatch.setattr(parsers_mod, "_toml_module", None)
    monkeypatch.setattr(parsers_mod, "_toml_checked", False)

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("tomllib", "tomli"):
            raise ImportError(name)

        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert load_toml_safe('[tool]\nkey = "value"') == {}


def test_config_load_yaml_safe_handles_invalid_yaml():
    assert load_yaml_safe("invalid: [broken") == {}


def test_config_load_yaml_safe_normalizes_non_dict_output():
    assert load_yaml_safe("tool:\n  enabled: true") == {"tool": {"enabled": True}}
    assert load_yaml_safe("- item1\n- item2") == {}


def test_config_load_yaml_safe_returns_empty_on_unavailable(monkeypatch):
    import lib.parsers as parsers_mod

    monkeypatch.setattr(parsers_mod, "_yaml_module", None)
    monkeypatch.setattr(parsers_mod, "_yaml_checked", False)

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError(name)

        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert load_yaml_safe("tool:\n  key: value") == {}


def test_config_parses_real_toml_config():
    toml = (
        Path(__file__).parent / "fixtures" / "python" / "pyproject.toml"
    ).read_text()
    data = load_toml_safe(toml)

    assert data["tool"]["ruff"]["line-length"] == 88
    assert data["tool"]["ruff"]["target-version"] == "py311"
    assert data["tool"]["black"]["line-length"] == 88
    assert data["tool"]["mypy"]["python_version"] == "3.11"


def test_config_parses_real_yaml_configs():
    prettier = (Path(__file__).parent / "fixtures" / "js" / "prettier.yaml").read_text()
    eslint = (Path(__file__).parent / "fixtures" / "js" / "eslint.yaml").read_text()
    golangci = (Path(__file__).parent / "fixtures" / "go" / "golangci.yml").read_text()

    prettier_data = load_yaml_safe(prettier)
    eslint_data = load_yaml_safe(eslint)
    golangci_data = load_yaml_safe(golangci)

    assert prettier_data["semi"] is False
    assert prettier_data["tabWidth"] == 2

    assert eslint_data["rules"]["semi"] is False
    assert eslint_data["rules"]["indent"][1] == 2

    assert golangci_data["run"]["timeout"] == "2m"
    assert golangci_data["run"]["skip-dirs"] == ["vendor", ".git"]


def test_config_parses_rust_toml_configs():
    rustfmt = (Path(__file__).parent / "fixtures" / "rust" / "rustfmt.toml").read_text()
    clippy = (Path(__file__).parent / "fixtures" / "rust" / "clippy.toml").read_text()

    rustfmt_data = load_toml_safe(rustfmt)
    clippy_data = load_toml_safe(clippy)

    assert rustfmt_data["max_width"] == 100
    assert rustfmt_data["tab_spaces"] == 4

    assert clippy_data["msrv"] == "1.70"
    assert "clippy::pedantic" in clippy_data["deny"]


def test_config_detects_from_fixture_configs(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "pyproject.toml": (
                Path(__file__).parent / "fixtures" / "python" / "pyproject.toml"
            ).read_text(),
            ".prettierrc.yaml": (
                Path(__file__).parent / "fixtures" / "js" / "prettier.yaml"
            ).read_text(),
            ".eslintrc.yaml": (
                Path(__file__).parent / "fixtures" / "js" / "eslint.yaml"
            ).read_text(),
            "go.mod": "module example.com/demo\n",
            ".golangci.yml": (
                Path(__file__).parent / "fixtures" / "go" / "golangci.yml"
            ).read_text(),
            "main.go": "package main\n",
            "rustfmt.toml": (
                Path(__file__).parent / "fixtures" / "rust" / "rustfmt.toml"
            ).read_text(),
            "clippy.toml": (
                Path(__file__).parent / "fixtures" / "rust" / "clippy.toml"
            ).read_text(),
            "main.rs": "fn main() {}",
        },
    )

    result = detect(str(repo))

    assert result["python"]["linter"]["name"] == "ruff"
    assert result["python"]["formatter"]["name"] == "black"
    assert result["typescript"]["formatter"]["name"] == "prettier"
    assert result["typescript"]["linter"]["name"] == "eslint"
    assert result["go"]["linter"]["name"] == "golangci-lint"
    assert result["rust"]["formatter"]["name"] == "rustfmt"
    assert result["rust"]["linter"]["name"] == "clippy"

    assert "E" in result["python"]["linter"]["settings"]["select"]
    assert result["rust"]["formatter"]["settings"]["max_width"] == 100


def test_config_invalid_toml_returns_empty():
    assert load_toml_safe("[tool.ruff\nline-length = 88") == {}


def test_config_invalid_yaml_returns_empty():
    assert load_yaml_safe("rules:\n - invalid: [") == {}


def test_config_mixed_formats_parsed_independently(tmp_path):
    repo = create_repo(
        tmp_path,
        {
            "pyproject.toml": "[tool.ruff]\nline-length = 88",
            ".prettierrc.yaml": "semi: false",
            "go.mod": "module demo\n",
            "main.go": "package main\n",
        },
    )

    result = detect(str(repo))

    assert result["python"]["linter"]["name"] == "ruff"
    assert result["typescript"]["formatter"]["name"] == "prettier"
    assert "go" in result
