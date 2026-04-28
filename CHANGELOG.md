# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0] - 2026-04-28

### Added

- `scripts/lib/agents_document.py` — parsing and serialization for sectioned AGENTS.md documents
- `AgentsSection` / `AgentsDocument` — frozen dataclasses representing headings, body text, and raw lines
- `parse_agents_document()` — ATX heading-based section extraction preserving blank lines and structure
- `build_section()` / `serialize_document()` — deterministic round-trip serialization
- `add_or_replace_section()` / `remove_section()` / `get_section()` — mutation helpers with normalized name lookup
- `normalize_section_name()` — case-insensitive, whitespace-normalized section name matching
- `scripts/lib/update_merge.py` — merge helpers for incremental AGENTS.md updates
- `MergePlan` — declarative merge plan with per-section actions (add, replace, preserve, append, prepend)
- `plan_merge()` — diff existing document sections against new analyzer output, producing a merge plan
- `apply_merge()` — execute a merge plan against an `AgentsDocument`, returning the updated document
- Section-level prepend/append with feedback-sourced content
- `scripts/lib/update_feedback.py` — repo-local feedback loading for AGENTS.md update workflows
- `FeedbackEntry` / `FeedbackFile` — structured models for `.agentskill-feedback.json`
- `load_feedback()` — load and validate feedback file from a repository root
- `apply_feedback()` — merge feedback entries into a merge plan as prepend notes and pinned facts
- `SUPPORTED_SECTION_FEEDBACK_KEYS` — supported feedback instruction types
- `scripts/lib/update_runner.py` — internal workflow for updating AGENTS.md from current analyzer output
- `update_agents()` — end-to-end update flow: validate repo, run analyzers, diff sections, apply feedback, serialize
- Section filtering with `--only` flag (run specific analyzers)
- Custom output path with `--out` flag
- Configurable `--mode` (overwrite, merge-new, merge-all)
- `cli.py` — `update` subcommand for updating or creating AGENTS.md
- `PLANNER.md` — release planner system prompt for generating implementation-ready PR briefs

### Changed

- CLI now exposes `update` command alongside existing `analyze` and individual analyzer commands
- README updated with update workflow documentation

## [0.6.0] - 2026-04-28

### Added

- Shared language registry — `scripts/common/languages.py` with `LanguageSpec`, 15 languages, 6 helper functions
- `language_for_path()`, `language_for_extension()`, `language_by_id()`, `is_test_path()`, `is_supported_language()`, `all_language_specs()`
- TypeScript and JavaScript parity across graph, symbols, and tests analyzers
- Comment stripping for JS/TS sources
- ES import and re-export extraction with line numbers
- CommonJS `require()` extraction
- Local relative import resolution with candidate extensions (.ts/.tsx/.js/.jsx/.mjs/.cjs + index variants)
- TypeScript symbol extraction: functions, classes, interfaces, type aliases, arrow functions, constants with exported flag
- TypeScript test mapping: `.test.ts`/`.spec.ts` to source files
- TypeScript framework detection from package.json (jest, vitest, mocha)
- `.cjs` extension support across analyzers
- Go and Rust parity across graph, symbols, and tests analyzers
- Go module path detection from `go.mod`
- Go import extraction with line numbers (single imports and import blocks)
- Go package boundary detection by directory
- Go symbol extraction: functions, methods, structs, interfaces, type aliases, constants, variables
- Go test mapping: `*_test.go` to source files
- Java and Kotlin support across analyzers and tests
- C#, C, and C++ support across analyzers and tests
- Ruby, PHP, and Bash support across analyzers and tests
- Swift and Objective-C support across analyzers and tests
- Config analyzer with multi-language config detection
- Language-specific example repositories under `examples/`
- Comprehensive test coverage: 345 tests passing

### Changed

- `scan` command migrated to use `language_for_path()` from shared registry
- `measure` command migrated to use `language_for_extension()` from shared registry
- `graph` analyzer: Go edges now include accurate line numbers
- `graph` analyzer: added Rust module/use graph with `mod` and `use` statement extraction
- `graph` analyzer: added JavaScript file collection with `.cjs` extension
- `symbols` analyzer: Go extraction enhanced with methods, interfaces, type aliases, and variables
- `symbols` analyzer: added Rust symbol extraction with structs, enums, traits, impls, constants, statics
- `tests` analyzer: added Go and Rust test detection and mapping
- `tests` analyzer: added Java, Kotlin, C#, C, C++, Ruby, PHP, Bash, Swift, Objective-C framework detection

### Added

