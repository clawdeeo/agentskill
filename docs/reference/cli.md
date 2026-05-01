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
- `--section`, `--exclude-section`, and `--force` are supported by `update`.

Release-grade CLI contract tests live in `tests/test_cli_contract.py`.
