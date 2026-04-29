# agentskill

Analyze a code repository and synthesize an `AGENTS.md` that lets any agent produce code indistinguishable from the existing codebase.

---

## What It Does

agentskill is not a linter and not a style guide generator. It is a forensic extraction tool. It walks a repository, measures every line, reads every config file, and inspects the commit log — then synthesizes a precise behavioral spec for a code-generating agent.

The output is not advice. It is mimicry instructions.

---

## How It Works

Seven analysis scripts run in parallel. Each extracts one class of signal that an LLM cannot derive reliably from reading source files alone:

| Script       | What it measures                                                    |
| ------------ | ------------------------------------------------------------------- |
| `scan.py`    | Directory tree, file inventory, suggested read order                |
| `measure.py` | Exact indentation, line length percentiles, blank line distributions |
| `config.py`  | Formatter, linter, and type-checker detection with config excerpts  |
| `git.py`     | Commit prefixes, branch naming, merge strategy, signing             |
| `graph.py`   | Internal import graph, circular dependencies, most-depended modules |
| `symbols.py` | Symbol name extraction, naming pattern clustering, affix detection  |
| `tests.py`   | Test-to-source mapping, framework detection, fixture extraction     |

Script output feeds directly into `AGENTS.md` synthesis. The synthesis step follows the behavioral spec in [`SYSTEM.md`](./SYSTEM.md).

---

## Install

```bash
pip install -e .
```

For local development:

```bash
python -m pip install -e '.[dev]'
```

To enable the commit-time checks after installing the dev environment:

```bash
pre-commit install
```

---

## Development Checks

Run the baseline quality checks locally:

```bash
ruff format .
ruff check .
mypy
pytest
```

To verify without changing files:

```bash
ruff format --check .
ruff check .
mypy
pytest
```

To run the commit-time hooks across the full repository:

```bash
pre-commit run --all-files
```

The pre-commit setup runs Ruff formatting, Ruff linting, and mypy before each
commit. Full `pytest` runs remain part of normal local verification and CI,
rather than a default commit-time hook.

---

## Usage

```bash
# Run all scripts and synthesize a report
python cli.py analyze <repo> --pretty

# Run individual scripts
python cli.py scan <repo> --pretty
python cli.py measure <repo> --lang python --pretty
python cli.py config <repo> --pretty
python cli.py git <repo> --pretty
python cli.py graph <repo> --pretty
python cli.py symbols <repo> --pretty
python cli.py tests <repo> --pretty

# Write output to file
python cli.py analyze <repo> --out report.json

# Generate AGENTS.md markdown directly
python cli.py generate <repo>
python cli.py generate <repo> --out AGENTS.md

# Update or create AGENTS.md in place
python cli.py update <repo>
python cli.py update <repo> --section testing
python cli.py update <repo> --exclude-section git
python cli.py update <repo> --force
python cli.py update <repo> --out updated-AGENTS.md

# Run a script directly
python scripts/scan.py <repo> --pretty
```

### Update Workflow

`python cli.py update <repo>` analyzes the repository, regenerates AGENTS sections,
merges them with any existing `AGENTS.md`, and writes the result back to
`<repo>/AGENTS.md` by default. Use `--section` to limit regeneration to one or
more named sections, `--exclude-section` to keep specific generated sections
untouched, and `--force` for a clean-slate rebuild that drops old custom
sections instead of preserving them.

### Generate Workflow

`python cli.py generate <repo>` analyzes the repository and prints a fresh
generated `AGENTS.md` document to stdout. Use `--out` to write that markdown to
an explicit file path. Unlike `update`, `generate` does not merge with an
existing `AGENTS.md` and does not write back to `<repo>/AGENTS.md` unless you
explicitly choose an output path.

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

Supported feedback keys are intentionally narrow in `0.7.0`:

- `sections.<name>.prepend_notes`
- `sections.<name>.pinned_facts`
- `preserve_sections`

In normal update mode, `preserve_sections` acts like an implicit exclusion list.
In `--force` mode, those preservation hints are ignored so the command can
produce a true clean-slate rebuild.

---

## Repository Structure

```
cli.py              # unified entry point — subcommand dispatch only
pyproject.toml      # build metadata and entry point declaration
SYSTEM.md           # behavioral spec for AGENTS.md generation — never modify
SKILL.md            # operational workflow — never modify
AGENTS.md           # conventions for this repo itself
scripts/
  commands/
    scan.py         # directory tree walk, file inventory, read order
    measure.py      # indentation, line lengths, blank lines, trailing whitespace
    config.py       # formatter/linter/type-checker detection from config files
    git.py          # commit log parsing, branch analysis, merge strategy
    graph.py        # internal import graph, cycle detection, monorepo detection
    symbols.py      # symbol name extraction and naming pattern clustering
    tests.py        # test-to-source mapping, framework detection, fixture extraction
  lib/
    runner.py       # aggregate analyzer orchestration for `analyze`
    output.py       # shared JSON output helpers for CLI and scripts
  common/
    constants.py    # shared repository-walk constants
    fs.py           # shared low-level filesystem helpers
  scan.py           # thin wrapper for direct script execution
  measure.py        # thin wrapper for direct script execution
  config.py         # thin wrapper for direct script execution
  git.py            # thin wrapper for direct script execution
  graph.py          # thin wrapper for direct script execution
  symbols.py        # thin wrapper for direct script execution
  tests.py          # thin wrapper for direct script execution
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

## File Ecosystem

Three files govern behavior. Read all three before modifying anything.

| File            | Role                                                                               |
| --------------- | ---------------------------------------------------------------------------------- |
| `SYSTEM.md`     | The canonical spec: what every section of `AGENTS.md` must contain and how to evaluate it |
| `SKILL.md`      | The operational workflow: when to invoke, what scripts to run, in what order       |
| `GOTCHAS.md`    | Extraction and synthesis errors from previous runs — read before writing           |

The public commands stay the same after refactors. Internal code is organized by technical role: analyzers in `scripts/commands/`, shared CLI infrastructure in `scripts/lib/`, and low-level helpers in `scripts/common/`.

---

## Examples

The `examples/` directory now serves two roles:

- Compact static language fixtures under per-language subdirectories for analyzer validation.
- Reference `AGENTS.md` examples in `SINGLE_LANGUAGE.md`, `MULTI_LANGUAGE.md`, and `MONOREPO.md`.

If this skill was downloaded from ClawHub, or if `examples/` is not present in the local copy, do not consult it; skip that step to avoid execution errors.

See [`examples/README.md`](./examples/README.md) for the supported fixture set.

---

## License

MIT
