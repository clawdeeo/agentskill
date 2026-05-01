# Command Modules

The analyzer command modules live in `agentskill.commands`. Each module exposes
one primary analyzer callable that accepts a repository path and returns a JSON
serializable payload, plus a `main()` wrapper for direct execution.

## Inventory

- `agentskill.commands.scan`
  Primary callable: `scan(repo_path: str, lang_filter: str | None = None) -> dict`
  Role: repository walk, file inventory, language summary, and suggested read order.
- `agentskill.commands.measure`
  Primary callable: `measure(repo_path: str, lang_filter: str | None = None) -> dict`
  Role: formatting metrics such as indentation, line-length percentiles, and blank-line distributions.
- `agentskill.commands.config`
  Primary callable: `detect(repo_path: str) -> dict`
  Role: formatter, linter, type-checker, build-tool, and project-marker detection.
- `agentskill.commands.git`
  Primary callable: `analyze(repo_path: str) -> dict`
  Role: commit-prefix, branch-shape, merge-strategy, and repository-history analysis.
- `agentskill.commands.graph`
  Primary callable: `build_graph(repo_path: str, lang_filter: str | None = None) -> dict`
  Role: import, include, require, and dependency-edge extraction across supported languages.
- `agentskill.commands.symbols`
  Primary callable: `extract_symbols(repo_path: str, lang_filter: str | None = None) -> dict`
  Role: symbol-name extraction and naming-pattern clustering.
- `agentskill.commands.tests`
  Primary callable: `analyze_tests(repo_path: str) -> dict`
  Role: test-framework detection, test-to-source mapping, and coverage-shape inference.

## Direct Wrappers

Each analyzer module also exposes `main(argv: list[str] | None = None) -> int`
for direct wrapper execution. Those wrappers remain supported under `scripts/`,
but they are secondary to the installed `agentskill` CLI.

## Extension Guidance

- Add new analyzer implementation logic inside `agentskill.commands`.
- Keep analyzer return values JSON-serializable.
- Follow the error-payload convention used elsewhere in the codebase:
  `{"error": "...", "script": "<name>"}`.
- Wire new public CLI exposure through `agentskill.main`, not by expanding
  wrapper-only behavior under `scripts/`.
