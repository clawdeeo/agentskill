# Common Helpers Reference

The `agentskill.common` package holds low-level utilities reused across
analyzers and library modules.

## Language Registry

- Module: `agentskill.common.languages`
- Primary helpers:
  `all_language_specs() -> tuple[LanguageSpec, ...]`
  `language_by_id(language_id: str) -> LanguageSpec | None`
  `language_for_extension(extension: str) -> LanguageSpec | None`
  `language_for_path(path: str | Path) -> LanguageSpec | None`
  `is_supported_language(language_id: str) -> bool`

This registry defines the supported language matrix, filename extensions,
package/config markers, test patterns, and source-root hints used throughout
the analyzer stack.

## Filesystem Helpers

- Module: `agentskill.common.fs`
- Primary helpers:
  `validate_repo(path: str) -> Path`
  `read_text(path: Path, max_bytes: int | None = MAX_FILE_BYTES) -> str`
  `count_lines(path: Path) -> int`

These helpers provide repo-path validation and tolerant file reads for analyzer
work that must keep going across partially broken or unusual repositories.

## Repository Walking and Constants

- Module: `agentskill.common.walk`
  Role: repository traversal and file filtering helpers used by analyzers.
- Module: `agentskill.common.constants`
  Role: shared constants such as byte limits and skip lists.

Keep new low-level helpers here only when they are genuinely reusable across
multiple analyzers or library modules. Orchestration-level behavior belongs in
`agentskill.lib` instead.
