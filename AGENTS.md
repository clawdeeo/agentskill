# AGENTS.md

## 1. Overview

agentskill is a Python repository that analyzes source code repositories and synthesizes `AGENTS.md` files. It operates as a command-line tool: a top-level `cli.py` dispatches to seven analysis scripts under `scripts/`, each of which walks a target repo, extracts a specific class of signals (file tree, formatting metrics, config files, git history, import graph, symbol names, test structure), and emits JSON to stdout. The scripts are also importable as modules; `cli.py` runs all seven in parallel via `ThreadPoolExecutor`. There are no classes anywhere in the codebase — all logic lives in module-level functions.

---

## 2. Repository Structure

```
cli.py              # unified entry point — subcommand dispatch only, no business logic
pyproject.toml      # build metadata and entry point declaration
SYSTEM.md           # canonical spec for AGENTS.md generation — never modify
SKILL.md            # operational workflow — never modify
AGENTS.md           # this file
scripts/
  scan.py           # directory tree walk, file inventory, read order
  measure.py        # indentation, line lengths, blank lines, trailing whitespace
  config.py         # formatter/linter/type-checker detection from config files
  git.py            # commit log parsing, branch analysis, merge strategy
  graph.py          # internal import graph, cycle detection, monorepo detection
  symbols.py        # symbol name extraction and naming pattern clustering
  tests.py          # test-to-source mapping, framework detection, fixture extraction
references/
  GOTCHAS.md        # synthesis failure modes — read before writing AGENTS.md
examples/           # placeholder for example outputs
```

- New analysis scripts go in `scripts/`. They must be importable as modules (expose a named function, not just a `main()`).
- `cli.py` lives at the repo root. It must not contain analysis logic — only argument parsing and dispatch.
- No new top-level Python packages. There is no `src/` layout; `cli.py` adds `scripts/` to `sys.path` directly.
- Nothing other than `cli.py`, `pyproject.toml`, `SYSTEM.md`, `SKILL.md`, `AGENTS.md`, and config files belongs at the repo root.
- Scripts must not import each other. Each script is independent.

---

## 5. Commands and Workflows

```
# Install
pip install -e .

# Run all scripts against a repo
python cli.py analyze <repo> --pretty

# Run individual scripts
python cli.py scan <repo> --pretty
python cli.py measure <repo> --lang python --pretty
python cli.py config <repo> --pretty
python cli.py git <repo> --pretty
python cli.py graph <repo> --pretty
python cli.py symbols <repo> --pretty
python cli.py tests <repo> --pretty

# Write output to file
python cli.py analyze <repo> --out report.json

# Run a script directly
python scripts/scan.py <repo> --pretty
```

There is no test suite, linter config, or formatter config in the repository.

---

## 6. Code Formatting

No formatter is configured. All style below is author convention measured directly from source.

### Python

**Indentation:** 4 spaces. Never tabs.

```python
def _measure_lang(lang: str, files: list[Path]) -> dict:
    all_line_lengths: list[int] = []
    indent_votes: list[dict] = []
    trailing_newline_present = 0
```

**Line length:** Keep lines under 88 characters in practice; the 95th percentile across all files is 77. Long lines are acceptable only for regex patterns and string literals. Do not wrap for wrapping's sake.

**Blank lines — top-level:** Two blank lines between every top-level function definition.

```python
def _measure_indentation(lines: list[str]) -> dict:
    ...


def _measure_line_lengths(all_line_lengths: list[int]) -> dict:
    ...
```

**Blank lines — after imports:** One blank line between the last import and the first definition.

```python
from statistics import median

SKIP_DIRS: set[str] = {
```

**Blank lines — methods:** Not applicable — no classes exist in this codebase.

**Blank lines — class open:** Not applicable.

**Blank lines — end of file:** Every file ends with exactly one trailing newline.

**Trailing whitespace:** Never present. All lines are clean.

**Quote style:** Double quotes for all string literals, including dict keys and f-strings.

