"""Shared TOML and YAML parser loading with optional dependency fallback."""

from typing import Any


class ParserUnavailableError(RuntimeError):
    """Raised when a required parser dependency is not installed."""


_toml_module = None
_toml_checked = False


def _resolve_toml():
    global _toml_module, _toml_checked

    if _toml_checked:
        return _toml_module

    _toml_checked = True

    try:
        import tomllib  # type: ignore[import-not-found]

        _toml_module = tomllib
        return _toml_module
    except ImportError:
        pass

    try:
        import tomli

        _toml_module = tomli
        return _toml_module
    except ImportError:
        pass

    _toml_module = None
    return None


def has_toml_support() -> bool:
    return _resolve_toml() is not None


def load_toml(content: str) -> dict[str, Any]:
    """Parse a TOML document from a string."""
    mod = _resolve_toml()

    if mod is None:
        raise ParserUnavailableError(
            "TOML parser unavailable: install 'tomli' for Python 3.10 "
            "or use Python 3.11+ (stdlib tomllib)"
        )

    return mod.loads(content)


def load_toml_safe(content: str) -> dict[str, Any]:
    """Parse a TOML document, returning {} on any error."""
    try:
        data = load_toml(content)
        return data if isinstance(data, dict) else {}
    except (ParserUnavailableError, Exception):
        return {}


_yaml_module = None
_yaml_checked = False


def _resolve_yaml():
    global _yaml_module, _yaml_checked

    if _yaml_checked:
        return _yaml_module

    _yaml_checked = True

    try:
        import yaml

        _yaml_module = yaml
        return _yaml_module
    except ImportError:
        pass

    _yaml_module = None
    return None


def has_yaml_support() -> bool:
    return _resolve_yaml() is not None


def load_yaml(content: str) -> Any:
    """Parse a YAML document from a string using safe_load."""
    mod = _resolve_yaml()

    if mod is None:
        raise ParserUnavailableError("YAML parser unavailable: install 'PyYAML'")

    return mod.safe_load(content)
