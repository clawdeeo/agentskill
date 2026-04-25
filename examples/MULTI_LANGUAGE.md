# AGENTS.md

> **Example: multi-language single repo.**
> Fictional Python/TypeScript project — `lumen`, a documentation site generator with a Python build engine and a TypeScript browser runtime. All data is fabricated for illustration.
> The structure and level of detail here represent the target quality for any multi-language single-repo output.

---

## 1. Overview

lumen is a documentation site generator: a Python package that parses Markdown and structured YAML into an intermediate representation, then serializes it to static HTML; and a TypeScript browser runtime that adds client-side search, syntax highlighting, and navigation to the generated output. The two halves share no code at runtime — the Python engine runs at build time, the TypeScript bundle is embedded in generated pages. Both halves live in one repository and are developed together. The codebase favors explicit data flow over magic: no monkey-patching, no global mutation, no hidden imports.

---

## 2. Repository Structure

```
lumen/
  pyproject.toml          # Python package metadata and tool config
  package.json            # TypeScript package metadata
  tsconfig.json
  Makefile
  lumen/                  # Python package
    __init__.py
    cli.py                # entry point — argparse dispatch only
    builder.py            # orchestrates the full build pipeline
    parser.py             # Markdown and YAML → IR
    renderer.py           # IR → HTML
    assets.py             # static file bundling and hashing
    config.py             # config file loading and validation
    errors.py             # all custom exception classes
    models.py             # dataclasses for the IR
    util.py               # shared utilities — string, path, hash helpers
  runtime/                # TypeScript browser runtime
    src/
      index.ts            # entry point — exports the public API
      search.ts           # client-side search index and query engine
      highlight.ts        # syntax highlighting integration
      nav.ts              # navigation and scroll-spy
      types.ts            # shared TypeScript interfaces and type aliases
      util.ts             # shared utilities
    tests/
      search.test.ts
      nav.test.ts
    tsconfig.json         # runtime-specific TS config (stricter than root)
  tests/                  # Python test suite
    conftest.py
    test_parser.py
    test_renderer.py
    test_builder.py
```

- New Python modules go in `lumen/`. No sub-packages.
- New TypeScript modules go in `runtime/src/`.
- Custom exception classes go in `lumen/errors.py` only. Do not define exceptions inline.
- Shared TypeScript types go in `runtime/src/types.ts`. Do not duplicate type definitions across files.
- `lumen/cli.py` contains only argument parsing and dispatch — no build logic.
- Nothing other than config files, `Makefile`, `pyproject.toml`, and `package.json` belongs at the repo root.

---

## 5. Commands and Workflows

```bash
# Install Python package (dev mode)
pip install -e ".[dev]"

# Install TypeScript dependencies
npm install

# Run Python tests
pytest

# Run TypeScript tests
npm test

# Build the TypeScript bundle
npm run build

# Build documentation site (full pipeline)
lumen build ./docs --out ./site

# Lint Python
ruff check lumen/ tests/

# Format Python
ruff format lumen/ tests/

# Lint TypeScript
npm run lint

# Format TypeScript
npm run format
```

---

## 6. Code Formatting

### Python

Formatted by `ruff format`. Config in `pyproject.toml` under `[tool.ruff.format]`.

**Indentation:** 4 spaces. Never tabs.

```python
def render(node: PageNode, ctx: RenderContext) -> str:
    parts: list[str] = []
    for child in node.children:
        parts.append(_render_node(child, ctx))
    return "".join(parts)
```

**Line length:** 88 characters. Configured as `line-length = 88` in `[tool.ruff]`. The 95th percentile across source files is 81.

**Blank lines — top-level:** Two blank lines between every top-level function and class definition.

```python
def parse_frontmatter(source: str) -> dict[str, str]:
    ...


def parse_body(source: str) -> list[BlockNode]:
    ...
```

**Blank lines — methods:** One blank line between methods inside a class.

```python
class Renderer:
    def render_page(self, page: PageNode) -> str:
        ...

    def render_block(self, block: BlockNode) -> str:
        ...
```

**Blank lines — class open:** No blank line between the class declaration and the first method.

```python
class BuildError(LumenError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
```

**Blank lines — after imports:** One blank line between the last import and the first definition.

**Blank lines — end of file:** Every file ends with exactly one trailing newline.

**Trailing whitespace:** Never present. `ruff format` enforces this.

