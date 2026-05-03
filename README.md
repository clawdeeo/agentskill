# agentskill

[![Main](https://github.com/airscripts/agentskill/actions/workflows/main.yml/badge.svg)](https://github.com/airscripts/agentskill/actions/workflows/main.yml)
[![Release](https://github.com/airscripts/agentskill/actions/workflows/release.yml/badge.svg)](https://github.com/airscripts/agentskill/actions/workflows/release.yml)
![ClawHub](https://skill-history.com/badge/airscripts/agentskill.svg)

Analyze a code repository and synthesize an `AGENTS.md` that lets any agent produce code indistinguishable from the existing codebase.

<p align="center">
  <img src="https://raw.githubusercontent.com/airscripts/agentskill/main/assets/agentskill.png" alt="agentskill" width="1280">
</p>

---

## Table of Contents

- [What It Does](#what-it-does)
- [How It Works](#how-it-works)
- [Supported Languages](#supported-languages)
- [Generation Modes](#generation-modes)
- [Install](#install)
- [Development Checks](#development-checks)
- [Usage](#usage)
- [Repository Structure](#repository-structure)
- [Where Code Goes](#where-code-goes)
- [Developer Workflow](#developer-workflow)
- [File Ecosystem](#file-ecosystem)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [Security](#security)
- [Statistics](#statistics)
- [Support](#support)
- [License](#license)

---

## What It Does

agentskill is not a linter and not a style guide generator. It is a forensic extraction tool. It walks a repository, measures every line, reads every config file, and inspects the commit log — then synthesizes a precise behavioral spec for a code-generating agent.

The output is not advice. It is mimicry instructions.

---

## How It Works

Seven analyzers run in parallel. Each extracts one class of signal that an LLM cannot derive reliably from reading source files alone:

| Analyzer  | What it measures                                                    |
| --------- | ------------------------------------------------------------------- |
| `scan`    | Directory tree, file inventory, suggested read order                |
| `measure` | Exact indentation, line length percentiles, blank line distributions |
| `config`  | Formatter, linter, and type-checker detection with config excerpts  |
| `git`     | Commit prefixes, branch naming, merge strategy, signing             |
| `graph`   | Internal import graph, circular dependencies, most-depended modules |
| `symbols` | Symbol name extraction, naming pattern clustering, affix detection  |
| `tests`   | Test-to-source mapping, framework detection, fixture extraction     |

Analyzer output feeds directly into `AGENTS.md` synthesis. The synthesis step follows the behavioral spec in [`SYSTEM.md`](./SYSTEM.md).

> Check our latest technical article for a deeper dive:
> [Turning Repository Knowledge Into Usable Agent Context](https://dev.to/airscript/turning-repository-knowledge-into-usable-agent-context-4pe4).

---

## Supported Languages

agentskill already ships analyzer coverage and repository examples across a
wide set of languages. This matters because the tool is meant to extract
project-specific conventions from real repositories, not only from Python-only
layouts.

Current supported language set:

- Python
- TypeScript
- JavaScript
- Go
- Rust
- Java
- Kotlin
- C#
- C
- C++
- Ruby
- PHP
- Swift
- Objective-C
- Shell / Bash

The repository also includes fixture/example projects for these languages under
[`examples/`](./examples/), which act as both regression coverage and reference
shapes for multi-language analysis.

---

## Generation Modes

agentskill supports two complementary generation workflows:

### Static Generation

Use the CLI when you want deterministic output based on analyzer results plus
static source inspection.

- `agentskill analyze <repo> --pretty` for combined machine-readable analysis
- `agentskill generate <repo>` for a fresh `AGENTS.md` draft
- `agentskill update <repo>` for deterministic regeneration of an existing
  `AGENTS.md`

This is the default mode for users who want a direct tool-driven workflow
without relying on an external agent harness.

### Artificial Generation

This repository is also distributed as a dedicated skill through the repo-root
[`SKILL.md`](./SKILL.md). In that mode, an agent harness can install the skill,
follow the skill workflow, and use the same analyzers plus the richer
skill/system instructions to synthesize or update `AGENTS.md`.

In short:

- use the CLI for basic static generation,
- use the skill for agent-assisted or marketplace-installed generation.

---

## Install

```bash
pip install agsk
```

This installs the `agentskill` CLI command.

Published package is available at:

- PyPI: <https://pypi.org/project/agsk>
- ClawHub: <https://clawhub.ai/airscripts/agentskill>

For local development:

```bash
python -m pip install -e '.[dev]'
```

To enable the commit-time checks after installing the dev environment:

```bash
pre-commit install
```

### For Agents

This repository is also distributed as a standard skill with a repo-root
`SKILL.md`. Harnesses that support skill installation from a filesystem path,
git repository, or marketplace entry should install it as a normal skill and
use `SKILL.md` as the entrypoint document.

Generic install guidance for skill-aware harnesses:

- If the harness installs skills from a local path, point it at the repository
  root so it can read `SKILL.md`, `SYSTEM.md`, `references/`, and `examples/`.
- If the harness installs skills from a git repository, use this repository URL
  and keep the repo-root `SKILL.md` as the skill manifest.
- If the harness installs skills from a marketplace, use the ClawHub entry:
  <https://clawhub.ai/airscripts/agentskill>.
- If the harness only needs the CLI and not the skill manifest, install the
  PyPI package instead: <https://pypi.org/project/agsk>.

Expected skill layout:

```text
SKILL.md            # skill entrypoint and workflow
SYSTEM.md           # generation/synthesis behavioral spec
references/         # gotchas and supporting guidance
examples/           # fixture repos and reference shapes
```

After a harness installs the skill, the usual operator-facing commands remain:

```bash
agentskill analyze <repo> --pretty
agentskill generate <repo>
agentskill update <repo>
```

---

## Development Checks

Run the canonical local checks:

```bash
ruff format .
ruff check .
mypy
pytest
```

To verify formatting without rewriting files:

```bash
ruff format --check .
ruff check .
mypy
pytest
```

`mypy` is the repo's configured type-check command. Its configuration in
`pyproject.toml` covers `agentskill/`, `scripts/`, and `tests/`.

Optional commit-time hooks are available if you want them locally:

```bash
pre-commit install
pre-commit run --all-files
```

The pre-commit setup mirrors the lightweight formatting, lint, and type-check
passes. Full `pytest` runs remain part of normal local verification and CI.

---

## Usage

```bash
# Canonical installed CLI
agentskill analyze <repo> --pretty
agentskill scan <repo> --pretty
agentskill measure <repo> --lang python --pretty
agentskill config <repo> --pretty
agentskill git <repo> --pretty
agentskill graph <repo> --pretty
agentskill symbols <repo> --pretty
agentskill tests <repo> --pretty

# Write output to file
agentskill analyze <repo> --out report.json
agentskill analyze <repo> --reference ../reference-repo --pretty

# Generate AGENTS.md markdown directly
agentskill generate <repo>
agentskill generate <repo> --out AGENTS.md
agentskill generate <repo> --reference ../ref-a --reference ../ref-b
agentskill generate <repo> --interactive

# Update or create AGENTS.md in place
agentskill update <repo>
agentskill update <repo> --section testing
agentskill update <repo> --exclude-section git
agentskill update <repo> --force
agentskill update <repo> --out updated-AGENTS.md

# Retained wrapper entrypoints for operator/skill workflows
python scripts/analyze.py <repo> --pretty
python scripts/scan.py <repo> --pretty
python scripts/measure.py <repo> --lang python --pretty
python scripts/generate.py <repo>
python scripts/update.py <repo>
```

The installed `agentskill` command is the steady-state CLI surface, including
local development after an editable install. The retained `scripts/*.py`
wrappers exist for direct analyzer execution and skill/operator workflows; they
are not the primary runtime surface.

The published console entrypoint is `agentskill.main:main`. The packaged
runtime under `agentskill/` is the source of truth for subcommand behavior,
output contracts, generation, update flows, and reference handling.

### Choosing `analyze`, `generate`, or `update`

Use `analyze` when you want machine-readable JSON from all analyzers and do not
want to touch any markdown files. This is the contract-stable inspection path.

Use `generate` when you want a fresh AGENTS draft from current analyzer output.
It prints markdown to stdout by default, never merges with an existing
`AGENTS.md`, and only writes a file when you pass `--out`.

Use `update` when you already have an `AGENTS.md` and want deterministic
regeneration plus preservation of untouched manual content. It writes back to
`<repo>/AGENTS.md` by default, or to `--out` while still using the repo-local
`AGENTS.md` as merge input.

### Reference Workflow

Both `analyze` and `generate` accept repeatable `--reference` flags. References
are explicit inputs, not hidden priors.

- Every local reference must point to a directory with a readable `AGENTS.md`.
- Duplicate references are rejected instead of being silently counted twice.
- `analyze --reference` validates references but does not change the JSON output
  shape.
- `generate --reference` preserves reference order in the emitted metadata block
  so the provenance is inspectable.

### Interactive Generation

`generate --interactive` is opt-in guided gap filling. It asks a small number of
targeted questions only when important signals are missing or ambiguous, then
injects those answers into the generated markdown as explicit interactive notes.

References can reduce prompt count when they clearly provide the missing
convention. Conflicting references do not get auto-resolved; the command asks
instead of guessing.

### Update Workflow

`agentskill update <repo>` analyzes the repository, regenerates AGENTS sections,
merges them with any existing `AGENTS.md`, and writes the result back to
`<repo>/AGENTS.md` by default.

- Use `--section` to regenerate only named sections.
- Use `--exclude-section` to keep generated sections untouched.
- Missing targeted sections are inserted without rewriting unrelated manual
  sections.
- Untouched custom sections and preamble text stay in place in normal mode.
- Use `--force` for a clean-slate rebuild that drops preserved/manual sections
  and ignores preservation hints from feedback.

### Repo-Local Feedback

Incremental updates can read an optional repo-local sidecar file named
`.agentskill-feedback.json`. This file is explicit, version-controllable, and
affects only the current repository. It is not hidden memory and it is not
global learning.

```json
{
  "sections": {
    "overview": {
      "prepend_notes": [
        "Mention that deployments go through GitHub Actions."
      ]
    },
    "testing": {
      "pinned_facts": [
        "Use pytest as the canonical test runner."
      ]
    }
  },
  "preserve_sections": [
    "red lines"
  ]
}
```

Supported feedback keys are intentionally narrow by design:

- `sections.<name>.prepend_notes`
- `sections.<name>.pinned_facts`
- `preserve_sections`

In normal update mode, `preserve_sections` acts like an implicit exclusion list.
In `--force` mode, those preservation hints are ignored so the command can
produce a true clean-slate rebuild.

Use `.agentskill-feedback.json` when you want durable, repo-local regeneration
guidance that should survive future updates. Edit `AGENTS.md` directly when you
are making one-off manual notes that should remain untouched unless you
explicitly target or force-regenerate that section.

---

## Repository Structure

```
README.md           # user-facing overview and contributor workflow
AGENTS.md           # conventions for this repository itself
SYSTEM.md           # synthesis spec for generated AGENTS.md files
SKILL.md            # operational workflow used by the skill
pyproject.toml      # packaging, CLI entrypoint, tool configuration
LICENSE
docs/
  reference/        # packaged API reference for contributors
agentskill/
  main.py           # packaged CLI entry point — subcommand dispatch only
  commands/         # analyzer implementations
  lib/              # orchestration, output, update, generation helpers
  common/           # shared low-level helpers and registries
scripts/
  *.py              # thin wrappers that import packaged analyzer entrypoints
tests/              # pytest suite for package code and wrapper behavior
references/
  GOTCHAS.md        # extraction and synthesis errors to avoid
examples/
  README.md             # language fixture index for analyzer validation
  python/               # compact per-language analyzer fixtures
  javascript/
  typescript/
  go/
  rust/
  java/
  kotlin/
  csharp/
  c/
  cpp/
  ruby/
  php/
  swift/
  objectivec/
  bash/
  mixed/
  SINGLE_LANGUAGE.md   # reference output: single-language repo
  MULTI_LANGUAGE.md    # reference output: multi-language single repo
  MONOREPO.md          # reference output: monorepo with multiple services
```

---

## Where Code Goes

- Put packaged CLI and runtime code in `agentskill/`.
- Put analyzer implementations in `agentskill/commands/`.
- Put shared orchestration, generation, update, and output helpers in `agentskill/lib/`.
- Put reusable low-level helpers and registries in `agentskill/common/`.
- Keep `scripts/` limited to thin wrappers and operator-facing workflow entrypoints.
- Do not add analyzer or business logic to `scripts/`.
- Add tests in `tests/` as `test_<subject>.py`; do not colocate tests under `scripts/`.
- Keep root-level files focused on metadata, docs, and project-wide specs.

There is no separate steady-state runtime under `scripts/`, and there is no
root `cli.py` compatibility entrypoint to extend. New runtime behavior should
land in the package tree and then be exposed through `agentskill.main` if
it belongs on the public CLI.

---

## Developer Workflow

For normal use and contributor verification:

```bash
python -m pip install -e '.[dev]'
agentskill analyze <repo> --pretty
ruff format .
ruff check .
mypy
pytest
```

When you add or extend functionality:

- Add analyzer logic in `agentskill/commands/` when it maps to a command.
- Add shared helpers in `agentskill/lib/` or `agentskill/common/`, based on whether they are orchestration-level or low-level utilities.
- Wire new CLI behavior through [`agentskill/main.py`](./agentskill/main.py).
- Add a `scripts/*.py` wrapper only when direct operator or skill invocation is still useful, and keep it as a thin import-and-dispatch shim.
- Cover both packaged behavior and any retained wrapper behavior in `tests/`.

For retained wrappers:

- Use `agentskill <command> ...` as the canonical interface in docs and examples.
- Use `python scripts/<name>.py ...` only for retained thin wrappers that still exist.
- Keep `generate` and `update` wrappers thin; packaged CLI behavior must still live under `agentskill/`.

---

## File Ecosystem

Three files govern behavior. Read all three before modifying anything.

| File            | Role                                                                               |
| --------------- | ---------------------------------------------------------------------------------- |
| `SYSTEM.md`     | The canonical spec: what every section of `AGENTS.md` must contain and how to evaluate it |
| `SKILL.md`      | The operational workflow: when to invoke, what scripts to run, in what order       |
| `GOTCHAS.md`    | Extraction and synthesis errors from previous runs — read before writing           |

The public commands stay the same after refactors. The packaged runtime lives
under `agentskill/`, while `scripts/` stays intentionally small as a
wrapper and operator layer for direct analyzer entrypoints.

---

## Examples

The `examples/` directory now serves two roles:

- Compact static language fixtures under per-language subdirectories for analyzer validation.
- Reference `AGENTS.md` examples in `SINGLE_LANGUAGE.md`, `MULTI_LANGUAGE.md`, and `MONOREPO.md`.

If this skill was downloaded from ClawHub, or if `examples/` is not present in the local copy, do not consult it; skip that step to avoid execution errors.

See [`examples/README.md`](./examples/README.md) for the supported fixture set.

---

## API Reference

Static API reference for the packaged codebase lives under
[`docs/reference/`](./docs/reference/README.md):

- [`docs/reference/cli.md`](./docs/reference/cli.md) for the packaged CLI entrypoint and dispatch model
- [`docs/reference/commands.md`](./docs/reference/commands.md) for analyzer command modules
- [`docs/reference/library.md`](./docs/reference/library.md) for orchestration, generation, update, and reference helpers
- [`docs/reference/common.md`](./docs/reference/common.md) for low-level registries and filesystem helpers

The reference is contributor-oriented. It documents the packaged namespace and
extension points that matter for real maintenance work without trying to expose
every private helper as public API.

---

## Contributing

Contributions are welcome, especially in these areas:

- improving static `AGENTS.md` generation quality
- expanding analyzer depth per supported language
- tightening output contracts and regression coverage
- improving skill ergonomics for agent harnesses

Before opening a pull request, read:

- [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)

Use the repository issue and pull request templates when reporting bugs,
requesting features, or proposing changes.

---

## Security

For supported versions and vulnerability reporting guidance, see
[`SECURITY.md`](./SECURITY.md).

---

## Statistics

This is the current star history progress of the project:

[![Star History Chart](https://api.star-history.com/chart?repos=airscripts/agentskill&type=date&legend=top-left)](https://www.star-history.com/?repos=airscripts%2Fagentskill&type=date&legend=top-left)

---

## Support

Project metadata and support files available in this repository include:

- [GitHub Sponsors](https://github.com/sponsors/airscripts)
- [Ko-Fi](https://ko-fi.com/airscript)

If you want to support the project, starring, sharing, contributing fixes, and
supporting through GitHub Sponsors all help.

---

## License

MIT
