# Synthesis Prompt

Synthesize AGENTS.md from extraction report. Multi-language.

## Input

```json
{
  "repos": [...],
  "analyses": [{
    "languages": { "rust": {...}, "python": {...} },
    "code_style": { "naming_descriptiveness": {...}, "blank_lines": {...} },
    "git": { "commits": {...}, "branches": {...} },
    "tooling": {...}
  }]
}
```

## Output Structure

```markdown
# AGENTS.md

## Overview
One-paragraph philosophy.

## Cross-Language Patterns
Patterns holding across langs (if any).

## [Language]
### Naming
case style, avg length, descriptiveness

### Error Handling
patterns

### Comments
density, style

### Spacing
blank line habits

## Git
- Commits: format, prefixes, length
- Branches: naming

## Tooling

## Red Lines
Explicit avoidances

---
**Source:** repo names + stats
**Confidence:** High/Medium/Low on claims
```

## Rules

1. **Multi-language.** Document every language found.
2. **Cross-language top.** Shared patterns once at top.
3. **Data only.** Omit if ambiguous; annotate confidence.
4. **Flag project-specific.** Single-repo patterns labeled.
5. **No universal noise.** Skip obvious (e.g., snake_case in Rust).
6. **Contextualize.** unwrap in CLI != library.
7. **Read GOTCHAS.md first.**