**Quote style:** Double quotes. Configured as `quote-style = "double"` in `[tool.ruff.format]`.

```python
raise ConfigError(f"missing required key: {key!r}")
```

**Brace/bracket placement:** Opening bracket on the same line as the assignment. Closing bracket on its own line for multi-line structures.

```python
SUPPORTED_EXTENSIONS: set[str] = {
    ".md",
    ".mdx",
    ".yaml",
    ".yml",
}
```

**Trailing commas:** Present on the last element of every multi-line structure.

**Line continuation:** Implicit via open brackets. Never backslash.

```python
result = renderer.render(
    page=page,
    context=ctx,
    strict=True,
)
```

**Import block formatting:** Three groups — stdlib, then third-party, then local — separated by one blank line each. `isort` profile `"black"` is configured. One import per line.

```python
import hashlib
import os
import sys
from pathlib import Path

import yaml

from lumen.errors import ConfigError
from lumen.models import PageNode
```

---

### TypeScript

Formatted by Prettier. Config in `.prettierrc` at the repo root.

**Indentation:** 2 spaces. Never tabs.

```typescript
function buildIndex(pages: Page[]): SearchIndex {
  const entries: IndexEntry[] = pages.map((page) => ({
    id: page.slug,
    title: page.title,
    body: page.plainText,
  }));
  return { entries };
}
```

**Line length:** 100 characters. Configured as `printWidth: 100` in `.prettierrc`.

**Blank lines — top-level:** One blank line between top-level function and class definitions.

**Blank lines — methods:** One blank line between methods inside a class.

**Blank lines — end of file:** Every file ends with exactly one trailing newline. Prettier enforces this.

**Trailing whitespace:** Never present.

**Quote style:** Double quotes. Configured as `singleQuote: false` in `.prettierrc`.

```typescript
const endpoint = "/_search/index.json";
```

**Semicolons:** Always present at end of statements. Configured as `semi: true`.

**Trailing commas:** `"all"` — present in function parameters, arguments, arrays, and objects wherever valid.

```typescript
export function highlight(
  code: string,
  language: string,
  options: HighlightOptions,
): string {
```

**Import block formatting:** One import per line. External imports before local imports. No blank line between groups (Prettier does not manage import order; `eslint-plugin-import` handles ordering).

```typescript
import { marked } from "marked";
import Prism from "prismjs";

import type { Page, SearchIndex } from "./types";
import { slugify } from "./util";
```

---

## 7. Naming Conventions

### Python

**Functions:** `snake_case`. Named after action and noun: `parse_frontmatter`, `render_page`, `load_config`, `hash_asset`.

**Classes:** `PascalCase`. Named after the domain concept: `Renderer`, `Builder`, `PageNode`, `ConfigError`.

**Variables:** `snake_case`. Short names for short scopes (`p`, `f`, `node`, `ctx`). Descriptive names at module level.

**Constants:** `SCREAMING_SNAKE_CASE` at module level.

```python
DEFAULT_OUTPUT_DIR: str = "_site"
SUPPORTED_EXTENSIONS: set[str] = { ... }
```

**Private helpers:** Single leading underscore.

```python
def _render_inline(node: InlineNode, ctx: RenderContext) -> str:
```

**Exception classes:** In `lumen/errors.py`. All inherit from `LumenError`. Named with `Error` suffix.

```python
class ParseError(LumenError): ...
class ConfigError(LumenError): ...
class BuildError(LumenError): ...
```

**File names:** `snake_case`, single noun or noun phrase: `builder.py`, `renderer.py`, `models.py`.

---

### TypeScript

**Functions:** `camelCase`. Named after action and noun: `buildIndex`, `queryIndex`, `highlightCode`, `scrollToAnchor`.

**Classes:** `PascalCase`. Rare — prefer plain functions and objects.

**Interfaces and type aliases:** `PascalCase`. Interfaces for objects with behavior, type aliases for data shapes.

```typescript
interface SearchEngine {
  query(term: string): SearchResult[];
}

type Page = {
  slug: string;
  title: string;
  plainText: string;
};
```

**Variables:** `camelCase`. `const` by default; `let` only when the value is reassigned.

**Constants:** `SCREAMING_SNAKE_CASE` for module-level constants that are not exported as typed values.

```typescript
const MAX_RESULTS = 20;
const DEBOUNCE_MS = 150;
```

**File names:** `camelCase` for runtime modules: `search.ts`, `highlight.ts`, `nav.ts`. Test files: `<module>.test.ts`.

