# agentskill

Generate AGENTS.md from your actual coding style.

## What It Does

1. **Scans repos** -- git history, source files, configs.
2. **Detects style** -- naming, errors, comments, spacing.
3. **Synthesizes** -- clean AGENTS.md via LLM.

## Install

```bash
clawhub install clawdeeo/agentskill
```

Or standalone:
```bash
python3 scripts/extract.py /path/to/repo
```

## Usage

With OpenClaw:
```
> Analyze my coding style from ~/projects/myapp
```

Standalone:
```bash
python3 scripts/extract.py ~/projects/myapp -o report.json
```

## Detected Patterns

| Category | Patterns |
|----------|----------|
| **Naming** | case style, avg length, descriptiveness |
| **Spacing** | blank lines between blocks |
| **Comments** | style, density, what gets explained |
| **Errors** | unwrap vs ? vs Result |
| **Git** | commit prefixes, branches |
| **Tooling** | linters, CI configs |

## Languages

Every language is supported.

## Structure

```
agentskill/
├── SKILL.md
├── README.md
├── scripts/extract.py
├── references/
│   ├── GOTCHAS.md
│   ├── OUTPUT-TEMPLATE.md
│   └── SYNTHESIS-PROMPT.md
└── examples/
    └── SAMPLE.md
```

## License

MIT
