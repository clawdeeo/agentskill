# CLI Reference

## Canonical Entry Point

- Module: `agentskill.main`
- Published console script: `agentskill = "agentskill.main:main"`
- Primary callable: `main(argv: list[str] | None = None) -> int`

`agentskill.main` is the source of truth for the installed CLI. It owns global
argument parsing, subcommand registration, and dispatch into analyzer,
generation, and update workflows.

## Public Command Families

- `agentskill analyze <repo> [<repo2> ...]`
  Runs the full analyzer stack and emits merged JSON.
- `agentskill scan|measure|config|git|graph|symbols|tests <repo>`
  Runs one analyzer and emits that analyzer's JSON payload.
- `agentskill generate <repo>`
  Renders a fresh `AGENTS.md` document to stdout or `--out`.
- `agentskill update <repo>`
  Regenerates sections and merges them into an existing `AGENTS.md`, or creates
  one when missing.

## Dispatch Model

- `cmd_analyze(args)` calls [`agentskill.lib.runner.run_many`](./library.md#runner)
  and writes public JSON through [`agentskill.lib.output.write_output`](./library.md#output-and-schema).
- `_single_script_cmd(command_name, args)` routes analyzer subcommands through
  the `COMMANDS` registry in `agentskill.lib.runner`.
- `cmd_generate(args)` delegates to
  [`agentskill.lib.generate_runner.generate_agents`](./library.md#generation-and-update).
- `cmd_update(args)` delegates to
  [`agentskill.lib.update_runner.update_agents`](./library.md#generation-and-update).

## Flags and Stable Behavior

- `--pretty` applies to JSON-producing analyzer flows only.
- `--out` writes JSON or markdown to a file instead of stdout.
- `--reference` is supported by `analyze` and `generate`.
- `--interactive` is supported by `generate` only.
- `--profile` is supported by `generate` and `update`. Accepted values are `concise` (default) and `comprehensive`.
  - `concise` emits operational rules and key facts only; representative code snippets and secondary explanatory bullets are suppressed.
  - `comprehensive` includes everything from concise plus representative snippets, annotation measurements, and expanded rationale bullets.
  - All profiles are deterministic from the same analyzer results and preserve the same section order and headings.
  - When `--layout split` is active, the `--profile` flag is ignored: the primary file is always concise and the companion is always comprehensive.
  - When `--layout multifile` is active, `--profile` controls the density of content in each section file. The default profile for multifile is `comprehensive`.
- `--layout` is supported by `generate`. Accepted values are `single` (default), `split`, and `multifile`.
  - `single` writes one complete markdown file. Without `--out`, prints to stdout.
  - `split` writes two files: a concise primary document and an `AGENTS.reference.md` companion with comprehensive content. The primary file contains a relative link to the companion. Without `--out`, split writes into the target repo using `<repo>/AGENTS.md` as the primary path.
  - `multifile` writes a root index file plus per-section markdown files in a `.agentskill/` directory beside the primary output. Section filenames follow a stable numbering scheme: `01_OVERVIEW.md`, `02_REPOSITORY_STRUCTURE.md`, `05_COMMANDS_AND_WORKFLOWS.md`, `06_CODE_FORMATTING.md`, `07_NAMING_CONVENTIONS.md`, `08_TYPE_ANNOTATIONS.md`, `09_IMPORTS.md`, `10_ERROR_HANDLING.md`, `11_COMMENTS_AND_DOCSTRINGS.md`, `12_TESTING.md`, `13_GIT.md`, `14_DEPENDENCIES_AND_TOOLING.md`, `15_RED_LINES.md`. Each section file contains a backlink to the root. Without `--out`, multifile writes into the target repo using `<repo>/AGENTS.md` as the root path.
  - `update --layout` is not yet supported for `split` or `multifile` and is explicitly rejected.
- `--section`, `--exclude-section`, and `--force` are supported by `update`.

Release-grade CLI contract tests live in `tests/test_cli_contract.py`.
