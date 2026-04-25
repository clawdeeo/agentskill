# AGENTS.md -- Coding Style

## Overview

Multi-language codebase spanning Rust, Python, and Go. Analyzed 3 repositories (cli-tools, web-api, utils-lib). Pragmatic tool-builder: self-documenting code over verbose comments, descriptive function names over terse ones, fail-fast over defensive error handling. Conventional commit discipline with lean, action-oriented messages.

Key principles distilled from actual patterns:
- Descriptive names over terse abbreviations
- Propagate errors, never swallow silently
- Comments explain "why", code explains "what"

## Cross-Language Patterns

Patterns holding across all detected languages:

### Naming
- **vars:** snake_case
- **functions:** snake_case
- **types:** PascalCase
- **constants:** SCREAMING_SNAKE_CASE

### Comments
- **Philosophy:** Documentation via doc comments for public API; minimal inline comments
- **Density:** Low (~5-8% of code lines)

### Error Handling
- Fail fast in CLI context; propagate in library code
- Never panic or raise without context

---

## Rust
### Naming
- **Vars:** snake_case (142) over camelCase (3)
- **Functions:** snake_case (87), highly descriptive -- 22 char avg
- **Types:** PascalCase (45)
- **Constants:** SCREAMING_SNAKE_CASE (115) over PascalCase (8)

### Error Handling
- `?` propagation: 232 occurrences
- `unwrap()`: 254 occurrences (CLI context only)
- `expect()`: 0 occurrences
- `panic!`: 0 occurrences

### Comments
- **Density:** 4.2%
- **Style:** `///` for public API, `//!` for module-level, `//` for inline

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

### Error Handling
- `try_except`: 24 occurrences
- `raise`: 18 occurrences
- `assert`: 45 occurrences (test files)
- `with_context`: 31 occurrences

### Comments
- **Density:** 6.1%
- **Style:** `"""` for modules and public functions, `#` for inline

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

## Git

### Commits
- **Format:** Conventional commits
- **Prefixes:** `feat`, `fix`, `docs`, `refactor`, `chore`
- **Avg length:** 41 chars
- **Style:** Lowercase, imperative mood

### Branches
- Sparse branching -- trunk-based workflow
- **Prefixes:** `feature/`, `fix/`

### Signing
- GPG signing: enabled
- Signoff: not configured

### Remotes
- Primary: GitHub
- Remote count: 1 per repository

---

## Tooling

Detected configurations:
- Cargo workspace (Rust)
- pytest (Python)
- GitHub Actions CI
- No explicit formatter configs detected
- Lockfiles: Cargo.lock, package-lock.json
- Docker: Dockerfile present in web-api
- License: MIT (all repositories)
- README: present in all repositories

---

## Red Lines

Explicit avoidances based on actual patterns:

- Never `panic!` -- controlled failure only
- Never `expect()` with messages -- unwrap or propagate
- No verbose comments -- self-document or omit
- Never mix naming conventions within a category
- Fail fast over defensive in CLI context
- Descriptive function names -- clarity over brevity

---

**Source:** cli-tools (68 commits, 40 Rust files), web-api (42 commits, 32 Python files), utils-lib (15 commits, 8 Go files)
**Files analyzed:** 80
**Confidence:** High on naming/git patterns; Medium on Go conventions (limited sample); Low on branch patterns (trunk-based, few branches)