```python
return {"error": f"path does not exist: {repo_path}", "script": "scan"}
```

**Spacing — operators:** Space on both sides of `=` in assignments and keyword arguments. Space on both sides of `:` in type annotations. Space after `:` in dict literals.

```python
result: dict = {}
indent = 2 if pretty else None
by_lang: dict[str, list[Path]] = {}
```

**Spacing — inside brackets:** No spaces inside parentheses, brackets, or braces.

```python
edges.append({"from": mod, "to": resolved, "line": node.lineno})
```

**Spacing — after commas:** One space after every comma.

```python
def _percentile(sorted_data: list[int], p: int) -> int:
```

**Brace/bracket placement — multi-line dicts and sets:** Opening brace on the same line as the assignment; each item on its own indented line; closing brace on its own line.

```python
SKIP_DIRS: set[str] = {
    "node_modules", "__pycache__", "dist", "build", "out",
    "target", "vendor", "third_party", ".eggs", "site-packages",
    "venv", ".venv", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "htmlcov", ".next", ".nuxt", "coverage",
}
```

**Trailing commas:** Present on the last item of every multi-line collection literal.

```python
EXTENSIONS: dict[str, str] = {
    ".py":   "python",
    ".ts":   "typescript",
    ...
    ".cs":   "csharp",
}
```

**Column alignment inside dicts:** Values in dict literals are column-aligned when the keys are short and the dict is a static constant.

```python
EXTENSIONS: dict[str, str] = {
    ".py":   "python",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".js":   "javascript",
}
```

**Line continuation:** Use implicit continuation via open brackets. Never use backslash continuation.

```python
most_depended = sorted(
    [{"module": m, "dependents": c} for m, c in dep_counts.items()],
    key=lambda x: -x["dependents"],
)[:10]
```

**Import block formatting:** stdlib imports only — no third-party dependencies. Imports are grouped in a single block with no blank lines between individual imports. Sorted loosely by module name. One import per line.

```python
import ast
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median
```

---

## 7. Naming Conventions

### Python

**Functions:** `snake_case`. Public functions are named after their action and primary noun: `scan`, `measure`, `build_graph`, `extract_symbols`, `analyze_tests`, `detect`. Internal helpers are prefixed with a single underscore.

```python
def _collect_files(repo: Path, lang_filter: str | None) -> dict[str, list[Path]]:
def _measure_indentation(lines: list[str]) -> dict:
def _should_skip_dir(name: str) -> bool:
```

**Public entry-point functions:** One per script, named after the script's primary action. This is what `cli.py` imports and calls.

```python
def scan(repo_path: str, lang_filter: str | None = None) -> dict:
def measure(repo_path: str, lang_filter: str | None = None) -> dict:
def build_graph(repo_path: str, lang_filter: str | None = None) -> dict:
```

**Variables:** `snake_case`. Local loop variables and temporaries use short descriptive names (`fp`, `fn`, `rel`, `mod`, `dep`). Accumulator lists use the plural of their element type: `edges`, `cycles`, `files`, `depths`.

**Constants:** `SCREAMING_SNAKE_CASE` for module-level constants.

```python
SKIP_DIRS: set[str] = { ... }
EXTENSIONS: dict[str, str] = { ... }
ENTRY_POINT_NAMES: set[str] = { ... }
```

**Private helpers:** Single leading underscore. Used for all functions not called from outside the module.

**File names:** `snake_case`, no hyphens. Script names are single nouns matching their purpose: `scan.py`, `measure.py`, `config.py`, `git.py`, `graph.py`, `symbols.py`, `tests.py`.

**No classes:** Do not introduce classes. All state is passed as arguments or accumulated into local dicts.

---

## 8. Type Annotations

### Python

- Annotate every function signature — both parameters and return type.
- Use built-in generic syntax (`list[str]`, `dict[str, int]`, `set[str]`, `tuple[list, list]`) not `typing` module generics. The `typing` module is never imported anywhere in this codebase.
- Use `X | None` for optional types, never `Optional[X]`.
- Use `X | None = None` for optional parameters with default.

