# GOTCHAS.md — Errors to Avoid in Generation

## Extraction Errors

| Error | Problem | Fix |
|-------|---------|-----|
| Keyword pollution | `self`, `if`, `for` counted as vars | Filter keywords |
| Single-word ambiguity | `foo` matches camelCase and snake_case | Require transitions |
| Generated file skew | lockfiles have 0 comments | Exclude vendored/generated |
| Test file bias | tests use `unwrap` heavily | Sample src/ and tests/ separately |
| Git squash gaps | lost commit granularity | Note when history is flattened |

## Synthesis Errors

| Error | Problem | Fix |
|-------|---------|-----|
| Overfitting | Pattern only in one repo | Flag "project-specific" |
| Default assumption | Claiming rustfmt use when it's cargo default | Only explicit custom configs |
| Convention vs preference | `feat:` prefix might be team, not personal | Check solo projects |
| Context confusion | High unwrap in CLI != library tolerance | Contextualize by crate type |
| Universal noise | "Uses snake_case in Rust" — obvious | Only document deviations |

## Confidence Annotations

- **High** — Consistent across repos, many files
- **Medium** — Pattern with exceptions, or limited sample
- **Low** — Few instances, flag as tentative

## Red Flags

- Generic advice applicable to anyone
- Contradictory patterns unexplained
- No src/test distinction
- Unusual claims without confidence annotations
