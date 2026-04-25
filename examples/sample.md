# AGENTS.md — Coding Style

## Overview

Pragmatic tool-builder. Self-documenting code, descriptive names, fail-fast errors. Conventional commits, lean messages.

---

## Cross-Language Patterns

### Naming
- Descriptive over terse (20+ char functions)
- camelCase variables, snake_case functions

### Comments
- Minimal (~5% density)
- "Why" not "what"

---

## Rust

### Naming
- Variables: camelCase (507) + snake_case (129)
- Types: PascalCase
- Constants: SCREAMING_SNAKE_CASE
- Functions: snake_case, 22 char avg

### Error Handling
- unwrap (254) alongside ? (232)
- No expect, no panic

### Comments
- Zero in core source
- // style when used

### Spacing
- 1 blank line between blocks

### Tooling
- Cargo, GitHub Actions

---

## Git

### Commits
- Conventional: feat (23), fix (15), docs (13), refactor (8), chore (7)
- 41 char avg
- Lowercase, imperative

### Branches
- Sparse — trunk-based workflow

---

## Red Lines

- Never panic — controlled failure only
- No verbose comments
- Descriptive names over terse

---

**Source:** gitclaw (68 commits, 40 Rust files)

**Confidence:** High (naming, git); Medium (branches)
