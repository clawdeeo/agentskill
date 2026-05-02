# AGENTS.md

## 1. Overview

agentskill is a single-repo Python CLI published from the `agsk` package metadata and exposed as the `agentskill` console command. It analyzes one or more repositories, emits structured analyzer output, and also supports direct `AGENTS.md` generation and in-place update flows. The codebase is organized around packaged runtime modules under `agentskill/`, thin direct wrappers under `scripts/`, reference specs and fixture repositories at the repo root, and a separate `tests/` tree that exercises analyzer internals, generation/update flows, and CLI entrypoints.

## 2. Repository Structure

```text
agentskill/
  agentskill/
    main.py                 # packaged CLI entry point; argument parsing and dispatch only
    commands/               # analyzer implementations
    lib/                    # orchestration, output, reference, generation, and update helpers
    common/                 # shared low-level helpers and registries
  pyproject.toml            # packaging, pytest, ruff, coverage config
  README.md                 # user-facing overview and command reference
  SYSTEM.md                 # synthesis spec for generated AGENTS.md files
  SKILL.md                  # operational workflow for the skill
  AGENTS.md                 # conventions for this repo
  LICENSE                   # MIT license text
  references/
    GOTCHAS.md              # extraction and synthesis failure modes
  examples/
    python/                 # fixture repository used by analyzer tests
    javascript/             # fixture repository for JS/TS detection paths
    mixed/                  # multi-language fixture repository
    ...                     # additional per-language example repos
  scripts/
    scan.py                 # thin direct-execution wrapper
    measure.py              # thin direct-execution wrapper
    config.py               # thin direct-execution wrapper
    git.py                  # thin direct-execution wrapper
    graph.py                # thin direct-execution wrapper
    symbols.py              # thin direct-execution wrapper
    tests.py                # thin direct-execution wrapper
  tests/                    # pytest suite; separate tree, not colocated
    conftest.py             # sys.path test bootstrap
    test_support.py         # shared repo/setup helpers for tests
```

- New analyzer logic goes in `agentskill/commands/`, not in entrypoint wrappers.
- Shared CLI plumbing, generation, reference adaptation, and update flows belong in `agentskill/lib/`; low-level reusable helpers belong in `agentskill/common/`.
- Files under `scripts/*.py` stay as thin wrappers around `agentskill.commands.<name>.main`.
- New tests go in `tests/` as `test_<subject>.py`; this repo does not colocate tests beside source files.
- New fixture repos or language-shape examples belong in `examples/`, not mixed into `references/`.
- Specs and extraction notes belong in `README.md`, `SYSTEM.md`, `SKILL.md`, and `references/`, not inside runtime modules.
- Keep the repo root small: metadata, docs/spec files, and no business logic outside `agentskill/`.

## 5. Commands and Workflows

```bash
# Install editable package with dev tooling
python -m pip install -e '.[dev]'

# Optional local hooks
pre-commit install

# Run all analyzers
agentskill analyze <repo> --pretty

# Generate or update markdown
agentskill generate <repo>
agentskill generate <repo> --out AGENTS.md
agentskill generate <repo> --interactive
agentskill update <repo>
agentskill update <repo> --section testing
agentskill update <repo> --force

# Run individual analyzers through the installed CLI
agentskill scan <repo> --pretty
agentskill measure <repo> --lang python --pretty
agentskill config <repo> --pretty
agentskill git <repo> --pretty
agentskill graph <repo> --pretty
agentskill symbols <repo> --pretty
agentskill tests <repo> --pretty

# Direct wrapper execution
python scripts/scan.py <repo> --pretty

# Local checks
ruff format .
ruff check .
mypy
pytest
```

- `python -m pip install -e '.[dev]'` is the documented development install path; use it instead of reconstructing the dev dependency list manually.
- `agentskill analyze <repo> --pretty` is the canonical aggregate analyzer workflow.
- `agentskill generate <repo>` is the fresh-draft path; `agentskill update <repo>` is the in-place merge/preservation path.
- `agentskill <command> <repo> --pretty` is the main single-analyzer interface; `python scripts/<name>.py <repo> --pretty` remains supported as a thin direct wrapper.
- Use `ruff format .`, `ruff check .`, `mypy`, and `pytest` as the canonical local verification stack.

## 6. Code Formatting

### Python

Configured tooling: Ruff is configured in `pyproject.toml` for linting, and the repo documents `ruff format .` as the formatting command. No formatter-specific overrides are declared, so follow the observed formatting directly.

**Indentation:** 4 spaces.

