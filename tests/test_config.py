from commands.config import (
    _parse_editorconfig,
    _parse_editorconfig_for_lang,
    _parse_ini_section,
    _parse_yaml_simple,
    detect,
)
from lib.parsers import load_toml_safe
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

    parsed_yaml = _parse_yaml_simple("tool:\n  enabled: true\n  count: 3\n")
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
