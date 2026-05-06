# Library Reference

The `agentskill.lib` package contains orchestration and document-generation
helpers that sit above the analyzer implementations.

## Runner

- Module: `agentskill.lib.runner`
- Primary callables:
  `run_all(repo: str, lang_filter: str | None = None, references: list[str] | None = None) -> dict`
  `run_many(repos: list[str], lang_filter: str | None = None, references: list[str] | None = None) -> dict`

This module owns the analyzer registry (`COMMANDS`), parallel analyzer
execution, timeout handling, and multi-repo aggregation.

## Output and Schema

- Module: `agentskill.lib.output`
  Primary helpers: `write_output(...)`, `run_and_output(...)`, `validate_out_path(...)`
- Module: `agentskill.lib.output_schema`
  Primary helper: `validate_public_output(data: object, *, mode: str) -> None`

These modules validate and serialize public JSON output, enforce `--out` path
rules, and keep the CLI-facing output contract consistent.

## Generation and Update

- Module: `agentskill.lib.generate_runner`
  Primary callables:
  `render_agents_markdown(...) -> str`
  `generate_agents(...) -> int`
- Module: `agentskill.lib.update_runner`
  Primary callables:
  `render_agents_sections(...) -> dict[str, AgentsSection]`
  `update_agents(...) -> int`
- Module: `agentskill.lib.update_merge`
  Primary helper: `merge_agents_document(...)`
- Module: `agentskill.lib.update_feedback`
  Primary helper: `load_feedback(repo_path: str | Path) -> UpdateFeedback`
- Module: `agentskill.lib.output_profiles`
  Primary callables: `validate_output_profile(profile: str) -> str`
  Constants: `DEFAULT_OUTPUT_PROFILE`, `SUPPORTED_OUTPUT_PROFILES`
- Module: `agentskill.lib.output_layouts`
  Primary callables: `validate_output_layout(layout: str) -> str`
  Constants: `DEFAULT_OUTPUT_LAYOUT`, `SUPPORTED_OUTPUT_LAYOUTS`
- Module: `agentskill.lib.profile_rendering`
  Primary callables: `combine_section_body(...)`, `build_companion_document(...)`, `inject_split_link(...)`, `companion_path(...)`, `companion_relative_link(...)`
- Module: `agentskill.lib.multifile_output`
  Primary callables: `section_file_path(...)`, `build_section_file(...)`, `build_root_index(...)`
  Constants: `SECTION_FILE_MAP`, `SECTION_DESCRIPTIONS`, `SECTION_DIR`

`generate_runner` produces a fresh document without merge semantics.
`update_runner` regenerates sections and merges them into an existing
`AGENTS.md` unless `--force` requests a clean rebuild.

Profile and layout handling: `--profile` controls content density (`concise`
or `comprehensive`). `--layout` controls output packaging (`single`, `split`,
or `multifile`). Split layout writes a concise primary plus comprehensive
companion regardless of the profile flag. Multifile layout writes a root
index plus per-section files using the specified profile (default
`comprehensive`).

## Reference and Interactive Flows

- Module: `agentskill.lib.reference_flow`
  Primary helper: `load_reference_documents(references: list[str] | None) -> list[ReferenceDocument]`
- Module: `agentskill.lib.reference_initialization`
  Primary helper: `initialize_from_references(...)`
- Module: `agentskill.lib.reference_adaptation`
  Role: compare reference conventions against target analysis signals
- Module: `agentskill.lib.reference_questions`
  Role: generate follow-up questions when references and target analysis diverge
- Module: `agentskill.lib.references`
  Role: local and remote reference loading
- Module: `agentskill.lib.interactive_runner`
  Role: prompt orchestration and interactive-note injection

These modules power `--reference` and `--interactive` behavior for the packaged
generation flow.

## Other Shared Helpers

- `agentskill.lib.cli_entrypoint`
  Shared analyzer-wrapper argument parsing for direct script entrypoints.
- `agentskill.lib.logging_utils`
  Stderr logger setup for internal use.
- `agentskill.lib.parsers`
  Safe TOML and YAML parsing helpers.
- `agentskill.lib.agents_document`
  AGENTS section parsing and section-object helpers.
