# AGENTS.md — Coding Style

## Overview

Multi-language codebase spanning Go, Python, Rust. Analyzed 3 repositories (cli-tools, web-api, utils-lib). Pragmatic tool-builder: self-documenting code over verbose comments, descriptive function names over terse ones, fail-fast over defensive error handling. Conventional commit discipline with lean, action-oriented messages.

Key principles distilled from actual patterns:
- Descriptive names over terse abbreviations
- Propagate errors, never swallow silently
- Self-documenting code over verbose comments

## Cross-Language Patterns

Patterns holding across all detected languages:

### Naming
- **vars:** snake_case
- **functions:** snake_case
- **types:** PascalCase
- **consts:** SCREAMING_SNAKE_CASE

### Comments
- **Philosophy:** Documentation via `///`, `"""`, `//`

### Error Handling
- Fail fast in CLI context; propagate in library code

---

## Rust
### Naming
- **Vars:** snake_case (142) over camelCase (3)
- **Functions:** snake_case (87)
- **Types:** PascalCase (45)
- **Constants:** SCREAMING_SNAKE_CASE (115) over PascalCase (8)

### Type Annotations
- **Param density:** High (92%)
- **Return density:** 88%

### Import Order
- **Style:** std → crate → external

### Error Handling
- `?` propagation: 232 occurrences
- `unwrap()`: 254 occurrences
- `expect()`: 0 occurrences
- `panic!`: 0 occurrences

### Comments
- **Density:** 4.2%
- **Style:** `///` for public API, `//!` for module-level

### Spacing
- **Avg blank lines between blocks:** 1.4

### Imports
- **std:** 28 imports
- **crate:** 15 imports
- **external:** 9 imports

*40 files analyzed*

## Python
### Naming
- **Vars:** snake_case (203) over camelCase (12)
- **Functions:** snake_case (68)
- **Types:** PascalCase (31)

### Type Annotations
- **Param density:** Medium (54%)
- **Return density:** 41%

### Import Order
- **Style:** stdlib → third-party → local

### Error Handling
- `try_except`: 24 occurrences
- `raise`: 18 occurrences
- `with_context`: 31 occurrences

### Comments
- **Density:** 6.1%
- **Style:** `"""` for modules and public functions

### Spacing
- **Avg blank lines between blocks:** 1.2

### Imports
- **stdlib:** 42 imports
- **third_party:** 27 imports
- **local:** 14 imports

*32 files analyzed*

## Go
### Naming
- **Vars:** camelCase (unexported), PascalCase (exported)
- **Functions:** PascalCase (exported), camelCase (unexported)

### Error Handling
- Explicit error returns, no exceptions
- `errors.New` and `fmt.Errorf` for construction

### Comments
- **Density:** 3.8%
- **Style:** `//` for both inline and doc comments

### Spacing
- **Avg blank lines between blocks:** 1.0

*8 files analyzed*

---

## Repository Structure

### File Naming
- **Dominant style:** snake_case

### Directory Depth
- **Max:** 5 levels
- **Average:** 2.3 levels

### Test Organization
- **Location:** separate_dirs
- **Frameworks:** pytest, cargo test

### Module Patterns
- **Barrel files:** mod.rs, lib.rs detected
- **Init files:** __init__.py detected

## Commands and Workflows

### Install
```bash
poetry install
```

```bash
cargo build
```

### Dev
```bash
just dev
```

### Build
```bash
make build
```

```bash
cargo build --release
```

### Test
```bash
pytest
```

```bash
cargo test
```

### Lint
```bash
ruff check .
```

```bash
cargo clippy
```

### Format
```bash
black .
```

```bash
cargo fmt
```

### CI
```bash
pytest --cov
```

```bash
cargo test --all-features
```

## Git

### Commits
- **Prefixes:** `feat`, `fix`, `docs`, `refactor`, `chore`
- **Avg length:** 41 chars
- **Style:** Lowercase, imperative mood

### Branches
- **Prefixes:** `feature/`, `fix/`, `main`

### Signing
- GPG signing: enabled
- Signoff: not configured

### Remotes
- Primary: GitHub
- Remote count: 1 per repository

## Tooling

Detected configurations:
- cargo (Rust)
- pytest (Python)
- GitHub Actions CI
- just
- ruff
- black

## Dependencies

### Package Managers
- cargo
- poetry
- npm

### Philosophy
- **Average dependency count:** 12 per project
- **Pin style:** locked

## Red Lines

Explicit avoidances based on actual patterns:

- Never `panic!` — controlled failure only
- Never `expect()` with messages — unwrap or propagate
- No verbose comments — self-document or omit
- Never mix naming conventions within a category
- Fail fast over defensive in CLI context

## Code Examples

Actual patterns from the codebase:

### Example 1
```
// From cli.rs:
pub fn run(config: Config) -> Result<(), Error> {
    let input = fs::read_to_string(&config.input)
        .map_err(|e| Error::Io(e))?;
    process(input)
}
```

### Example 2
```
# From analyzer.py:
def detect_patterns(content: str, patterns: dict) -> dict:
    matches = {}
    for name, pattern in patterns.items():
        count = len(re.findall(pattern, content))
        if count > 0:
            matches[name] = count
    return matches
```

### Example 3
```
// From handler.go:
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    data, err := h.service.Process(r.Context(), r.Body)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    json.NewEncoder(w).Encode(data)
}
```

---

**Source:** cli-tools, web-api, utils-lib
**Files analyzed:** 80
**Confidence:** High on naming/git patterns; Medium on Go conventions (limited sample); Low on branch patterns (trunk-based, few branches)