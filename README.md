# agentskill

Generate AGENTS.md from your actual coding style.

## What It Does

1. **Scans repos** -- source files, git history, tooling configs.
2. **Detects style** -- naming, error handling, comments, spacing, imports.
3. **Synthesizes** -- complete AGENTS.md with red lines, overview, per-language sections, repo structure, git patterns, code examples.

## Install

```bash
# Generate AGENTS.md
python3 scripts/agentskill.py ~/projects/myapp

# Raw JSON analysis
python3 scripts/agentskill.py ~/projects/repo1 ~/projects/repo2 --json -o report.json

# Skip sections
python3 scripts/agentskill.py ~/projects/myapp --skip-git --skip-tooling

# Install as package
pip install .
agentskill ~/projects/myapp
```

## Detected Patterns

| Category | What It Finds |
|----------|---------------|
| **Naming** | Dominant case style per category (vars, functions, types, consts), average length |
| **Error Handling** | Rust: unwrap/expect/?/panic/Result counts. Python: try/except/raise/assert/with |
| **Comments** | Density, doc vs normal, style (/// vs // vs #) |
| **Spacing** | Average blank lines between code blocks |
| **Imports** | Rust: std/crate/external. Python: stdlib/third-party |
| **Git** | Commit prefixes, average length, branch naming, signing |
| **Tooling** | Cargo, npm, pytest, CI, lockfiles, Docker, editorconfig, license detection |
| **Structure** | File naming, directory depth, test organization, module patterns |
| **Commands** | Install, dev, build, test, lint, format, CI workflows |

## Languages

Every language is supported via a language-agnostic analysis engine. Files are grouped by extension and analyzed through text pattern detection — no language-specific analyzers required.

## Output Sections

Generated AGENTS.md files are ordered by priority:

1. **Red Lines** -- hard constraints, what not to do
2. **Overview** -- project context and key principles
3. **Cross-Language Patterns** -- universal naming, comments, errors
4. **Language Sections** -- per-language details
5. **Commands and Workflows** -- install, test, lint, build, CI
6. **Git** -- commits, branches, signing
7. **Repository Structure** -- tree view, file naming, depth
8. **Tooling** -- detected configs
9. **Dependencies** -- package managers, pin style
10. **Code Examples** -- actual patterns from the codebase

## Examples

- **SIMPLE.md** -- single-language project (most common scenario)
- **MONOREPO.md** -- multi-language, multi-project monorepo

## Structure

```
agentskill/
├── SKILL.md
├── README.md
├── setup.py
├── scripts/
│   └── agentskill.py          # CLI entry point
├── agentskill/                # Core package
│   ├── __init__.py
│   ├── cli.py                 # Pipeline orchestration
│   ├── constants.py           # Shared constants
│   ├── engine.py              # Language-agnostic analysis engine
│   ├── extractors/
│   │   ├── commands.py        # Commands and workflows
│   │   ├── filesystem.py      # Scanning, tooling, metadata
│   │   ├── git.py             # Commits, branches, config, remotes
│   │   └── structure.py      # Repo structure and conventions
│   └── synthesis/
│       └── __init__.py        # AGENTS.md generation
├── references/
│   ├── GOTCHAS.md
│   ├── OUTPUT-TEMPLATE.md
│   └── SYNTHESIS-PROMPT.md
├── examples/
│   ├── SIMPLE.md              # Single-language output
│   └── MONOREPO.md            # Multi-language output
└── tests/
    └── test_agentskill.py
```

## Testing

```bash
python3 tests/test_agentskill.py
```

## License

MIT