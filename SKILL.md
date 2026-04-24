---
name: agentskill
description: Analyze one or more code repositories to extract the user's coding style conventions and synthesize an AGENTS.md file that captures their personal coding philosophy, naming patterns, git habits, and project conventions. Use when the user wants to generate, update, or improve their AGENTS.md based on actual code they've written. Triggers on phrases like 'generate AGENTS.md', 'extract my coding style', 'analyze my repos for style', 'create style guide from my code', 'synthesize AGENTS.md'.
---

# AgentSkill — Coding Style Synthesizer

Analyze repositories and synthesize a personal AGENTS.md that captures coding style, conventions, and habits across **all detected languages**.

## Workflow

1. **Collect inputs** — Ask user for one or more repository paths (local or remote). No need to ask about languages — we detect all.

2. **Run extraction** — Execute `scripts/extract.py <repo-paths...>` which outputs a structured JSON report containing patterns across all languages found.

3. **Check GOTCHAS.md** — Read `references/GOTCHAS.md` for common extraction errors and synthesis pitfalls to avoid.

4. **Review examples** — If available, browse `examples/` folder for successful AGENTS.md templates and patterns.

5. **Synthesize AGENTS.md** — Feed the JSON report into the LLM with `references/synthesis-prompt.md`. Draft a clean AGENTS.md in the user's voice.

6. **Iterate** — Present the draft. Let the user request adjustments. Re-run synthesis with updated instructions.

7. **Save** — Write the final AGENTS.md to the user's workspace.

## Key Principles

- **Extract, don't guess.** Use AST-level metrics and git logs.
- **Triangulate.** Find patterns that hold across repos. Flag repo-specific deviations.
- **Multi-language.** Detect and document patterns for **every language found**, not just one.
- **Separate style from tooling.** Linter rules go in "Tooling". Personal philosophy goes in "Style".
- **Actionable, not abstract.** "Prefer early extraction" beats "Keep functions short."
- **Minimal.** Only include distinctive or non-obvious rules.

## When to Read References

- **GOTCHAS.md:** Always read before synthesis — contains extraction errors to avoid.
- **synthesis-prompt.md:** Read before generating AGENTS.md draft.
- **output-template.md:** Read if user wants specific AGENTS.md structure.
- **examples/:** Browse for successful templates to emulate.

## Scripts

- `scripts/extract.py` — Main extraction engine. Run: `python3 scripts/extract.py <repo1> [repo2] ...`
  - Requires Python 3.8+
  - Multi-language support (Rust, Python, Go, JS/TS, etc.)
  - Outputs JSON to stdout
