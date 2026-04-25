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

# Run a script directly
python scripts/scan.py <repo> --pretty
```

---

## Repository Structure

```
cli.py              # unified entry point — subcommand dispatch only
pyproject.toml      # build metadata and entry point declaration
SYSTEM.md           # behavioral spec for AGENTS.md generation — never modify
SKILL.md            # operational workflow — never modify
AGENTS.md           # conventions for this repo itself
scripts/
  scan.py           # directory tree walk, file inventory, read order
  measure.py        # indentation, line lengths, blank lines, trailing whitespace
  config.py         # formatter/linter/type-checker detection from config files
  git.py            # commit log parsing, branch analysis, merge strategy
  graph.py          # internal import graph, cycle detection, monorepo detection
  symbols.py        # symbol name extraction and naming pattern clustering
  tests.py          # test-to-source mapping, framework detection, fixture extraction
references/
  GOTCHAS.md        # extraction and synthesis errors to avoid
examples/
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

---

## Examples

The `examples/` directory contains three reference `AGENTS.md` files, each representing a distinct repo shape:

- **`SINGLE_LANGUAGE.md`** — a Go HTTP service with no external tooling
- **`MULTI_LANGUAGE.md`** — a Python/TypeScript project with shared conventions
- **`MONOREPO.md`** — a multi-service monorepo with per-service sections

Consult the relevant example before handling an unfamiliar repo shape.

---

## License

MIT
