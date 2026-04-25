"""Constants for style detection and analysis."""

SAMPLE_SIZE_SMALL = 30
SAMPLE_SIZE_MEDIUM = 50
COMMIT_LOG_LIMIT = 100
TOP_COMMIT_PREFIXES = 5
TOP_BRANCH_PREFIXES = 10

GIT_TIMEOUT = 30
JSON_INDENT = 2

HIDDEN_PREFIX = "."
GIT_DIR = ".git"
REMOTE_PREFIX = "remotes/origin/"

LOCKFILES = {
    "Cargo.lock": "cargo",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
    "go.sum": "go",
    "Gemfile.lock": "bundler",
    "composer.lock": "composer",
    "mix.lock": "mix",
    "flake.lock": "nix",
}

EXTENSIONS = {
    "rust": [".rs"],
    "python": [".py"],
    "javascript": [".js", ".mjs"],
    "typescript": [".ts", ".tsx"],
    "go": [".go"],
    "bash": [".sh"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".hpp", ".cc"],
    "java": [".java"],
    "csharp": [".cs"],
    "ruby": [".rb"],
    "php": [".php"],
    "swift": [".swift"],
    "kotlin": [".kt"],
    "scala": [".scala"],
    "zig": [".zig"],
    "nim": [".nim"],
    "haskell": [".hs"],
    "ocaml": [".ml", ".mli"],
    "elixir": [".ex", ".exs"],
    "clojure": [".clj", ".cljs"],
    "lua": [".lua"],
    "perl": [".pl", ".pm"],
    "r": [".r", ".R"],
    "julia": [".jl"],
    "dart": [".dart"],
    "groovy": [".groovy"],
    "fsharp": [".fs", ".fsx"],
    "crystal": [".cr"],
    "d": [".d"],
}

TOOL_FILES = {
    "rustfmt.toml": "rustfmt",
    ".rustfmt.toml": "rustfmt",
    "Cargo.toml": "cargo",
    ".github/workflows": "GitHub Actions",
    ".gitignore": "git",
    "Makefile": "make",
    "justfile": "just",
    ".pre-commit-config.yaml": "pre-commit",
    "pyproject.toml": "poetry/flit",
    "setup.py": "setuptools",
    "requirements.txt": "pip",
    "package.json": "npm/yarn",
    "tsconfig.json": "typescript",
    "go.mod": "go modules",
    "Dockerfile": "docker",
    "docker-compose.yml": "docker-compose",
    ".env.example": "dotenv",
    "LICENSE": "license",
    "README.md": "readme",
    "CONTRIBUTING.md": "contributing",
    ".editorconfig": "editorconfig",
    ".gitattributes": "gitattributes",
}

SKIP_DIRS = {
    'node_modules', 'target', '__pycache__', '.git', '.hg', '.svn',
    'vendor', 'third_party', 'third-party', 'dist', 'build', 'out',
    '.tox', '.nox', '.venv', 'venv', '.eggs', '*.egg-info',
    '.pytest_cache', '.mypy_cache', '.ruff_cache', '.coverage',
    'htmlcov', 'site-packages', 'wheelhouse',
}

PYTHON_VAR_KEYWORDS = {'self', 'cls', 'if', 'for', 'while', 'def', 'class', 'return', 'import', 'from', 'as'}

RUST_COMMENT_STYLES = {'///', '//!', '//', '/*'}
PYTHON_COMMENT_STYLE = '#'

RUST_ERROR_PATTERNS = ["unwrap()", "expect(", "?", "panic!", "Result<"]
RUST_ERROR_KEYS = ["unwrap", "expect", "?", "panic", "Result"]

CASE_SCREAMING_SNAKE = "SCREAMING_SNAKE_CASE"
CASE_SNAKE = "snake_case"
CASE_KEBAB = "kebab-case"
CASE_CAMEL = "camelCase"
CASE_PASCAL = "PascalCase"
CASE_MIXED = "mixed"

LANG_RUST = "rust"
LANG_PYTHON = "python"
LANG_JS = "javascript"
LANG_TS = "typescript"
LANG_GO = "go"

NAME_VAR = "vars"
NAME_FUNCTION = "functions"
NAME_TYPE = "types"
NAME_CONST = "consts"
