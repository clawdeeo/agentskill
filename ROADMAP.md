# agentskill — Version Roadmap to 1.0.0

This roadmap maps the path from the current release to a stable 1.0.0. Each version bundles related work and introduces new features alongside quality improvements. Items from the previous roadmap are merged where they fit and dropped if superseded by newer decisions.

---

## 0.2.0 — Tooling & Foundation

**Theme:** solidify the development workflow and add basic safety guards.

- Expand ruff lint rules (`B`, `W`, `C4`, `SIM`, `UP`, `N`) and fix warnings
- Add `mypy` to dev dependencies and configure in `pyproject.toml`
- Add pre-commit hooks mirroring CI checks
- Centralize the directory-walk helper in `scripts/common/` (`walk_repo`)
- Add per-analyzer timeouts in `run_all` (e.g. 60 s)
- Add file-size and file-count limits (`MAX_FILES_TO_PARSE`, `MAX_FILE_BYTES`)
- Centralize repo-path validation (`validate_repo(path) -> Path`)

---

## 0.3.0 — Observability & Error Handling

**Theme:** make failures visible and actionable instead of silent.

- Introduce a lightweight logger (`logging.getLogger("agentskill")`)
- Surface subprocess stderr from `_run` in `git.py`
- Log per-analyzer failures in aggregate mode with tracebacks
- Validate `--out` paths (refuse absolute or escaping paths)
- Ensure parent directories exist for `--out`
- Remove dead/duplicate parser code once real parsers land (moved forward)

---

## 0.4.0 — Parser Robustness

**Theme:** replace hand-rolled parsers with correct ones.

- Replace custom TOML parser with `tomli`
- Replace custom YAML parser with `PyYAML`
- Backfill unit tests for config extraction with real parsers
- Make `tomli` and `PyYAML` optional runtime dependencies with graceful degradation

---

## 0.5.0 — Reference Repositories

**Theme:** generate AGENTS.md by learning from existing repos.

- Pull AGENTS.md from local repositories as reference material
- Pull AGENTS.md from remote repositories via shallow clone or raw fetch
- Adapt reference conventions to the target project's scope
- Ask targeted questions when gaps exist between reference and target
- Support empty-folder / new-project initialization from reference alone
- Store reference sources and version in generated AGENTS.md metadata

---

## 0.6.0 — Language Expansion

**Theme:** reach parity across the most widely-used languages.

- TypeScript / JavaScript — full symbol extraction, import graph, test mapping
- Go — full symbol extraction, module graph, package boundary detection
- Rust — Cargo.toml parsing, module graph, symbol extraction
- Java — Maven/Gradle detection, package graph, symbol extraction
- C# — .csproj detection, namespace graph, symbol extraction
- C / C++ — CMake/Makefile detection, header/include graph, symbol extraction
- Ruby — Gemfile detection, require graph, RSpec/minitest mapping
- PHP — Composer detection, namespace graph, PHPUnit mapping
- Swift / Objective-C — Package.swift / CocoaPods detection, module graph
- Kotlin — Gradle detection, package graph, symbol extraction
- Shell / Bash — script detection, sourcing graph
- Ensure all analyzers (`scan`, `measure`, `graph`, `symbols`, `tests`) handle every supported language
- Update examples in `examples/` for each supported language

---

## 0.7.0 — Incremental Updates

**Theme:** regenerate without losing user edits or context.

- Diff-based merge when an existing AGENTS.md is present
- Per-section regeneration flags (`--section <name>`, `--exclude-section <name>`)
- Full-regeneration mode (`--force`) when the user wants a clean slate
- Feedback incorporation workflow: accept user corrections and bias future output
- Preserve manual user edits in sections not being regenerated
- Add `agentskill update` command as the incremental entry point

---

## 0.8.0 — Test Backfill & DRY

**Theme:** pay down technical debt and raise coverage.

- DRY the `main()` boilerplate in every command (`lib.cli_entrypoint` helper)
- DRY extension/language mappings into `scripts/common/constants.py`
- Remove redundant `sys.path` manipulation from `test_support.py`
- Test `config.py` internals with temporary config files
- Test `measure.py` edge cases (empty files, mixed tabs/spaces, non-Python)
- Test `scan.py` edge cases (empty repo, zero-match filter, symlinks)
- Test `symbols.py` per-language extractors
- Test `graph.py` for TS/Go import resolution
- Assert exact error payloads across all analyzers

---

## 0.9.0 — Schema Validation & CLI Polish

**Theme:** guarantee output shape and improve the user interface.

- Lightweight output-schema validation (dataclasses or Pydantic)
- Snapshot / contract tests for JSON keys against known sample repos
- Add `agentskill generate` command — direct AGENTS.md generation from analyzed repo
- Interactive mode for answering targeted questions inline
- `--reference` flag on `analyze` and `generate` for passing reference repos
- `--interactive` flag for guided gap-filling workflow

---

## 1.0.0 — Stable Release

**Theme:** a reliable, documented, multi-language tool ready for daily use.

- All features from 0.9.0 complete and tested
- Stable CLI contract — no breaking changes without major version bump
- Full documentation: README, examples, API reference
- Multi-language support verified across Python, TypeScript/JavaScript, Go, Rust, Java, C#, C/C++, Ruby, PHP, Swift/Objective-C, Kotlin, and Shell/Bash
- Reference repository workflow polished and documented
- Incremental update workflow polished and documented
- Release on PyPI with `pip install agentskill`

---

## Legend

| Symbol | Meaning                                  |
| ------ | ---------------------------------------- |
| (moved)| Carried forward from the previous roadmap |
| (new)  | Feature originating from project discussion |