```python
def _single_script_cmd(command_name: str, args: argparse.Namespace) -> int:
    metadata = COMMANDS[command_name]
    extra_kwargs = {}

    if metadata["supports_lang"]:
        extra_kwargs["lang_filter"] = getattr(args, "lang", None)
```

**Line length:** keep ordinary code in the mid-70s or below; measured p95 is 76. Long regex literals and long docstring summary lines still appear.

```python
CONVENTIONAL_PREFIX_RE = re.compile(r"^([a-z][a-z0-9_-]*)(\([^)]+\))?(!)?\s*:\s*(.+)$")
```

**Blank lines — top-level:** 2 blank lines between top-level functions and constants-to-functions transitions.

```python
from agentskill.lib.output import run_and_output, write_output
from agentskill.lib.runner import COMMANDS, run_many


def cmd_analyze(args: argparse.Namespace) -> int:
    result = run_many(args.repos, getattr(args, "lang", None))
```

**Blank lines — methods:** not applicable in the dominant code path; classes are effectively absent in source.

**Blank lines — class open:** not applicable in source for the same reason.

**Blank lines — after imports:** usually 1 blank line before module constants; 2 blank lines before the first function when a file goes straight from imports into functions.

```python
from agentskill.lib.output import run_and_output

GIT_TIMEOUT = 30
GIT_HASH_LENGTH = 40
```

```python
from test_support import create_sample_repo

from agentskill.main import main


def test_cli_scan_outputs_json(tmp_path, capsys):
```

**Blank lines — end of file:** every file ends with exactly 1 trailing newline.

**Trailing whitespace:** stripped.

**Brace / bracket placement:** opening delimiters stay on the same line; multiline calls and literals use hanging indentation with the closing delimiter on its own line.

```python
return run_and_output(
    metadata["fn"],
    repo=args.repo,
    pretty=args.pretty,
    out=getattr(args, "out", None),
    script_name=command_name,
    extra_kwargs=extra_kwargs,
)
```

**Quote style:** double quotes everywhere in normal Python code and docstrings.

```python
if not repo.exists():
    return {"error": f"path does not exist: {repo_path}", "script": "git"}
```

**Spacing — operators:** spaces around assignment and binary operators.

```python
avg_parents = sum(parent_counts) / len(parent_counts)
bucket = prefix if prefix else "unprefixed"
```

**Spacing — inside brackets:** no inner padding.

```python
if COMMANDS[command_name]["supports_lang"]:
```

**Spacing — after commas:** always a single space.

```python
return None, None, False
```

**Spacing — colons:** no space before `:`, one space after `:` in dict literals, none in type annotations.

```python
prefixes[k] = {
    "count": v["count"],
    "pct": round(v["count"] / total * 100, 1),
    "example": v["example"],
}
```

```python
def run_many(repos: list[str], lang_filter: str | None = None) -> dict:
```

**Spacing — decorators:** decorators are flush with the function they decorate, with no blank line between decorator and `def`.

```python
@pytest.fixture
def repo_fixture(tmp_path):
    return create_sample_repo(tmp_path)
```

**Import block formatting:** one import per line; groups are separated by a blank line. In source files, stdlib imports come first and local package imports follow. Tests usually import local helpers before packaged runtime modules.

```python
import json

from test_support import create_sample_repo

from agentskill.main import main
```

**Trailing commas:** used in multiline calls, dicts, lists, and imports.

```python
exit_code = main(
    ["analyze", str(repo_one), str(repo_two), "--out", str(out_file)]
)
```

**Line continuation:** implicit via open brackets; no backslash continuations.

**Semicolons:** absent.

## 7. Naming Conventions

### Python

**Functions and methods:** public entrypoints use plain snake_case names like `analyze`, `measure`, `build_graph`, `extract_symbols`; internal helpers use `_snake_case`.

```python
def analyze(repo_path: str) -> dict:
def build_graph(repo_path: str, lang_filter: str | None = None) -> dict:
def _detect_merge_strategy(cwd: str) -> tuple[str, str]:
```

**CLI command helpers:** root CLI helper names read as verbs or command phrases.

```python
def cmd_analyze(args: argparse.Namespace) -> int:
def _single_script_cmd(command_name: str, args: argparse.Namespace) -> int:
```

**Constants:** module constants use `SCREAMING_SNAKE_CASE`.

```python
GIT_TIMEOUT = 30
PRETTIER_CONFIG_FILES = [
MAKEFILE_NAMES = ["Makefile", "makefile", "GNUmakefile"]
```

**Private members:** internal helpers overwhelmingly use a single leading underscore; there is no meaningful double-underscore pattern.