```python
def _collect_files(repo: Path, lang_filter: str | None) -> dict[str, list[Path]]:
def _single_script_cmd(fn, args: argparse.Namespace, extra_kwargs: dict | None = None) -> int:
def main(argv: list[str] | None = None) -> int:
```

- Annotate module-level constants with their full type.

```python
SKIP_DIRS: set[str] = { ... }
TOP_LEVEL_DEF_RE: dict[str, re.Pattern] = { ... }
```

- Annotate local variables when the type is non-obvious, especially empty collections.

```python
result: dict = {}
edges: list[dict] = []
adjacency: dict[str, list[str]] = {}
```

- No type checker is configured. Annotations are documentation, not enforced.

---

## 9. Imports

### Python

- stdlib only. No third-party imports anywhere in the codebase. Do not add third-party dependencies.
- Group: stdlib `import` statements first, then `from` imports. No blank lines between imports within the block. One blank line after the last import before the first definition or constant.
- Sort alphabetically within the block (loosely — `from` imports after bare `import` statements).
- Never use `import *`.
- No `__future__` imports.
- `argparse` is imported inside `main()` in standalone scripts, not at the module top level.

Canonical example from `scripts/measure.py`:

```python
import ast
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median
```

`cli.py` adds `scripts/` to `sys.path` and imports scripts as bare module names with private aliases:

```python
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "scripts"))

import scan as _scan
import measure as _measure
import config as _config
import git as _git
import graph as _graph
import symbols as _symbols
import tests as _tests
```

---

## 10. Error Handling

### Python

- Every public entry-point function (`scan`, `measure`, `detect`, etc.) catches all exceptions at the top level and returns `{"error": str(exc)}` — never raises to the caller.

```python
def scan(repo_path: str, lang_filter: str | None = None) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "scan"}
```

- Internal helper functions use bare `except Exception` to swallow errors on a per-file basis, continuing to the next file. They never log — they either silently skip or append to an error list.

```python
for fp in files:
    try:
        source = fp.read_text(errors="ignore")
        tree = ast.parse(source)
    except Exception:
        continue
```

- Parse errors on individual files are collected into a `parse_errors: list[str]` list and returned in the result dict, not raised.

```python
    except Exception:
        parse_errors.append(str(fpath.relative_to(repo)))
        continue
```

- `cli.py` wraps every script call in `try/except Exception` and stores `{"error": str(exc)}` under the script's key — the overall `analyze` command always succeeds.

```python
try:
    result[name] = future.result()
except Exception as exc:
    result[name] = {"error": str(exc)}
```

- Never use bare `except:` (without `Exception`).
- Never raise custom exceptions. There are no custom exception classes in this codebase.

---

## 11. Comments and Docstrings

### Python

**Module docstrings:** Every script file has a module-level docstring. It describes what the script does in one sentence, lists what it outputs, and shows the exact usage invocations.

```python
#!/usr/bin/env python3
"""Walk the repository directory tree. Produce an annotated file inventory.

Outputs:
  - tree: flat list of all source files with metadata
  - summary: per-language file/line counts
  - read_order: suggested reading order (entry points first, then by size)

Usage:
    python scripts/scan.py <repo>
    python scripts/scan.py <repo> --lang python
    python scripts/scan.py <repo> --pretty
"""
```

**Function docstrings:** Used only on functions where the behavior is non-obvious — specifically internal helpers with a non-trivial algorithm. One-line docstrings only; no multi-line Google/NumPy format.

```python
def _find_cycles(adjacency: dict[str, list[str]]) -> list[list[str]]:
    """DFS cycle detection. Returns list of cycles as ordered node lists."""
```

**Public entry-point functions:** No docstring. The module docstring covers the script's purpose.

**Inline comments:** Used sparingly for non-obvious logic. Two spaces before `#`, one space after.

```python
# Normalize to existing module
resolved = target if target in module_set else next(
    (m for m in module_set if target.startswith(m)), target
)
```

