"""Central language registry and detection helpers for all analyzers."""

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path


@dataclass(frozen=True)
class LanguageSpec:
    id: str
    display_name: str
    extensions: tuple[str, ...]
    config_files: tuple[str, ...] = ()
    package_files: tuple[str, ...] = ()
    test_patterns: tuple[str, ...] = ()
    source_roots: tuple[str, ...] = ()


_PYTHON = LanguageSpec(
    id="python",
    display_name="Python",
    extensions=(".py",),
    config_files=(
        "pyproject.toml",
        "setup.cfg",
        ".flake8",
        ".isort.cfg",
        "ruff.toml",
        ".ruff.toml",
    ),
    package_files=("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"),
    test_patterns=("test_*.py", "*_test.py", "tests/**/*.py"),
    source_roots=("src",),
)

_TYPESCRIPT = LanguageSpec(
    id="typescript",
    display_name="TypeScript",
    extensions=(".ts", ".tsx"),
    config_files=("tsconfig.json", "tsconfig.*.json"),
    package_files=("package.json",),
    test_patterns=(
        "*.test.ts",
        "*.spec.ts",
        "*.test.tsx",
        "*.spec.tsx",
        "__tests__/**/*",
    ),
    source_roots=("src",),
)

_JAVASCRIPT = LanguageSpec(
    id="javascript",
    display_name="JavaScript",
    extensions=(".js", ".jsx", ".mjs", ".cjs"),
    config_files=("jsconfig.json",),
    package_files=("package.json",),
    test_patterns=(
        "*.test.js",
        "*.spec.js",
        "__tests__/**/*",
    ),
    source_roots=("src",),
)

_GO = LanguageSpec(
    id="go",
    display_name="Go",
    extensions=(".go",),
    config_files=("go.mod",),
    package_files=("go.mod", "go.work"),
    test_patterns=("*_test.go",),
    source_roots=(),
)

_RUST = LanguageSpec(
    id="rust",
    display_name="Rust",
    extensions=(".rs",),
    config_files=("rustfmt.toml", ".rustfmt.toml", "clippy.toml"),
    package_files=("Cargo.toml",),
    test_patterns=("tests/**/*.rs", "*_test.rs"),
    source_roots=("src",),
)

_JAVA = LanguageSpec(
    id="java",
    display_name="Java",
    extensions=(".java",),
    config_files=(),
    package_files=("pom.xml", "build.gradle", "build.gradle.kts"),
    test_patterns=("*Test.java", "src/test/java/**/*.java"),
    source_roots=("src/main/java",),
)

_KOTLIN = LanguageSpec(
    id="kotlin",
    display_name="Kotlin",
    extensions=(".kt", ".kts"),
    config_files=(),
    package_files=(
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
    ),
    test_patterns=("*Test.kt", "src/test/kotlin/**/*.kt"),
    source_roots=("src/main/kotlin",),
)

_CSHARP = LanguageSpec(
    id="csharp",
    display_name="C#",
    extensions=(".cs",),
    config_files=(),
    package_files=(".csproj", ".sln"),
    test_patterns=("*Tests.cs", "*.Tests/**/*.cs"),
    source_roots=("src",),
)

_C = LanguageSpec(
    id="c",
    display_name="C",
    extensions=(".c", ".h"),
    config_files=(),
    package_files=("CMakeLists.txt", "Makefile"),
    test_patterns=("*_test.c", "tests/**/*"),
    source_roots=("src",),
)

_CPP = LanguageSpec(
    id="cpp",
    display_name="C++",
    extensions=(".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"),
    config_files=(),
    package_files=("CMakeLists.txt", "Makefile"),
    test_patterns=("*_test.cpp", "tests/**/*"),
    source_roots=("src",),
)

_RUBY = LanguageSpec(
    id="ruby",
    display_name="Ruby",
    extensions=(".rb",),
    config_files=(".rubocop.yml",),
    package_files=("Gemfile",),
    test_patterns=("*_spec.rb", "spec/**/*.rb", "test/**/*.rb"),
    source_roots=("lib",),
)

