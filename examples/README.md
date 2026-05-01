# Language Examples

This directory contains compact static fixtures for every supported language.

They are analyzer fixtures, not runnable projects. They intentionally avoid
dependency installs, build outputs, vendored code, and generated files.

## What They Validate

The per-language directories are the release-grade verification backbone for:

- `agentskill analyze <repo>` aggregate analyzer output
- individual analyzer behavior for `scan`, `measure`, `config`, `graph`, `symbols`, and `tests`
- the supported-language matrix advertised by the packaged tool

The `mixed/` fixture validates multi-language behavior across several analyzers
in one repository shape.

Available example repos:

- `python/`
- `javascript/`
- `typescript/`
- `go/`
- `rust/`
- `java/`
- `kotlin/`
- `csharp/`
- `c/`
- `cpp/`
- `ruby/`
- `php/`
- `swift/`
- `objectivec/`
- `bash/`
- `mixed/`

## Typical Commands

```bash
agentskill analyze examples/python --pretty
agentskill scan examples/typescript --pretty
agentskill generate examples/mixed
```

Use the installed `agentskill` CLI as the canonical interface. The example
repos exist to validate analyzers and generation flows; they are not intended
to be built or installed as standalone projects.

## Reference Markdown Examples

`SINGLE_LANGUAGE.md`, `MULTI_LANGUAGE.md`, and `MONOREPO.md` are reference
`AGENTS.md` outputs. They are useful for understanding the rendered document
shape, but they are not the analyzer-fixture source of truth for language
support.
