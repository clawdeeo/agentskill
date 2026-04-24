# agentskill

Generate AGENTS.md from your actual coding style. Analyzes repositories and synthesizes a personal conventions document that captures how you actually write code — not how you think you do.

## What It Does

1. **Scans your repos** — Extracts patterns from git history, source files, and configs
2. **Detects style** — Naming conventions, error handling, comment philosophy, spacing habits
3. **Synthesizes AGENTS.md** — Turns the data into a clean, actionable style guide

## Installation

As an OpenClaw skill:

```bash
clawhub install clawdeeo/agentskill
```

Or use the extraction script standalone:

```bash
python3 scripts/extract.py /path/to/repo
```

## Usage

### With OpenClaw

```
> Analyze my coding style from ~/projects/gitclaw and ~/projects/myapp
```

The skill will:
- Run extraction on both repos
- Synthesize a draft AGENTS.md
- Let you iterate on it

### Standalone Script

```bash
python3 scripts/extract.py ~/projects/gitclaw ~/projects/myapp -o report.json
cat report.json | jq '.code_style.rust.naming_descriptiveness'
```

## What Gets Detected

| Category | Patterns |
|----------|----------|
| **Naming** | Case style, average name length by symbol type |
| **Spacing** | Blank line habits between blocks |
| **Comments** | Style (// vs ///), density, what gets documented |
| **Error handling** | unwrap vs ? vs Result, panic tolerance |
| **Git** | Commit prefixes, branch naming, PR style |
| **Tooling** | Linters, formatters, CI configs |

## Supported Languages

- **Rust** — Full analysis
- **Python** — Partial (naming, comments)
- **Go** — File detection only
- **JavaScript/TypeScript** — File detection only

PRs welcome for deeper language support.

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Repos     │────>│  extract.py  │────>│   Report    │
│   (1-N)     │     │  (AST + git) │     │   (JSON)    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                       ┌──────────────┐
                                       │   LLM +      │
                                       │   synthesis  │
                                       │   prompt     │
                                       └──────┬──────┘
                                                │
                                                ▼
                                          ┌──────────┐
                                          │ AGENTS.md│
                                          └──────────┘
```

## Output Example

```markdown
# AGENTS.md — Coding Style

## Overview
Pragmatic Rustacean. Prefers explicit over clever, early extraction,
zero tolerance for dead code.

## Rust

### Naming
- Variables: snake_case (avg length: 12 chars)
- Types: PascalCase (avg length: 18 chars)
- Constants: SCREAMING_SNAKE_CASE

### Comments
- Minimal. Prefer doc comments (///) for public APIs.
- Density: ~5% of code lines.
- No inline comments explaining "what" — only "why".

### Spacing
- One blank line between functions.
- Two blank lines between modules.

### Error Handling
- Propagate with `?` in library code.
- Never `unwrap()` — always handle or expect with message.

## Git
- Branches: fix/, feat/, docs/, chore/
- Commits: conventional format, lowercase
- PR titles: lowercase

## Red Lines
- Never commit to main.
- No dead code — remove, don't #[allow].
```

## License

MIT © Francesco Sardone (Airscript)
