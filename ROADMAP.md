# agentskill — Code Quality Roadmap

This roadmap captures the most impactful robustness and code-quality improvements for the agentskill CLI. Items are grouped by theme and ordered from quick wins to longer refactors.

## Phase 1 — Tooling & CI (Quick Wins)

1. **Expand Ruff lint rules**
   - Current select list (`E4`, `E7`, `E9`, `F`, `I`) is minimal.
   - Add `B` (flake8-bugbear), `W`, `C4` (comprehensions), `SIM` (simplification), `UP` (pyupgrade), and `N` (pep8-naming).
   - Run a full pass over the repo and fix any new warnings.

2. **Add static type-checking gate**
   - The codebase is fully annotated but has no type-checker configured.
   - Add `mypy` (or `pyright`) to `project.optional-dependencies.dev`, configure in `pyproject.toml`, and run in CI.

3. **Add a GitHub Actions workflow**
   - Create `.github/workflows/check.yml` running:
     1. `ruff format --check .`
     2. `ruff check .`
     3. `mypy scripts/ cli.py`
     4. `pytest --cov`
   - Block merges on failure.

4. **Add pre-commit hooks (optional)**
   - `.pre-commit-config.yaml` mirroring the CI checks so local errors are caught before push.

## Phase 2 — Error Handling & Observability

5. **Introduce a lightweight logger**
   - Add a module-level `logging.getLogger("agentskill")` helper in `scripts/lib/`.
   - Replace silent `except Exception:` fallbacks with `log.warning` / `log.exception` so users can opt into visibility with `-v`.

6. **Surface subprocess stderr**
   - `_run` in `git.py` discards stderr. Include stderr in the error payload or log it so git failures are actionable.

7. **Log per-analyzer failures in aggregate mode**
   - `run_all` swallows analyzer tracebacks. Even though the CLI returns structured errors, log the traceback when an analyzer crashes to aid debugging.

## Phase 3 — Input Safety & Resource Guards

8. **Add file-size and file-count limits**
   - Add `MAX_FILES_TO_PARSE` and `MAX_FILE_BYTES` constants.
   - Skip oversized files with a logged warning rather than crashing or hanging on huge blobs.
   - Apply limits consistently during `os.walk` in every analyzer.

9. **Validate `--out` paths**
   - `write_output` accepts any path string. Add a guard refusing absolute paths or paths pointing outside the current directory unless forced, and ensure parent directories exist.

10. **Add per-analyzer timeouts in `run_all`**
    - `ThreadPoolExecutor` waits indefinitely on `future.result()`. Add a per-task timeout (e.g., 60 s) so a hung git log or massive AST walk cannot block the whole `analyze` command.

11. **Centralize the directory-walk helper**
    - `os.walk` with `dirs[:] = [d for d in dirs if not should_skip_dir(d)]` is repeated in every analyzer.
    - Move a `walk_repo(repo, extensions, max_files)` generator into `scripts/common/` to reduce drift and make it easier to inject size/count limits.

## Phase 4 — Replace Fragile Hand-Rolled Parsers

12. **Replace custom TOML parser with `tomli`**
    - `_parse_toml` in `config.py` does not handle inline tables, dotted keys, multi-line strings, or comments robustly.
    - Project targets `>=3.9`; add `tomli` to runtime dependencies and use it instead.

13. **Replace custom YAML parser with `PyYAML`**
    - `_parse_yaml_simple` fails on lists inside mappings, quoted keys, and multi-line values.
    - Add `PyYAML` to runtime dependencies (or make it optional with a graceful fallback).

14. **Remove dead/duplicate parser code**
    - After swapping in real parsers, delete `_parse_toml`, `_parse_yaml_simple`, `_split_toml_array`, etc., and backfill unit tests that assert correct extraction of real configs.

## Phase 5 — Backfill Tests

15. **Test `config.py` internals**
    - Add tests for TOML/YAML/JSON/INI extraction once real parsers are in place.
    - Cover `_detect_python_formatter`, `_detect_python_linter`, and `_detect_python_type_checker` with temporary config files.

16. **Test `measure.py` edge cases**
    - Non-Python blank-line measurement, indentation heuristics, mixed tabs/spaces, and empty files.

17. **Test `scan.py` edge cases**
    - Empty repo, `lang_filter` that yields zero files, symlink handling.

18. **Test `symbols.py` per-language extractors**
    - TypeScript/JavaScript symbol extraction, Go symbol extraction, affix deduplication logic.

19. **Test `graph.py` for TS/Go**
    - Currently only Python cycles and edges are tested. Add dedicated tests for TypeScript relative-import resolution and Go module-prefix extraction.

20. **Assert exact error payloads**
    - The convention is `{"error": ..., "script": ...}` — add focused tests that hit every `not repo.exists()`, `not a git repository`, and parse-error branch.

## Phase 6 — Refactoring & DRY

21. **DRY the `main()` boilerplate in every command**
    - Every `scripts/commands/*.py` has an identical argparse + `run_and_output` wrapper.
    - Extract a small `lib.cli_entrypoint(name, fn, supports_lang=False)` helper.

22. **DRY extension/language mappings**
    - `SKIP_EXTENSIONS` and `EXTENSIONS` appear in `scan.py` and are partially duplicated in `measure.py`.
    - Move canonical mappings to `scripts/common/constants.py` and import everywhere.

23. **Remove redundant `sys.path` manipulation**
    - `tests/test_support.py` duplicates the bootstrap already in `tests/conftest.py`.
    - Remove the duplication from `test_support.py`.

## Phase 7 — Contracts & Validation

24. **Add lightweight output-schema validation**
    - The JSON is consumed by an external synthesizer. Introduce Pydantic (or dataclasses + `jsonschema`) to validate the top-level shape so accidental refactors do not break downstream consumers.
    - If adding a dependency is a concern, at least add snapshot/contract tests that assert the JSON keys of a known sample repo.

25. **Centralize repo-path validation**
    - Only `scan.py` checks `is_dir()`; other analyzers assume the path is a directory after `exists()`.
    - Add a shared `validate_repo(path) -> Path` helper that returns a resolved directory or raises a standard error payload.

## Appendix — Dependency Impact Summary

| Addition     | Scope            | Rationale                                                   |
| ------------ | ---------------- | ----------------------------------------------------------- |
| `tomli`      | runtime          | Robust TOML parsing for `config.py` (stdlib only in 3.11+). |
| `pyyaml`     | runtime          | Robust YAML parsing for `config.py`.                        |
| `mypy`       | dev              | Type-checking gate.                                         |
| `pydantic`   | dev (or runtime) | Optional output-schema validation.                          |
| `pytest-cov` | dev              | Already present; wire into CI.                              |

> **Note:** If keeping the project zero-dependency at runtime is a hard requirement, make `tomli` and `pyyaml` optional (soft-import with graceful degradation to the current hand-rolled parsers). However, the hand-rolled parsers are the single biggest correctness risk in the codebase, so strong preference to making them required.