_PHP = LanguageSpec(
    id="php",
    display_name="PHP",
    extensions=(".php",),
    config_files=("phpcs.xml", ".phpcs.xml"),
    package_files=("composer.json",),
    test_patterns=("*Test.php", "tests/**/*.php"),
    source_roots=("src",),
)

_SWIFT = LanguageSpec(
    id="swift",
    display_name="Swift",
    extensions=(".swift",),
    config_files=(),
    package_files=("Package.swift", "Podfile", ".xcodeproj", ".xcworkspace"),
    test_patterns=("*Tests.swift", "Tests/**/*.swift"),
    source_roots=("Sources",),
)

_OBJECTIVEC = LanguageSpec(
    id="objectivec",
    display_name="Objective-C",
    extensions=(".m", ".mm"),
    config_files=(),
    package_files=("Podfile", ".xcodeproj", ".xcworkspace"),
    test_patterns=("*Tests.m", "*Tests.mm"),
    source_roots=(),
)

_BASH = LanguageSpec(
    id="bash",
    display_name="Bash",
    extensions=(".sh", ".bash"),
    config_files=(),
    package_files=(),
    test_patterns=("test_*.sh", "*_test.sh", "*.bats"),
    source_roots=(),
)


_LANGUAGES: tuple[LanguageSpec, ...] = (
    _PYTHON,
    _TYPESCRIPT,
    _JAVASCRIPT,
    _GO,
    _RUST,
    _JAVA,
    _KOTLIN,
    _CSHARP,
    _C,
    _CPP,
    _RUBY,
    _PHP,
    _SWIFT,
    _OBJECTIVEC,
    _BASH,
)


def _build_registry() -> tuple[
    dict[str, LanguageSpec],
    dict[str, LanguageSpec],
]:
    by_id: dict[str, LanguageSpec] = {}
    by_ext: dict[str, LanguageSpec] = {}

    for spec in _LANGUAGES:
        by_id[spec.id] = spec

        for ext in spec.extensions:
            normalized = ext.lower()

            if normalized in by_ext:
                raise ValueError(
                    f"Duplicate extension {normalized!r} in "
                    f"{spec.id!r} and {by_ext[normalized].id!r}"
                )

            by_ext[normalized] = spec

    return by_id, by_ext


_BY_ID, _BY_EXT = _build_registry()


def all_language_specs() -> tuple[LanguageSpec, ...]:
    """Return all registered language specs in deterministic order."""
    return _LANGUAGES


def language_by_id(language_id: str) -> LanguageSpec | None:
    """Look up a language spec by its stable ID."""
    return _BY_ID.get(language_id)


def language_for_extension(extension: str) -> LanguageSpec | None:
    """Look up a language spec by file extension.

    Accepts forms with or without a leading dot (e.g. '.py' or 'py').
    """
    normalized = extension.lower()

    if not normalized.startswith("."):
        normalized = "." + normalized

    return _BY_EXT.get(normalized)


def language_for_path(path: str | Path) -> LanguageSpec | None:
    """Look up a language spec by a file path's suffix."""
    return language_for_extension(Path(path).suffix)


def is_supported_language(language_id: str) -> bool:
    """Return True if the given language ID is registered."""
    return language_id in _BY_ID


def is_test_path(path: str | Path, language_id: str | None = None) -> bool:
    """Return True if the path matches a known test pattern.

    When language_id is provided, only that language's patterns are checked.
    Otherwise, all registered patterns are tested.
    """
    p = Path(path)
    name = p.name
    rel = str(p)

    specs: tuple[LanguageSpec, ...]

    if language_id is not None:
        if language_id in _BY_ID:
            specs = (_BY_ID[language_id],)
        else:
            return False
    else:
        specs = _LANGUAGES

    for spec in specs:
        for pattern in spec.test_patterns:
            if fnmatch(name, pattern) or fnmatch(rel, pattern):
                return True

    return False
