# GOTCHAS.md — Common Extraction Errors to Avoid

This file documents common pitfalls in repository analysis and AGENTS.md synthesis. Read before synthesizing to avoid repeating these errors.

## Extraction Errors

### Variable Naming False Positives
- **Issue:** Regex catches `self`, `cls`, `if`, `for` as variable names
- **Fix:** Filter out keywords and builtins before counting

### camelCase vs snake_case Confusion
- **Issue:** Single-word identifiers match both patterns
- **Fix:** Require at least one transition (lower->upper or underscore) to classify

### Comment Density Skew
- **Issue:** Generated files (lockfiles, vendored code) have 0 comments
- **Fix:** Exclude generated files from sampling

### Test File Bias
- **Issue:** Tests use `unwrap()` heavily; library code doesn't
- **Fix:** Sample src/ and tests/ separately, report both

### Git History Gaps
- **Issue:** Squashed commits lose granularity
- **Fix:** Note when history is flattened; rely more on file analysis

## Synthesis Errors

### Overfitting to One Repo
- **Issue:** Pattern only appears in one of multiple repos
- **Fix:** Flag as "Project-specific" unless consistent across repos

### Assuming Defaults
- **Issue:** "Uses rustfmt" because rustfmt.toml exists — maybe it's cargo defaults
- **Fix:** Only claim explicit custom configs

### Confusing Convention with Preference
- **Issue:** `feat:` prefix might be team convention, not personal
- **Fix:** Look for solo projects to find true preference

### Misattributing Style
- **Issue:** High `unwrap` count in a CLI tool != tolerance in libraries
- **Fix:** Contextualize patterns by crate type

### Over-documenting Basics
- **Issue:** Stating "uses snake_case in Rust" — this is universal, not personal
- **Fix:** Only document deviations or unusual combinations (e.g., camelCase vars)

## Confidence Levels

Use these in synthesized AGENTS.md:

- **High:** Pattern appears consistently across multiple repos, many files
- **Medium:** Pattern appears but with exceptions, or limited sample
- **Low:** Pattern inferred from few instances, flag as tentative

## Red Flags

If you see these, question your synthesis:

- Generic advice that could apply to any programmer
- Contradictory patterns without explanation
- No distinction between code and test styles
- Missing confidence annotations on unusual claims
