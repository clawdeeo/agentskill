# agentskill — Release Roadmap

This file is reserved for future release planning.

Use it to track upcoming versions, themes, and release-scoped work. Remove
completed items instead of turning this file into a changelog.

## Planning Rules

- Keep this file focused on unreleased work only.
- Group work by release, not by subsystem.
- Prefer short release themes over long prose.
- Move shipped details to changelog or release notes, not here.
- Keep speculative ideas out unless they are likely to land in a planned release.

---

## 1.4.0 — Watch and Validate

**Theme:** faster local feedback and safer regeneration loops.

- Add file watching for continuous analyze / generate / update workflows
- Add diff preview before applying `update` changes
- Add stale-check detection for generated `AGENTS.md` files
- Add validation command(s) for generated markdown and workflow expectations
- Add optional pre-commit hook integration for validate/update checks
- Improve local iteration flow for users maintaining `AGENTS.md` actively

---

## 1.5.0 — Landing Page

**Theme:** present the project clearly to new users.

- Add a dedicated presentational landing page
- Add hero section with concise project positioning
- Add feature cards for analyzers, generate, update, references, and skill mode
- Add interactive product demo or walkthrough preview
- Add links to:
  - documentation site
  - GitHub repository
  - PyPI package
  - ClawHub entry
- Keep the landing page marketing-focused and separate from technical docs

---

## 1.6.0 — Documentation Site

**Theme:** make the docs easier to explore and maintain.

- Add a dedicated documentation site separate from the landing page
- Add searchable API reference
- Add per-analyzer guides
- Add tutorials for:
  - analyze
  - generate
  - update
  - references
  - interactive mode
- Add versioned documentation
- Add dark mode
- Add docs navigation for contributors and users separately

---

## 1.7.0 — Export and Reporting

**Theme:** make output easier to consume and share.

- Add HTML export for analysis and generated reports
- Add repository stats dashboard output
- Add CI-friendly badges and embeddable status/report artifacts
- Add batch multi-repo analysis workflows
- Add summary reporting views for multiple repositories at once
- Improve machine-readable and human-readable reporting output formats

---

## 1.8.0 — Extensibility

**Theme:** let advanced users adapt agentskill to their own environments.

- Add plugin system for custom analyzers
- Add support for custom output templates
- Add external config loading for project- or user-level customization
- Define stable extension points for packaged runtime modules
- Document plugin lifecycle and safety boundaries
- Keep core analyzers first-party while allowing optional extension hooks

---

## 1.9.0 — Smarter Synthesis

**Theme:** improve the quality and usefulness of generated `AGENTS.md` output.

- Add confidence scoring in generated `AGENTS.md`
- Add pattern suggestions when conventions are weak or ambiguous
- Add cross-repo comparison workflows
- Add git history trend analysis for convention drift over time
- Improve synthesis quality by combining analyzer signals more explicitly
- Keep all synthesis deterministic unless an explicit optional AI mode is enabled

---

## 1.10.0 — AI Enhancement (opt-in)

**Theme:** optional LLM-assisted synthesis improvements without changing the default offline model.

- Add opt-in LLM-powered synthesis enhancement
- Add provider support for external AI backends
- Add token budgeting controls
- Add cost estimation before execution
- Keep offline/static generation as the default behavior
- Ensure AI enhancement is additive and optional, never required for normal use

---

## 1.11.0 — Workspace and Scale

**Theme:** handle larger organizations and repository collections more cleanly.

- Add monorepo workspace manifest support
- Add cross-repo graph views
- Add per-repo overrides inside a workspace
- Improve large-scale analysis flows for many related repositories
- Add workspace-aware generate/update behaviors where appropriate
- Keep single-repo usage simple while scaling cleanly to larger environments

---

## 1.12.0 — Team and Collaboration

**Theme:** support shared conventions and collaborative review workflows.

- Add team-level overrides on top of repo-local configuration
- Add convention diff between two `AGENTS.md` files
- Add PR review mode for generated or updated `AGENTS.md`
- Add team voting or review input collection for convention changes
- Improve workflows for teams standardizing conventions across repos
- Keep collaboration features optional and non-breaking for solo users

---

## 1.13.0 — Templates and Profiles

**Theme:** speed up adoption with reusable starting points.

- Add built-in project-type templates
- Add user-defined templates
- Add reusable profiles for common stacks or team styles
- Add template selection during generation workflows
- Add template marketplace support
- Keep templates as accelerators, not replacements for repository analysis

---

## 1.14.0 — CI and Distribution

**Theme:** make agentskill easier to adopt in automation and developer shells.

- Add official GitHub Action
- Add `--check` gate mode for CI enforcement
- Add shell completions
- Add unified JSON output across commands where practical
- Improve automation-friendly distribution and integration surfaces
- Strengthen CI adoption paths without introducing breaking CLI changes