```python
def _parse_toml_value(s: str):
def _measure_line_lengths(all_lengths: list[int]) -> dict:
def _command_kwargs(command_name: str, lang_filter: str | None) -> dict:
```

**File names:** source and helper files use lowercase snake_case; test files use `test_<subject>.py`; package markers use `__init__.py`.

```text
agentskill/lib/output.py
agentskill/common/constants.py
tests/test_measure.py
tests/test_support.py
```

**Directory names:** lowercase simple nouns: `agentskill`, `scripts`, `tests`, `references`, `examples`.

**Test function names:** `test_<behavior>` with long descriptive tails is the dominant pattern.

```python
def test_cli_writes_out_file_and_multi_repo_results(tmp_path):
def test_graph_detects_relative_imports_cycles_and_parse_errors(tmp_path):
```

**Fixture names:** when fixtures appear, they use snake_case nouns.

```python
def sample_fixture():
def repo_fixture(tmp_path):
```

## 8. Type Annotations

### Python

- Public functions are annotated on parameters and return types.
- Internal helpers are also usually annotated; this repo does not reserve annotations only for public APIs.
- Use built-in generics like `list[str]`, `dict[str, int]`, and union syntax like `str | None` instead of `List`, `Dict`, or `Optional`.
- Container-rich return types are accepted directly in signatures instead of being hidden behind aliases.
- `mypy` is configured in `pyproject.toml`; this repo does not rely on type annotations for linting alone.

```python
def main(argv: list[str] | None = None) -> int:
def _run(cmd: list[str], cwd: str) -> tuple[int, str]:
def run_many(repos: list[str], lang_filter: str | None = None) -> dict:
```

```python
def _analyze_branches(cwd: str) -> tuple[dict[str, int], int, list[str]]:
```

## 9. Imports

### Python

- Import order is not strict stdlib/third-party/local in the test suite; document and mimic the local file pattern instead of forcing generic ordering.
- In source files, stdlib imports come first, then local package imports separated by one blank line.
- In tests, import the packaged entrypoint from `agentskill.main` unless a compatibility path is being exercised explicitly.
- No wildcard imports.
- No `__future__` imports appear.

Canonical source import block:

```python
import re
import subprocess
import sys
from pathlib import Path

from agentskill.lib.output import run_and_output
```

Canonical test import block:

```python
import json

from test_support import create_sample_repo

from agentskill.main import main
```

## 10. Error Handling

### Python

- Low-level validators and normalization helpers raise `ValueError` with exact message text when the caller provides an invalid path or malformed feedback/config shape.
- User-facing analyzer functions catch those validation failures at the command boundary and return exact two-key payloads shaped as `{"error": ..., "script": ...}`.
- Shared CLI wrappers and aggregate runners catch broad exceptions, log or print diagnostics, and convert failures into a non-zero exit code or the same machine-readable error payload instead of letting tracebacks escape by default.
- Best-effort filesystem helpers degrade quietly for unreadable files by returning `""` or `0`; walker and parser-style helpers also skip individual failures when continuing the scan is more useful than aborting.
- Tests assert exact error strings and exact payload shape, not just exception type.

```python
def validate_repo(path: str) -> Path:
    repo = Path(path).resolve()

    if not repo.exists():
        raise ValueError(f"path does not exist: {path}")

    if not repo.is_dir():
        raise ValueError(f"not a directory: {path}")

    return repo
```

```python
def scan(repo_path: str, lang_filter: str | None = None) -> dict:
    try:
        repo = validate_repo(repo_path)
    except ValueError as exc:
        return {"error": str(exc), "script": "scan"}
```

```python
try:
    result = command_fn(repo, **kwargs)
except Exception as exc:
    logger.exception("Command %s failed for repo %s", script_name, repo)
    result = {"error": str(exc), "script": script_name}
```

```python
def read_text(path: Path, max_bytes: int | None = MAX_FILE_BYTES) -> str:
    try:
        with open(path, "rb") as file_obj:
            raw = file_obj.read() if max_bytes is None else file_obj.read(max_bytes)
    except Exception:
        return ""

    return raw.decode(errors="ignore")
```

```python
try:
    validate_feedback([])
    raise AssertionError("should have raised ValueError")
except ValueError as exc:
    assert str(exc) == "feedback must be an object"
```

## 11. Comments and Docstrings

### Python

- Modules almost always begin with a triple-double-quoted docstring.
- Function docstrings are short, declarative, and describe return shape or intent; many small helpers omit them.
- Inline comments are rare and only appear when a small detail would otherwise be unclear.
- Comments are not used for narration of obvious code.

```python
"""Aggregate analyzer execution for the top-level CLI."""
```

