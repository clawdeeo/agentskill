---
name: agentskill
description: Analyze code repositories to extract coding style conventions and synthesize an AGENTS.md file. Use when generating, updating, or improving AGENTS.md from actual code. Triggers on 'generate AGENTS.md', 'extract my coding style', 'analyze my repos for style', 'create style guide from my code'.
---

# agentskill

Analyze repos, synthesize AGENTS.md.

## Workflow

1. **Collect** — Ask for repo paths (local or remote).
2. **Extract** — Run `scripts/extract.py <repos...>` → JSON report.
3. **Check GOTCHAS.md** — Read `references/GOTCHAS.md` before synthesis.
4. **Review examples/** — Browse for templates if needed.
5. **Synthesize** — Use `references/synthesis-prompt.md` with extraction data.
6. **Iterate** — Present draft, adjust per feedback.
7. **Save** — Write final AGENTS.md.

## Principles

- **Extract, don't guess.** AST + git metrics.
- **Multi-language.** Document all languages found.
- **Triangulate.** Patterns across repos = personal; single repo = project-specific.
- **Actionable.** "Prefer early extraction" > "Keep functions short."
- **Minimal.** Distinctive rules only.

## References

- **GOTCHAS.md** — Extraction/synthesis errors to avoid.
- **synthesis-prompt.md** — LLM prompt template.
- **output-template.md** — Structure guide.
- **examples/** — Successful AGENTS.md samples.

## Scripts

- `scripts/extract.py` — Multi-language extraction.
