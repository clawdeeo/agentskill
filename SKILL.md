---
name: agentskill
description: Analyze one or more code repositories to extract the user's coding style conventions and synthesize an AGENTS.md file that captures their personal coding philosophy, naming patterns, git habits, and project conventions. Use when the user wants to generate, update, or improve their AGENTS.md based on actual code they've written. Triggers on phrases like 'generate AGENTS.md', 'extract my coding style', 'analyze my repos for style', 'create style guide from my code', 'synthesize AGENTS.md'.
---

# AgentSkill — Coding Style Synthesizer

Analyze repositories and synthesize a personal AGENTS.md that captures coding style, conventions, and habits.

## Workflow

1. **Collect inputs** — Ask user for one or more repository paths (local or remote). Also ask what languages they care about most, if not obvious.

2. **Run extraction** — Execute `scripts/extract.py <repo-paths...>` which outputs a structured JSON report containing:
   - Naming conventions by language (vars, types, functions, files, branches)
   - Comment patterns (density, style, what gets explained)
   - Function/method metrics (average length, complexity hints)
   - Error handling patterns (Result types, exceptions, unwrap/panic usage)
   - Git conventions (commit prefixes, branch prefixes, PR style)
   - Tooling configs (linter, formatter, CI files)
   - Architecture patterns (module organization, visibility, traits/interfaces)

3. **Synthesize AGENTS.md** — Feed the JSON report into the LLM with the prompt from `references/synthesis-prompt.md`. The LLM reads the data and drafts a clean AGENTS.md in the user's voice.

4. **Iterate** — Present the draft. Let the user request adjustments (more terse, add/remove sections, focus on specific languages). Re-run synthesis with updated instructions.

5. **Save** — Write the final AGENTS.md to the user's workspace or a path they specify.

## Key Principles

- **Extract, don't guess.** Use AST-level metrics and git logs, not surface-level file reading.
- **Triangulate.** If the user gives multiple repos, find patterns that hold across them. Flag repo-specific deviations.
- **Separate style from tooling.** Linter-enforced rules (e.g., tab width) go in a "Tooling" section. Personal philosophy goes in "Style".
- **Actionable, not abstract.** "Prefer early extraction" is better than "Keep functions short."
- **Minimal.** Only include rules that are distinctive or non-obvious. Don't document "use camelCase" unless it's unusual or paired with specific exceptions.

## When to Read References

- **Synthesis prompt template:** Read `references/synthesis-prompt.md` before generating AGENTS.md draft.
- **Output format guide:** Read `references/output-template.md` if the user wants a specific AGENTS.md structure.

## Scripts

- `scripts/extract.py` — The main extraction engine. Run with `python3 scripts/extract.py <repo1> [repo2] ...`.
  - Requires Python 3.8+
  - Uses `git`, `cloc`, and basic AST heuristics (no external parser deps)
  - Outputs JSON to stdout; capture to file if needed