---

## 8. Type Annotations

### Python

- Annotate every function signature — parameters and return type.
- Use built-in generics: `list[str]`, `dict[str, Any]`, `set[str]`. Never import from `typing` for these.
- Use `X | None` for optional types. Never `Optional[X]`.
- Dataclasses in `models.py` have fully annotated fields.

```python
from dataclasses import dataclass

@dataclass
class PageNode:
    slug: str
    title: str
    children: list["BlockNode"]
    metadata: dict[str, str]
```

- Type checker: `mypy`. Config in `pyproject.toml` under `[tool.mypy]`.

### TypeScript

- TypeScript strict mode is enabled (`"strict": true` in `tsconfig.json`).
- No `any`. Use `unknown` for values of genuinely unknown type, then narrow with guards.
- No non-null assertions (`!`). Use explicit null checks.
- All exported functions have explicit return type annotations.

```typescript
export function queryIndex(index: SearchIndex, term: string): SearchResult[] {
  if (!term.trim()) {
    return [];
  }
  return index.entries
    .filter((e) => e.body.includes(term) || e.title.includes(term))
    .map((e) => ({ slug: e.id, title: e.title }));
}
```

---

## 9. Imports

### Python

- Three groups: stdlib, third-party, local. Separated by blank lines. `isort` profile `"black"`.
- Never `import *`.
- No `__future__` imports.
- Local imports use the full package path: `from lumen.models import PageNode`, never `from models import PageNode`.

```python
import os
import sys
from pathlib import Path

import yaml

from lumen.errors import ParseError
from lumen.models import BlockNode, PageNode
```

### TypeScript

- External imports first, then local imports. Managed by `eslint-plugin-import`.
- `import type` for type-only imports.
- No wildcard imports.

```typescript
import { marked } from "marked";

import type { Page } from "./types";
import { slugify } from "./util";
```

---

## 10. Error Handling

### Python

- All custom exceptions are defined in `lumen/errors.py` and inherit from `LumenError`.
- Public functions that can fail raise a `LumenError` subclass — never a bare `Exception` or `ValueError`.
- Internal helpers raise the same typed exceptions; they do not catch and re-wrap unless adding context.
- `cli.py` catches `LumenError` at the top level, prints the message to stderr, and exits with code 1.

```python
def load_config(path: Path) -> Config:
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    return Config(**raw)
```

- Never swallow exceptions silently. If a file can be skipped, log a warning before continuing.
- No bare `except:`. Always `except Exception` at minimum.

### TypeScript

- Functions that can fail return `Result<T, E>` — a discriminated union, not thrown exceptions.
- Exceptions are only thrown for programmer errors (impossible states). User-facing errors use `Result`.

```typescript
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

export function parseQuery(raw: string): Result<Query, string> {
  if (!raw.trim()) {
    return { ok: false, error: "query must not be empty" };
  }
  return { ok: true, value: { terms: raw.trim().split(/\s+/) } };
}
```

---

## 11. Comments and Docstrings

### Python

**Module docstrings:** Every module has a one-sentence module docstring describing its role.

```python
"""Parse Markdown and YAML source files into the lumen intermediate representation."""
```

**Function docstrings:** Public functions have a one-line docstring. Multi-line only when parameters or return values need explanation. Google style.

```python
def render_page(self, page: PageNode) -> str:
    """Render a PageNode to an HTML string."""
```

**Inline comments:** Two spaces before `#`, one space after. Used only for non-obvious logic.

**Never:** commented-out code, `TODO` without a linked issue, docstrings that restate the function signature.

### TypeScript

**JSDoc:** Exported functions and interfaces have a JSDoc comment. One line when the name is self-explanatory; multi-line when the contract needs clarification.

```typescript
/**
 * Build a search index from the given pages.
 * The index is serialized and embedded in the generated site.
 */
export function buildIndex(pages: Page[]): SearchIndex {
```

**Inline comments:** `//` with one space. Two spaces before when appended to a line of code.

**Never:** commented-out code, `@ts-ignore` without a following comment explaining why.

---

## 12. Testing

### Python

Framework: `pytest`. Config in `pyproject.toml` under `[tool.pytest.ini_options]`.

```bash
pytest
pytest -x          # stop on first failure
pytest -k parser   # filter by name
```

