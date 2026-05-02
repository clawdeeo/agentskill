---
name: agentskill
description: Analyze a code repository and synthesize an AGENTS.md.
---

# SKILL.md — agentskill

> **Operational spec for agentskill.**
> This file governs _when_ to invoke, _what_ to run, and _in what order_.
> For _how_ to generate `AGENTS.md`, read [`SYSTEM.md`](./SYSTEM.md) — it is the behavioral bible.
> These two files are complementary. Neither is sufficient alone.

---

## Purpose

Analyze one or more code repositories. Extract exact coding conventions. Synthesize a precise, forensic `AGENTS.md` that allows any agent to produce code indistinguishable from the existing codebase.

---

## Trigger Phrases

Invoke this skill when the user says any of the following — or a close paraphrase:

- _"Generate an AGENTS.md"_
- _"Extract my coding style"_
- _"Analyze my repo for conventions"_
- _"Create a style guide from my code"_
- _"Update my AGENTS.md"_
- _"My agent doesn't write code the way I do — fix it"_

Do **not** invoke this skill for general code review, refactoring, or style advice not tied to generating `AGENTS.md`.

---

## File Ecosystem

| File                     | Role                                                                                   |
| ------------------------ | -------------------------------------------------------------------------------------- |
| `SKILL.md` _(this file)_ | Operational spec: workflow, scripts, fallbacks, uncertainty handling                   |
| `SYSTEM.md`              | Behavioral spec: what to generate, section by section, and how to evaluate it          |
| `references/GOTCHAS.md`  | Extraction errors to avoid; update this file whenever a new failure mode is discovered |
| `examples/`              | Analyzer fixtures plus reference `AGENTS.md` examples; consult when handling an unfamiliar repo shape |

> **Maintenance rule:** If SYSTEM.md and SKILL.md ever contradict each other, SYSTEM.md wins. Fix SKILL.md to match.

> **Availability rule:** If this skill was downloaded from ClawHub, or if `examples/` is unavailable locally, do not consult `examples/`; skip it to avoid execution errors.

---

## Workflow

Execute these steps **in order**. Do not skip steps. Do not reorder steps.

---

### Step 1 — Collect

Ask the user for repo path(s). Accept one or more. Confirm before proceeding.

```
Provide the path(s) to your repository or repositories.
One path per repo. Multiple repos are supported.
```

If the user provides a monorepo, note this explicitly — steps 3 and 4 of SYSTEM.md apply.

---

### Step 2 — Scan

Run the scan script to get the directory tree and source file inventory.

```bash
python scripts/scan.py <repo>
```

**Outputs:** annotated directory tree, source files grouped by language with line counts.

**Use the output to decide what to read** — largest files first, entry points and core modules before tests.

> **If the script fails:** Manually walk the directory tree using available file tools. Note in your working context that the scan was manual — this affects reliability of the file inventory for large repos.

---

### Step 3 — Measure

Run the measurement script to get exact formatting metrics.

```bash
python scripts/measure.py <repo>
python scripts/measure.py <repo> --lang python   # single language
```

**Outputs:** per-language indentation unit and size, line length percentiles (p95 and p99), blank line distributions between top-level definitions and between methods, trailing newline convention.

> **If the script fails:** Proceed without exact measurements. Mark all formatting measurements in the generated `AGENTS.md` as `[tentative]` and note that manual inspection was used. Do not estimate percentiles — state the observable range instead.

---

### Step 4 — Config

Run the config script to detect formatters, linters, and their exact settings.

```bash
python scripts/config.py <repo>
```

**Outputs:** per-language tool detection with relevant config excerpts — `[tool.black]`, `[tool.ruff]`, `[tool.mypy]`, `tsconfig.json`, `.prettierrc`, `.editorconfig`, and equivalents.

> **If the script fails:** Read config files directly from disk. Prioritize: `pyproject.toml`, `package.json`, `.editorconfig`, any `.*rc` files at the repo root. Do not guess what a formatter enforces — only document what you can read from config.

---

### Step 5 — Read SYSTEM.md

