# API Reference

This directory documents the packaged `agentskill/` namespace as shipped.

The public CLI surface is the installed `agentskill` command wired through
`agentskill.main:main`. Analyzer implementations live in `agentskill.commands`,
shared orchestration and generation/update helpers live in `agentskill.lib`,
and reusable low-level helpers live in `agentskill.common`.

Reference pages:

- [`cli.md`](./cli.md): packaged CLI entrypoint, subcommands, and dispatch
- [`commands.md`](./commands.md): analyzer command modules and their primary callables
- [`library.md`](./library.md): orchestration, output, update, generation, and reference helpers
- [`common.md`](./common.md): shared registries, filesystem helpers, and repository walking utilities

This reference is intentionally static and release-oriented. It describes the
current packaged layout and contributor extension points rather than every
private helper.
