# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