**Read [`SYSTEM.md`](./SYSTEM.md) fully before writing a single line of `AGENTS.md`.**

Do not rely on memory of previous runs. Read it fresh every time.

---

### Step 6 — Read Source Files

Read actual source files directly. Use the file inventory from Step 2 to choose what to read.

**Minimum per language before drafting any section:**

| Priority | What to read                                                            |
| -------- | ----------------------------------------------------------------------- |
| 1st      | Entry point and CLI files                                               |
| 2nd      | Core logic modules (largest non-test files)                             |
| 3rd      | At least one test file                                                  |
| 4th      | Package manifest (`pyproject.toml`, `Cargo.toml`, `package.json`, etc.) |
| 5th      | At least one utility or helper module                                   |

**Minimum count:** 3–5 files per language. For monorepos, 3–5 files per service.

Do not begin drafting until this step is complete.

---

### Step 7 — Check GOTCHAS.md

Read [`references/GOTCHAS.md`](./references/GOTCHAS.md) before drafting.

This file contains extraction and synthesis errors discovered from previous agentskill runs — false patterns, formatter assumption traps, monorepo boundary mistakes, and section omissions.

---

### Step 8 — Consult Examples

Read the relevant file in [`examples/`](./examples/) if you are handling an unfamiliar repo shape.

If this skill was downloaded from ClawHub, or if `examples/` is unavailable locally, skip this step to avoid execution errors.

| Scenario                        | File to consult               |
| ------------------------------- | ----------------------------- |
| Standard single-language repo   | `examples/SINGLE_LANGUAGE.md` |
| Monorepo with multiple services | `examples/MONOREPO.md`        |
| Multi-language single repo      | `examples/MULTI_LANGUAGE.md`  |

> **If no relevant example exists:** Proceed without one. Do not consult an example from a different repo shape — it will introduce structural assumptions that don't apply.

---

### Step 9 — Synthesize

Follow SYSTEM.md **section by section**, in the exact order specified.

**Source of truth per data type:**

| Data type                                   | Source                                 |
| ------------------------------------------- | -------------------------------------- |
| Line length, indentation, blank line counts | Script output from Step 3              |
| Formatter and linter settings               | Script output from Step 4              |
| Naming conventions                          | Direct source file reads (Step 6)      |
| Error handling patterns                     | Direct source file reads (Step 6)      |
| Import ordering                             | Direct source file reads (Step 6)      |
| Comment and docstring style                 | Direct source file reads (Step 6)      |
| Test patterns                               | Direct source file reads (Step 6)      |
| Directory structure                         | Script output from Step 2              |
| Git conventions                             | `.git/` config + commit log inspection |

For qualitative sections such as naming, imports, error handling, comments, and testing, enrich from static source evidence first: concrete rules plus real snippets. Use analyzer output to find candidate files, not as the section body.

Apply the **Mimicry Test** from SYSTEM.md to each section before moving to the next. Do not batch-test at the end.

---

### Step 10 — Handle Uncertainty

When you are uncertain about a pattern mid-synthesis, apply this decision tree — do not silently guess:

```
Is the pattern supported by fewer than 3 examples?
  YES → Mark the rule [tentative] and continue.

Is there genuine inconsistency with no dominant pattern?
  YES → State the inconsistency explicitly. Do not invent a rule.

Is an entire section unmeasurable (e.g. script failed, files unreadable)?
  YES → Surface this to the user before writing that section.
        Ask: "I couldn't reliably extract [section].
        Do you want me to skip it, mark it tentative, or provide the data manually?"

Is the uncertainty minor and isolated to one sub-rule?
  YES → Mark [tentative], continue, note it in the draft summary.
```

**Never silently guess. Never invent a rule. Never omit a section without telling the user.**

---

### Step 11 — Write

Write the final `AGENTS.md` to the repo root.

**If this is a new file:** Write directly.

**If an existing `AGENTS.md` is present:**

1. Read the existing file first.
2. Present a diff-style summary of what will change and why.
3. Ask for confirmation before overwriting.

After writing, output a brief summary:

