# AGENTS.md Output Template

Use this as the structural reference for AGENTS.md generation. Adapt sections based on detected languages and patterns.

## Required Sections

- **Overview** — 1-2 sentence philosophy summary
- **Per-language sections** — One section per primary language detected
- **Git** — Branch, commit, PR conventions
- **Tooling** — Linters, formatters, CI
- **Red Lines** — Hard rules (never/don't)

## Optional Sections

- **Testing** — If test patterns are distinctive
- **Documentation** — If docs have specific conventions
- **Security** — If security patterns stand out (e.g., no secrets in code, input validation)
- **Performance** — If performance considerations are recurring

## Section Order

Overview → Languages (alphabetical) → Git → Tooling → Red Lines → Optional extras

## Tone

Direct, imperative, warm. No fluff. Match the user's own tone from commit messages.