- `scripts/lib/references.py` — reference source, document, load result, and metadata models
- `load_local_reference()` / `load_local_references()` — load AGENTS.md from local directories
- `load_remote_reference()` / `load_remote_references()` — load AGENTS.md from remote repos via shallow clone
- `_run_git()` — subprocess helper with 60s timeout and error capture
- `scripts/lib/reference_adaptation.py` — reference adaptation engine with heuristic classification
- `ReferenceSection`, `AdaptedConvention`, `ReferenceAdaptationResult` — frozen dataclasses for section splitting and convention classification
- `split_markdown_sections()` — heading-based Markdown section extraction
- `adapt_reference()` / `adapt_references()` — classify conventions as applicable, mismatched, uncertain, or ignored
- Category detection with priority ordering: directory_structure, testing, formatter, linter, type_checker, git
- Language/tool extraction and target analysis comparison
- Directory path matching against scan tree
- `scripts/lib/reference_questions.py` — gap detection and targeted question generation
- `ReferenceQuestion` model with section, question, reason, category, source, blocking, options
- `generate_reference_questions()` — produce targeted questions from uncertain and mismatched conventions
- Selective question generation: irrelevant mismatches filtered, ecosystem-aware relevance checks
- Conflict detection across multiple references proposing different conventions
- Question deduplication and deterministic ordering
- `scripts/lib/reference_initialization.py` — empty-project initialization from references
- `is_empty_target()` — detect empty or near-empty target repositories
- `build_reference_metadata()` — build deterministic metadata from loaded documents
- `render_reference_metadata_block()` — render metadata as Markdown HTML comment with JSON
- `ReferenceInitializationResult` — structured result with adapted references, questions, metadata, warnings
- `initialize_from_references()` — end-to-end initialization flow
- `successful_reference_documents()` — filter load results to successful documents
- `AGENTSKILL_VERSION` constant

## [0.4.0] - 2026-04-27

### Added

- `scripts/lib/parsers.py` — shared TOML and YAML parser loading with optional dependency fallback
- `load_toml` / `load_yaml` — strict parsers that raise `ParserUnavailableError` when deps are missing
- `load_toml_safe` / `load_yaml_safe` — graceful parsers returning `{}` on any error
- Comprehensive config parsing tests with real-world fixtures for Python, JS, Go, and Rust

### Changed

- Replaced custom TOML parsing in `config.py` with `tomllib` / `tomli` via shared parser
- Replaced custom YAML parsing in `config.py` with `PyYAML` `safe_load` via shared parser
- Moved `tomli` and `PyYAML` to optional `[parsers]` dependency group

### Removed

- `_parse_toml`, `_parse_toml_value`, `_split_toml_array` — replaced by real TOML parser
- `_parse_yaml_simple`, `_yaml_scalar` — replaced by real YAML parser

## [0.3.0] - 2026-04-26

### Added

- Logging infrastructure — `scripts/lib/logging_utils.py` with configurable log level and exception capture
- Output path validation — `--out` paths are validated; parent directories are created automatically
- Per-analyzer timeout logging — runner logs when an analyzer exceeds its deadline
- `write_output` exception handling — captures and logs JSON serialization errors

### Changed

- `_run` in `git.py` now returns stderr alongside stdout, and logs command failures
- `run_all` logs per-analyzer failures with tracebacks instead of silently swallowing them

## [0.2.0] - 2026-04-26

### Added

- GitHub Actions CI workflows — build, test, verify, and main branch checks
- `tomli` runtime dependency for Python < 3.11 TOML support

### Changed

- Bumped minimum Python version to 3.10
- Switched build backend to `setuptools.build_meta`
- Expanded `py-modules` to include `cli` for correct CLI invocation

### Fixed

- Import order error flagged by ruff
- CLI invocation error caused by missing `py-modules` declaration

## [0.1.0] - 2026-04-26

### Added

- Initial release of agentskill
- `analyze` command — run all analyzers and synthesize an `AGENTS.md` report
- `scan` analyzer — directory tree mapping, file inventory, suggested read order
- `measure` analyzer — exact indentation, line length percentiles, blank line distributions
- `config` analyzer — formatter, linter, and type-checker detection with config excerpts
- `git` analyzer — commit prefixes, branch naming, merge strategy, and signing detection
- `graph` analyzer — internal import graph, circular dependencies, most-depended modules
- `symbols` analyzer — symbol name extraction, naming pattern clustering, affix detection
- `tests` analyzer — test-to-source mapping, framework detection, fixture extraction
- Parallel analyzer execution via `ThreadPoolExecutor`
- Pretty-printed and machine-readable JSON output modes (`--pretty`, `--json`)
- `--out` flag to write report to a file
- `--language` flag to override auto-detected language
- Language-agnostic analysis engine supporting Python, JavaScript/TypeScript, Rust, Go, and others
- Multiple output example formats: `SINGLE_LANGUAGE.md`, `MULTI_LANGUAGE.md`, `MONOREPO.md`
- `SYSTEM.md` — behavioral spec for the synthesis step
- `SKILL.md` — OpenClaw AgentSkill manifest
- `AGENTS.md` — self-documented analysis rules
- Full test suite with pytest covering all modules
- `pyproject.toml` with `project.scripts` entry points
- Development dependencies: `ruff`, `pytest`
