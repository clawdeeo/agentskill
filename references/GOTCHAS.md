# GOTCHAS.md — Extraction and Synthesis Errors

> Read this file in full before drafting any section of `AGENTS.md`.
> Every entry here is a failure mode discovered from an actual run.
> When you discover a new one, add it.

---

## Extraction Errors

These errors occur during data collection — the signal is wrong before synthesis even begins.

---

### Keyword pollution

**What happens:** Language keywords (`self`, `cls`, `if`, `for`, `return`) are counted alongside identifier names, inflating snake_case totals and polluting naming pattern analysis.

**Fix:** Filter keywords before classifying names. Do not count anything that appears in the language's reserved word list.

---

### Single-word name ambiguity

**What happens:** A name like `foo` or `data` matches both `camelCase` and `snake_case` classifiers because it has no case transitions. These names dominate short codebases and produce false confidence.

**Fix:** Require at least one case transition or underscore before classifying a name. Single-word names are `other`, not evidence of any convention.

---

### Generated file skew

**What happens:** Vendored files, lockfiles, and generated code have zero comments, uniform indentation, and no meaningful names. Including them distorts every measurement.

**Fix:** Exclude all directories in `SKIP_DIRS` — including `node_modules`, `vendor`, `dist`, `build`, `.eggs`, `site-packages`, and `__pycache__`. Do not include `.lock` files in line length or whitespace analysis.

---

### Test file bias

**What happens:** Test files use different idioms than source files — more `assert` statements, more fixture variables, more repetitive naming. Mixing them into source analysis contaminates naming and error handling measurements.

**Fix:** Analyze test files and source files separately. Only report source-file patterns as codebase conventions. Call out test-specific patterns explicitly under Section 12.

---

### Blank line measurement at file boundaries

**What happens:** The first top-level definition in a file has no predecessor, so the blank line count before it is always zero. Including this in the distribution pulls the mode toward zero even when the real convention is two blank lines between definitions.

**Fix:** Exclude the first definition in each file from the blank-line-between-definitions measurement. Only measure gaps _between_ two definitions, never before the first one.

---

### Import misclassification

**What happens:** stdlib module names that overlap with third-party package names (`email`, `ast`, `typing`) get classified as third-party, and vice versa. This produces incorrect import ordering rules.

**Fix:** Maintain an explicit stdlib module list. Check against it before classifying an import. When uncertain, check the module's origin via `sys.stdlib_module_names` (Python 3.10+) rather than guessing.

---

### Branch inflation from remote tracking refs

**What happens:** `git branch -a` returns both local branches and remote tracking refs (`remotes/origin/fix/thing`). Counting both doubles the apparent branch count and inflates prefix diversity.

**Fix:** Strip `remotes/origin/` prefixes before analysis. Count each logical branch once.

---

### Monorepo boundary misdetection

**What happens:** A repo with a `packages/` or `services/` directory at the root is treated as a monorepo even when it contains a single service. This triggers Section 3 and Section 4 synthesis when they don't apply.

**Fix:** Require at least two immediate child directories under the boundary dir before classifying as monorepo. One service is a single repo with a subdirectory, not a monorepo.

---

## Synthesis Errors

These errors occur during `AGENTS.md` generation — the data is fine but the output is wrong.

---

### Reporting language defaults as codebase rules

**What happens:** `AGENTS.md` states "uses snake_case for variable names in Python" or "uses tabs in Go." These are language defaults, not codebase conventions. An agent following these rules learns nothing specific about this repo.

**Fix:** Never state a language default as a codebase rule unless you have a specific reason — for example, the codebase deviates from the default, or the default is so frequently violated in practice that it's worth reinforcing. If you can't point to a concrete reason to include it, omit it.

---

### Claiming formatter use without explicit config

**What happens:** The code looks formatted, so `AGENTS.md` states "uses Black" or "uses Prettier." But no config file exists, and the author may simply write clean code manually. An agent that believes a formatter is in use may generate sloppy code expecting a post-processing fix.

**Fix:** Only claim formatter use if a config file is present and readable. If the code looks formatted but no config exists, state that no formatter is configured and document the observed style directly.

---

### Universal noise in red lines

**What happens:** Red lines include entries like "be consistent with naming" or "handle errors properly." These apply to every codebase and teach an agent nothing about this one.

**Fix:** Every red line must be grounded in something this specific codebase avoids. If you cannot point to evidence that this repo avoids a pattern, do not list it. Prefer "never use `Optional[X]` — this repo uses `X | None` exclusively" over "use consistent type annotation style."

---

### Omitting the Code Formatting section or treating it as lower priority

**What happens:** Synthesis focuses on naming and error handling — the interesting sections — and produces a thin or empty Code Formatting section. The agent then generates code with wrong indentation, wrong blank lines, or wrong quote style.

**Fix:** Code Formatting is the highest-fidelity section. It must be completed in full before any other section is considered done. Apply the Mimicry Test to it first.

---

### Conflating method blank lines with top-level blank lines

**What happens:** The measured blank line convention (e.g. two blank lines between top-level definitions) is incorrectly applied to methods inside classes, where the convention may be one blank line. Or the reverse.

**Fix:** Document blank line conventions separately: one rule for top-level definitions, one rule for methods inside a class, one rule for after the class declaration line. State "not applicable" explicitly if the codebase has no classes.

---

### Missing metadata from README and LICENSE

**What happens:** `AGENTS.md` is written without checking `README.md` or `LICENSE`. The overview section omits the project's stated purpose, and the dependencies section omits the license type, which sometimes affects dependency philosophy.

**Fix:** Always read `README.md` before writing Section 1. Check `LICENSE` before writing Section 14. These files contain author-stated intent that source code alone cannot reveal.

---

### Carrying rules across language boundaries without labeling them

**What happens:** A Python naming rule or a TypeScript error handling pattern ends up in a shared or unlabeled section, and an agent working in Go applies it.

**Fix:** Every rule must be explicitly scoped. Repo-wide rules get a `> **Repo-wide:**` blockquote. Language-specific rules live under clearly named `### Language` subsections. A rule that appears in both languages must be stated twice — once per language — unless it is explicitly marked repo-wide.

---

### Stale remote assumptions

**What happens:** A GitHub remote is detected, so `AGENTS.md` states CI exists. But the `.github/workflows/` directory is empty or absent.

**Fix:** Check `.github/workflows/` explicitly before mentioning CI. A remote host is not evidence of a CI pipeline.

---

### Tentative rules left unlabeled

**What happens:** A pattern is observed in only one or two files but stated as a firm rule. An agent follows it without knowing the evidence is thin.

**Fix:** Mark any rule grounded in fewer than three examples as `[tentative]`. If you find genuine inconsistency with no dominant pattern, state the inconsistency explicitly. Never invent a rule to fill a gap.

---

_Add new entries here after every run where a failure mode is discovered._
_Do not remove entries — even superseded gotchas document the shape of the problem space._