```python
def _detect_merge_strategy(cwd: str) -> tuple[str, str]:
    """Return (strategy, evidence)."""
```

```python
j = last_import  # 1-indexed -> 0-indexed
```

## 12. Testing

### Python

- Framework: `pytest`.
- Tests live in `tests/`, not beside source files.
- Test files are named `test_<subject>.py`.
- `tests/conftest.py` adds the repo root to `sys.path`; helper setup code is centralized in `tests/test_support.py`.
- Tests use plain `assert` statements and `tmp_path`, `capsys`, and `monkeypatch` fixtures heavily.
- The suite tests both pure functions and command-line entrypoints.

```python
def test_cli_scan_outputs_json(tmp_path, capsys):
    repo = create_sample_repo(tmp_path)
    exit_code = main(["scan", str(repo), "--pretty"])

    assert exit_code == 0

    output = json.loads(capsys.readouterr().out)
    assert output["summary"]["total_files"] >= 4
```

```python
def test_detect_merge_strategy_paths(monkeypatch):
    monkeypatch.setattr(git_command, "_run", lambda cmd, cwd: (1, ""))
    assert _detect_merge_strategy("repo") == ("unknown", "insufficient data")
```

```python
def write(repo: Path, rel_path: str, content: str) -> Path:
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
```

## 13. Git

- Commit subjects follow conventional-commit-style prefixes. Dominant prefixes in current history are `feat:`, `refactor:`, `docs:`, `release:`, `fix:`, `chore:`, and smaller amounts of `ci:`, `test:`, `style:`, `deps:`, and `build:`.
- Branch names use a slash-separated prefix pattern when they are not trunk branches.
- The current analyzer output detects merge commits rather than a pure rebase-only history, so do not write process notes that assume a strictly linear workflow.
- Commit bodies exist, but not on every commit.

Examples from current history:

```text
feat: release version 1.0.0 with updated build workflow and CLI command name
refactor: update project structure moving to an idiomatic one
docs: add comprehensive API and CLI documentation with reference examples
fix: update tag validation in release workflow to use regex for version extraction
```

Branch example:

```text
docs/changelog-0.2.0
```

## 14. Dependencies and Tooling

- Packaging uses `setuptools.build_meta` with `setuptools>=68` in `build-system.requires`.
- The published console script is `agentskill = "agentskill.main:main"`.
- The distribution package name is `agsk`.
- Runtime requirement is Python `>=3.10`.
- Runtime dependencies include `tomli` and `PyYAML` for Python `<3.11`.
- Dev dependencies include `mypy`, `pre-commit`, `pytest`, `pytest-cov`, `ruff`, `tomli`, `PyYAML`, and `types-PyYAML`.
- Ruff targets `py39`, excludes cache and virtualenv directories, and lint rules are configured in `pyproject.toml` with `select = ["B", "C4", "E4", "E7", "E9", "F", "I", "N", "SIM", "UP", "W"]` and `ignore = ["E402"]`.
- `mypy` is configured in `pyproject.toml` for `agentskill`, `scripts`, and `tests` with `check_untyped_defs = true`, `warn_unused_ignores = true`, `warn_redundant_casts = true`, `warn_unreachable = true`, and `show_error_codes = true`.
- Coverage omits `tests/*`.
- License is MIT.

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "agsk"
version = "1.0.0"
requires-python = ">=3.10"

[project.scripts]
agentskill = "agentskill.main:main"
```

```toml
[tool.ruff]
target-version = "py39"

[tool.ruff.lint]
select = ["B", "C4", "E4", "E7", "E9", "F", "I", "N", "SIM", "UP", "W"]
ignore = ["E402"]
```

## 15. Red Lines

- Do not put analyzer implementation logic into `agentskill/main.py`; keep it as dispatch and orchestration only.
- Do not add colocated tests under `scripts/`; tests belong under `tests/`.
- Do not introduce `Optional[...]`, `List[...]`, or `Dict[...]` annotation style; the repo uses built-in generics and `| None`.
- Do not switch quote style to single quotes in ordinary Python code.
- Do not start using wildcard imports or `__future__` imports without a repo-wide reason.
- Do not rely on exceptions escaping CLI/output wrappers when the existing pattern returns `{"error": ..., "script": ...}` payloads.
- Do not fold example fixture repos into `references/` or analyzer code; keep repo-shaped fixtures in `examples/`.
- Do not bypass `agentskill/lib/` by adding generation or update orchestration directly to wrappers under `scripts/`.
- Do not assume `python -m agentskill.main` is a supported operator path; the supported surfaces are the installed `agentskill` console script, direct wrapper scripts, and direct `main([...])` invocation in tests.
