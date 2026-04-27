"""Tests for scripts/lib/parsers.py — TOML/YAML loader availability and fallback."""

from lib.parsers import (
    ParserUnavailableError,
    has_toml_support,
    has_yaml_support,
    load_toml,
    load_yaml,
)


def test_toml_loads_simple_mapping():
    result = load_toml('[project]\nname = "agentskill"\n')
    assert isinstance(result, dict)
    assert result["project"]["name"] == "agentskill"


def test_toml_loads_nested_structure():
    toml = '[tool.ruff.lint]\nselect = ["E4", "F"]\nignore = ["E402"]\n'
    result = load_toml(toml)
    assert result["tool"]["ruff"]["lint"]["select"] == ["E4", "F"]


def test_toml_loads_scalar_types():
    toml = 'flag = true\ncount = 42\nratio = 3.14\nlabel = "hello"\n'
    result = load_toml(toml)
    assert result["flag"] is True
    assert result["count"] == 42
    assert isinstance(result["ratio"], float)
    assert result["label"] == "hello"


def test_toml_reports_support_available():
    assert has_toml_support() is True


def test_toml_raises_when_unavailable(monkeypatch):
    import builtins

    import lib.parsers as parsers_mod

    monkeypatch.setattr(parsers_mod, "_toml_module", None)
    monkeypatch.setattr(parsers_mod, "_toml_checked", False)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("tomllib", "tomli"):
            raise ImportError(name)

        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        load_toml("x = 1")
        raise AssertionError("should have raised ParserUnavailableError")
    except ParserUnavailableError as exc:
        assert "TOML parser unavailable" in str(exc)


def test_toml_reports_support_unavailable_when_missing(monkeypatch):
    import builtins

    import lib.parsers as parsers_mod

    monkeypatch.setattr(parsers_mod, "_toml_module", None)
    monkeypatch.setattr(parsers_mod, "_toml_checked", False)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("tomllib", "tomli"):
            raise ImportError(name)

        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert has_toml_support() is False


def test_yaml_loads_simple_mapping():
    result = load_yaml("name: agentskill\nversion: 0.4.0\n")
    assert isinstance(result, dict)
    assert result["name"] == "agentskill"


def test_yaml_loads_nested_mapping():
    yaml = "tool:\n  ruff:\n    line-length: 88\n"
    result = load_yaml(yaml)
    assert result["tool"]["ruff"]["line-length"] == 88


def test_yaml_loads_list_value():
    yaml = "select:\n  - E4\n  - F\n"
    result = load_yaml(yaml)
    assert result["select"] == ["E4", "F"]


def test_yaml_loads_scalar_types():
    yaml = "flag: true\ncount: 42\nratio: 3.14\nlabel: hello\n"
    result = load_yaml(yaml)
    assert result["flag"] is True
    assert result["count"] == 42
    assert isinstance(result["ratio"], float)
    assert result["label"] == "hello"


def test_yaml_reports_support_available():
    assert has_yaml_support() is True


def test_yaml_raises_when_unavailable(monkeypatch):
    import builtins

    import lib.parsers as parsers_mod

    monkeypatch.setattr(parsers_mod, "_yaml_module", None)
    monkeypatch.setattr(parsers_mod, "_yaml_checked", False)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError(name)

        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        load_yaml("x: 1")
        raise AssertionError("should have raised ParserUnavailableError")
    except ParserUnavailableError as exc:
        assert "YAML parser unavailable" in str(exc)


def test_yaml_reports_support_unavailable_when_missing(monkeypatch):
    import builtins

    import lib.parsers as parsers_mod

    monkeypatch.setattr(parsers_mod, "_yaml_module", None)
    monkeypatch.setattr(parsers_mod, "_yaml_checked", False)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError(name)

        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert has_yaml_support() is False