- Test files in `tests/`, named `test_<module>.py`.
- Test functions named `test_<function>_<scenario>`.
- Shared fixtures in `tests/conftest.py`.
- No `unittest.TestCase` classes. All tests are plain functions.

```python
def test_parse_frontmatter_valid(tmp_path: Path) -> None:
    source = "---\ntitle: Hello\ndate: 2024-01-01\n---\n"
    result = parse_frontmatter(source)
    assert result == {"title": "Hello", "date": "2024-01-01"}
```

### TypeScript

Framework: `vitest`. Config in `package.json` under `"vitest"`.

```bash
npm test
npm run test:watch
```

- Test files in `runtime/tests/`, named `<module>.test.ts`.
- Test functions use `describe` and `it` blocks.

```typescript
describe("queryIndex", () => {
  it("returns empty array for empty term", () => {
    const index = buildIndex([{ slug: "a", title: "A", plainText: "alpha" }]);
    expect(queryIndex(index, "")).toEqual([]);
  });
});
```

---

## 13. Git

> **Repo-wide:**

**Commit prefixes:**

- `feat:` — new user-visible feature in either the Python engine or the TypeScript runtime
- `fix:` — bug correction
- `refactor:` — restructuring without behavior change
- `docs:` — documentation only
- `chore:` — build, CI, dependency, tooling changes
- `test:` — adds or modifies tests
- `perf:` — measurable performance improvement

**Scopes:** Optional. Used to disambiguate when the commit is clearly isolated to one half of the codebase.

```
feat(runtime): add fuzzy matching to search index
fix(engine): handle YAML files with BOM prefix
chore: upgrade marked to v12
```

**Subject line:** Imperative mood. No period. Under 72 characters.

**Branch naming:** `<prefix>/<short-description>` with hyphens.

```
feat/fuzzy-search
fix/bom-handling
chore/vitest-upgrade
```

**Merge strategy:** Rebase. No merge commits.

**GPG signing:** Not required.

---

## 14. Dependencies and Tooling

### Python

- **Package manager:** pip with `pyproject.toml`. No `requirements.txt`.
- **Install:** `pip install -e ".[dev]"`.
- **Add a dependency:** Add to `[project.dependencies]` in `pyproject.toml`. Run `pip install -e ".[dev]"` to update the environment.
- **Linter/formatter:** `ruff`. Config in `pyproject.toml` under `[tool.ruff]` and `[tool.ruff.format]`.
- **Type checker:** `mypy`. Config in `pyproject.toml` under `[tool.mypy]`.
- **Minimum Python:** 3.11.

### TypeScript

- **Package manager:** npm. `package-lock.json` is committed.
- **Add a dependency:** `npm install <pkg>`.
- **Formatter:** Prettier. Config in `.prettierrc`.
- **Linter:** ESLint. Config in `.eslintrc.json`.
- **Test runner:** vitest. Config in `package.json`.
- **Bundler:** esbuild. Config in `scripts/build.js`.
- **Minimum Node:** 20 (declared in `package.json` under `"engines"`).

---

## 15. Red Lines

**Formatting violations:**

- Never use single quotes in Python. All string literals use double quotes — enforced by `ruff format`.
- Never use tabs in Python. All indentation is 4 spaces — enforced by `ruff format`.
- Never use tabs in TypeScript. All indentation is 2 spaces — enforced by Prettier.

**Architectural violations:**

- Never define custom exception classes outside `lumen/errors.py`. All exceptions inherit from `LumenError` and live in one file.
- Never put build logic in `lumen/cli.py`. That file contains only argument parsing and dispatch to `builder.py`.
- Never import from `runtime/` in Python code, or from `lumen/` in TypeScript code. The two halves share no runtime dependencies.

**Style violations:**

- Never use `Optional[X]` in Python. This codebase uses `X | None` exclusively.
- Never import from `typing` for generics that are available as builtins (`list`, `dict`, `set`, `tuple`).
- Never use `any` in TypeScript. Use `unknown` and narrow with type guards.
- Never use non-null assertions (`!`) in TypeScript. Use explicit null checks.

**Testing violations:**

- Never use `unittest.TestCase` in Python tests. All tests are plain `pytest` functions.
- Never write tests that perform real filesystem I/O outside of `tmp_path`. Use pytest's `tmp_path` fixture.

**Git violations:**

- Never commit without a conventional prefix.
- Never commit `package-lock.json` with uncommitted `package.json` changes. Keep them in sync.
- Never commit commented-out code.