```python
# Cap for large repos
"edges": edges[:200],
```

**Never:** commented-out code, redundant comments restating what the code does, TODO comments left in committed code.

---

## 12. Testing

No test suite exists in this repository. Do not add one unless explicitly requested. When tests are added:

- Use `pytest` as the framework.
- Place test files in a top-level `tests/` directory mirroring the structure of `scripts/`.
- Name test files `test_<module>.py` (e.g. `test_scan.py`).
- Name test functions `test_<function>_<scenario>`.
- No `conftest.py` exists; do not create one unless fixtures are genuinely shared.

---

## 13. Git

> **Repo-wide:**

**Commit prefixes — use exactly one per commit:**

- `feat:` — adds new user-visible capability
- `fix:` — corrects a bug in existing behavior
- `refactor:` — restructures code without changing behavior
- `docs:` — changes to documentation files only
- `chore:` — maintenance tasks (dependency bumps, file deletions, tooling config)
- `test:` — adds or modifies tests only

**Scopes:** Not used. Never write `feat(scripts):` — write `feat:`.

**Subject line:** Imperative mood, no period at end. Keep under 72 characters. The 95th percentile in this repo is 75 characters.

```
feat: add git.py commit log analysis script
fix: resolve all 8 accuracy bugs from self-analysis
refactor: code clean up
```

**Body:** Optional. Used on roughly one in four commits. When present, separated from subject by a blank line.

**Branch naming:** Use `<prefix>/<short-description>` with hyphens. Observed prefix: `chore/`.

```
chore/strip-comments
```

**Merge strategy:** Rebase. No merge commits. History is linear.

**GPG signing:** Not required. Do not sign commits.

---

## 14. Dependencies and Tooling

### Python

- **Package manager:** pip with `pyproject.toml`. No `requirements.txt`, no `setup.py`.
- **Install:** `pip install -e .`
- **Add a dependency:** Add to `[project.dependencies]` in `pyproject.toml`. Do not add third-party dependencies — this repo uses Python stdlib only.
- **Lockfile:** None. Do not create one.
- **Linter:** None configured.
- **Formatter:** None configured.
- **Type checker:** None configured.
- **Minimum Python:** 3.9 (declared in `pyproject.toml`). Use `str | None` union syntax and built-in generics freely — these require 3.10+ syntax but the codebase already uses them everywhere.

---

## 15. Red Lines

**Formatting violations:**

- Never use single quotes for string literals in Python. All strings use double quotes.
- Never place two or more top-level function definitions with only one blank line between them. Two blank lines are always required.
- Never use a backslash for line continuation. Always use implicit continuation via open brackets.
- Never indent with tabs. All indentation is 4 spaces.

**Architectural violations:**

- Never put analysis logic in `cli.py`. It contains only argument parsing and dispatch.
- Never import one script from another. Each script in `scripts/` is independent. Shared logic must be duplicated or extracted to a new shared module — not by creating a dependency between scripts.
- Never create a Python package (directory with `__init__.py`) inside `scripts/`. Scripts are standalone modules loaded via `sys.path`.
- Never add a third-party dependency. The entire codebase runs on Python stdlib.

**Style violations:**

- Never introduce a class. All logic is module-level functions. No `class Foo:` anywhere.
- Never import from `typing`. Use built-in generics (`list[str]`, `dict[str, int]`, `X | None`) directly.
- Never write a function without type annotations on both its parameters and its return type.
- Never use `Optional[X]` — use `X | None`.

**Testing violations:**

- Never import from a script using a relative import (`from .scan import ...`). Scripts must be imported as top-level modules after `sys.path` manipulation.
- Never write a test that depends on a live filesystem path outside the repo. Use `tmp_path` or in-memory data.

**Git violations:**

- Never commit without a conventional prefix (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`). Unprefixed commit messages are not acceptable.
- Never use a scope in a commit prefix (e.g. `feat(scripts):`). This repo does not use scopes.
- Never commit commented-out code.