```
AGENTS.md written.

Sections completed:    15 / 15
Tentative rules:       [list them, or "none"]
Sections with gaps:    [list them, or "none"]
Recommended follow-up: [e.g. "Run measure.py — line length marked tentative"]
```

---

## Why Seven Scripts?

The scripts handle exactly and only what an LLM cannot do reliably from reading source files.

| Script       | Why it cannot be skipped                                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `scan.py`    | Large repos exceed the context window; without a file inventory the agent reads arbitrarily, missing dominant patterns in unread files      |
| `measure.py` | 95th-percentile line length requires counting every line across every file — estimation from reading samples is structurally inaccurate     |
| `config.py`  | Formatter config files are ground truth; inferring what a formatter enforces from its output is unreliable and will drift as config changes |
| `git.py`     | Commit log and branch history require `git log` access; source files alone do not reveal prefix conventions or merge strategy               |
| `graph.py`   | Import graph cycle detection and monorepo boundary identification require traversing all files simultaneously, not reading them one by one  |
| `symbols.py` | Codebase-specific affix detection requires counting patterns across every identifier in the repo — impractical to do by reading samples     |
| `tests.py`   | Test-to-source mapping and framework detection require walking the full file tree; sampling misses coverage gaps and naming inconsistencies |

Everything else — error handling patterns, comment style, docstring format, architectural rules — comes from reading source files directly. Do not run scripts for things you can read.

---

## Scripts Quick Reference

All scripts require Python stdlib only. No installation needed beyond `pip install -e .`.

```bash
# Aggregate analyzer wrapper
python scripts/analyze.py <repo>

# Directory tree and file inventory
python scripts/scan.py <repo>

# Formatting metrics (indentation, line length, blank lines, newlines)
python scripts/measure.py <repo>
python scripts/measure.py <repo> --lang python

# Formatter and linter detection with config excerpts
python scripts/config.py <repo>

# Commit log, branch naming, and merge strategy
python scripts/git.py <repo>

# Internal import graph, cycle detection, monorepo boundaries
python scripts/graph.py <repo>

# Symbol name extraction and codebase-specific affix detection
python scripts/symbols.py <repo>

# Test-to-source mapping, framework detection, fixture extraction
python scripts/tests.py <repo>

# Fresh AGENTS.md draft
python scripts/generate.py <repo>

# Update or create AGENTS.md in place
python scripts/update.py <repo>

# Run all seven analyzers in parallel and merge output
agentskill analyze <repo> --pretty
```

All scripts output JSON to stdout. Pass `--pretty` for human-readable output. Pass `--out <file>` to write to disk.

---

## Uncertainty Reference

| Situation                                  | Action                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------- |
| Fewer than 3 examples for a rule           | Mark `[tentative]`                                                        |
| Genuine inconsistency, no dominant pattern | State the inconsistency; do not invent a rule                             |
| Script failed, measurement unavailable     | Mark affected measurements `[tentative]`; note manual inspection was used |
| Entire section unmeasurable                | Surface to user; ask before proceeding                                    |
| Existing `AGENTS.md` present               | Diff and confirm before overwriting                                       |
| No matching example in `examples/`         | Skip Step 8; do not use a mismatched example                              |

---

## Principles

> These are reminders, not the full spec. The full spec is in SYSTEM.md.

- **Extract, don't guess.** Every rule must be grounded in observed code.
- **Snippets are the spec.** Every non-trivial rule needs a real code snippet.
- **Static enrichment beats metric summaries.** Qualitative sections should read like observed code behavior, not analyzer tallies.
- **3 examples minimum.** Fewer → `[tentative]`. Inconsistency → state it.
- **Scope every rule.** Repo-wide vs. per-language vs. per-service — always explicit.
- **No statistics in output.** No counts, percentages, or confidence levels in `AGENTS.md`.
- **Mimicry test per section.** Apply it before moving on, not at the end.
- **Uncertainty surfaces up.** Never silently guess. Never silently omit.

---

_Update `references/GOTCHAS.md` after every run where a new failure mode is discovered._
_Update this file whenever the workflow changes._
_If this file and SYSTEM.md contradict — SYSTEM.md wins._
