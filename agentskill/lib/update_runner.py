"""Internal workflow for updating AGENTS.md from current analyzer output."""

import re
import sys
from collections import Counter
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from agentskill.common.fs import read_text, validate_repo
from agentskill.lib.agents_document import (
    AgentsSection,
    build_section,
    normalize_section_name,
)
from agentskill.lib.output import validate_out_path
from agentskill.lib.output_layouts import validate_output_layout
from agentskill.lib.output_profiles import validate_output_profile
from agentskill.lib.profile_rendering import RenderedSectionBody, combine_section_body
from agentskill.lib.runner import run_all
from agentskill.lib.update_feedback import (
    SectionFeedback,
    UpdateFeedback,
    load_feedback,
)
from agentskill.lib.update_merge import merge_agents_document

AGENTS_FILENAME = "AGENTS.md"
DOCUMENT_TITLE = "# AGENTS.md\n\n"

SECTION_ORDER = [
    "overview",
    "repository structure",
    "service map",
    "cross-service boundaries",
    "commands and workflows",
    "code formatting",
    "naming conventions",
    "type annotations",
    "imports",
    "error handling",
    "comments and docstrings",
    "testing",
    "git",
    "dependencies and tooling",
    "red lines",
]

SECTION_HEADINGS = {
    "overview": "1. Overview",
    "repository structure": "2. Repository Structure",
    "service map": "3. Service Map",
    "cross-service boundaries": "4. Cross-Service Boundaries",
    "commands and workflows": "5. Commands and Workflows",
    "code formatting": "6. Code Formatting",
    "naming conventions": "7. Naming Conventions",
    "type annotations": "8. Type Annotations",
    "imports": "9. Imports",
    "error handling": "10. Error Handling",
    "comments and docstrings": "11. Comments and Docstrings",
    "testing": "12. Testing",
    "git": "13. Git",
    "dependencies and tooling": "14. Dependencies and Tooling",
    "red lines": "15. Red Lines",
}


def _format_languages(scan: dict) -> str:
    by_language = scan.get("summary", {}).get("by_language", {})
    languages = sorted(by_language)

    if not languages:
        return "No primary language could be determined from the repository scan."

    if len(languages) == 1:
        return languages[0]

    return ", ".join(languages[:-1]) + f", and {languages[-1]}"


def _code_block(snippet: str, lang: str = "python") -> str:
    return f"```{lang}\n{snippet.rstrip()}\n```"


def _read_pyproject(repo: Path) -> dict:
    pyproject = repo / "pyproject.toml"

    if not pyproject.exists():
        return {}

    try:
        with pyproject.open("rb") as file_obj:
            return tomllib.load(file_obj)
    except Exception:
        return {}


def _readme_summary(repo: Path) -> str | None:
    readme = repo / "README.md"
    content = read_text(readme, None)

    if not content:
        return None

    paragraphs = [chunk.strip() for chunk in content.split("\n\n")]

    for paragraph in paragraphs:
        if not paragraph or paragraph.startswith("#") or paragraph.startswith("---"):
            continue

        if paragraph.startswith("```") or paragraph.startswith("|"):
            continue

        return " ".join(paragraph.splitlines()).strip()

    return None


def _top_level_layout(scan: dict) -> list[str]:
    tree = scan.get("tree", [])
    grouped: dict[str, list[str]] = {}

    for entry in tree:
        path = entry.get("path", "")

        if not path:
            continue

        head = path.split("/", 1)[0]
        grouped.setdefault(head, []).append(path)

    lines: list[str] = []

    for name in sorted(grouped):
        suffix = "/" if any("/" in path for path in grouped[name]) else ""
        kind = "test files" if name == "tests" else "source files"
        lines.append(f"{name}{suffix}  # {kind} ({len(grouped[name])} files)")

    return lines


def _python_commands(config: dict, tests: dict) -> list[str]:
    commands = ["pip install -e ."]
    python_tests = tests.get("python", {})
    run_command = python_tests.get("run_command")

    if run_command and run_command != "unknown":
        commands.append(run_command)

    python_config = config.get("python", {})
    linter = python_config.get("linter", {}).get("name")

    if linter == "ruff":
        commands.extend(["ruff format .", "ruff check ."])

    type_checker = python_config.get("type_checker", {}).get("name")

    if type_checker == "mypy":
        commands.append("mypy")

    return commands


def _render_overview(repo: Path, analysis: dict) -> RenderedSectionBody:
    scan = analysis.get("scan", {})
    graph = analysis.get("graph", {})
    boundaries = graph.get("monorepo_boundaries", {})
    languages = _format_languages(scan)
    architecture = "monorepo" if boundaries.get("detected") else "single repository"

    readme_summary = _readme_summary(repo)
    pyproject = _read_pyproject(repo)
    project = pyproject.get("project", {})
    scripts = project.get("scripts", {})
    cli_names = ", ".join(sorted(scripts)) if isinstance(scripts, dict) else ""

    parts = []

    if readme_summary:
        parts.append(readme_summary)
    else:
        parts.append(
            f"{repo.name} is a {architecture} codebase analyzed by agentskill."
        )

    if cli_names:
        parts.append(f"The packaged CLI surface is exposed through `{cli_names}`.")

    parts.append(
        f"The primary language set detected here is {languages}, and the codebase is organized as a {architecture} with analyzer-driven markdown generation."
    )

    core = " ".join(parts) + "\n"
    expanded = ""

    if cli_names and readme_summary:
        expanded = f"The published console scripts include `{cli_names}`.\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_repository_structure(analysis: dict) -> RenderedSectionBody:
    scan = analysis.get("scan", {})
    lines = _top_level_layout(scan)
    body = [
        "```text",
        *lines,
        "```",
        "",
    ]

    line_text = "\n".join(lines)

    core_bullets: list[str] = []
    expanded_bullets: list[str] = []

    if "tests/" in line_text:
        core_bullets.append(
            "- Keep tests under `tests/`; this repo separates tests from source."
        )

    if "scripts/" in line_text:
        core_bullets.append(
            "- Keep direct-execution wrappers under `scripts/`; use the packaged runtime for reusable logic."
        )

    if "examples/" in line_text:
        core_bullets.append(
            "- Keep example or fixture repositories under `examples/`; do not mix them into runtime packages."
        )

    source_roots = [
        line.split("  #", 1)[0] for line in lines if not line.startswith("tests")
    ]

    if source_roots:
        core_bullets.append(
            f"- Keep new source files under existing roots such as `{source_roots[0]}`."
        )

    if len(source_roots) > 1:
        expanded_bullets.append(
            f"- Additional source roots detected: {', '.join(f'`{r}`' for r in source_roots[1:])}."
        )

    core = "\n".join(body + core_bullets) + "\n"
    expanded = ""

    if expanded_bullets:
        expanded = "\n".join(expanded_bullets) + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_service_map(analysis: dict) -> RenderedSectionBody | None:
    boundaries = analysis.get("graph", {}).get("monorepo_boundaries", {})
    services = boundaries.get("services", [])

    if not boundaries.get("detected") or not services:
        return None

    core_lines: list[str] = []
    expanded_lines: list[str] = []

    for service in services:
        core_lines.append(f"- `{service}`: service root at `{service}`")
        expanded_lines.append(f"  - Service root: `{service}`")

    core = "\n".join(core_lines) + "\n"
    expanded = ""

    if expanded_lines:
        expanded = "\n".join(expanded_lines) + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_cross_service_boundaries(analysis: dict) -> RenderedSectionBody | None:
    boundaries = analysis.get("graph", {}).get("monorepo_boundaries", {})

    if not boundaries.get("detected"):
        return None

    imports = boundaries.get("cross_service_imports", [])

    if imports:
        core = (
            "- Cross-service imports were detected in the dependency graph.\n"
            "- Review shared contracts before changing any service boundary.\n"
        )

        expanded = (
            "- Cross-service imports compromise service isolation; "
            "introduce a shared contract layer before adding new cross-service dependencies.\n"
        )
    else:
        core = (
            "- No cross-service imports were detected in the current graph analysis.\n"
            "- Preserve service boundaries unless a shared contract layer is introduced.\n"
        )

        expanded = ""

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_commands_and_workflows(analysis: dict) -> RenderedSectionBody:
    commands = _python_commands(
        analysis.get("config", {}),
        analysis.get("tests", {}),
    )

    core = (
        "```bash\n"
        + "\n".join(commands)
        + "\n```\n\n"
        + "- Use the editable install plus the full `ruff`/`mypy`/`pytest` stack as the canonical local verification path.\n"
    )

    expanded = "- Treat the installed CLI as the primary runtime surface; keep direct wrapper scripts as thin operator entrypoints when they exist.\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_code_formatting(repo: Path, analysis: dict) -> RenderedSectionBody:
    python_metrics = analysis.get("measure", {}).get("python", {})

    if not python_metrics:
        return RenderedSectionBody(
            core="No formatting metrics were extracted from the current analysis run.\n"
        )

    indentation = python_metrics.get("indentation", {})
    line_length = python_metrics.get("line_length", {})

    core = (
        "### Python\n\n"
        f"- Indent with `{indentation.get('size', 0)}` {indentation.get('unit', 'unknown')}; Python files in the scan do not rely on tab-indented blocks.\n"
        f"- Keep ordinary lines around the measured p95 of `{line_length.get('p95', 0)}` and preserve the repo's one-blank-line import-to-constant / two-blank-lines top-level rhythm.\n"
        f"- Leave trailing whitespace stripped and keep a final trailing newline in generated files.\n"
        f"- Follow hanging-indented multiline calls and literals rather than backslash continuations.\n"
    )

    expanded = ""
    multiline = _multiline_call_snippet(repo, analysis)

    if multiline:
        expanded = "\n" + _code_block(multiline) + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_naming_conventions(repo: Path, analysis: dict) -> RenderedSectionBody:
    symbols = analysis.get("symbols", {}).get("python", {})
    function_patterns = ", ".join(
        sorted(symbols.get("functions", {}).get("patterns", {}))
    )

    class_patterns = ", ".join(sorted(symbols.get("classes", {}).get("patterns", {})))
    constant_patterns = ", ".join(
        sorted(symbols.get("constants", {}).get("patterns", {}))
    )

    function_name = _first_python_name(repo, analysis, r"^def ([a-zA-Z0-9_]+)\(")
    class_name = _first_python_name(repo, analysis, r"^class ([A-Za-z0-9_]+)")

    constant_name = _first_python_name(repo, analysis, r"^([A-Z][A-Z0-9_]+)\s*=")
    test_file = next(
        (
            entry.get("path", "")
            for entry in analysis.get("scan", {}).get("tree", [])
            if entry.get("path", "").startswith("tests/test_")
        ),
        "",
    )

    core = (
        "### Python\n\n"
        f"- Keep public helpers and command functions in snake_case; representative names include `{function_name or 'analyze'}`.\n"
        f"- Use PascalCase for classes when they appear; representative names follow patterns like `{class_name or 'ReferenceDocument'}`.\n"
        f"- Keep module constants in SCREAMING_SNAKE_CASE; representative names include `{constant_name or 'GIT_TIMEOUT'}`.\n"
        f"- Name test modules as `test_<subject>.py`; representative paths look like `{test_file or 'tests/test_cli.py'}`.\n"
    )

    expanded = ""
    constant_snippet = _constant_snippet(repo, analysis)

    if constant_snippet:
        expanded_bullets = (
            f"- Observed naming patterns: functions `{function_patterns or 'unknown'}`, "
            f"classes `{class_patterns or 'PascalCase'}`, constants `{constant_patterns or 'unknown'}`.\n"
        )

        expanded = expanded_bullets + "\n" + _code_block(constant_snippet) + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _python_source_paths(scan: dict) -> list[str]:
    return [
        entry.get("path", "")
        for entry in scan.get("tree", [])
        if entry.get("language") == "python"
    ]


def _python_read_order(scan: dict) -> list[str]:
    tree_paths = set(_python_source_paths(scan))
    ordered = [
        path for path in scan.get("read_order", []) if path in tree_paths and path
    ]

    for path in sorted(tree_paths):
        if path not in ordered:
            ordered.append(path)

    return ordered


def _first_python_line(repo: Path, analysis: dict, pattern: str) -> str | None:
    needle = re.compile(pattern)

    for rel_path in _python_read_order(analysis.get("scan", {})):
        content = read_text(repo / rel_path)

        for line in content.splitlines():
            if needle.search(line):
                return line.strip()

    return None


def _first_python_name(repo: Path, analysis: dict, pattern: str) -> str | None:
    needle = re.compile(pattern)

    for rel_path in _python_read_order(analysis.get("scan", {})):
        content = read_text(repo / rel_path)

        for line in content.splitlines():
            match = needle.search(line.strip())

            if match is not None:
                return match.group(1)

    return None


def _module_docstring_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines[:10]):
            if line.strip().startswith('"""'):
                end = min(len(lines), index + 3)
                return _trim_snippet(lines[index:end])

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _inline_comment_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if " #" not in line or line.lstrip().startswith("#"):
                continue

            return _function_snippet(lines, index)

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _multiline_call_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if not line.rstrip().endswith("("):
                continue

            snippet = _function_snippet(lines, index)

            if "\n" in snippet and ")" in snippet:
                return snippet

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _typed_signature_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("def ") and "->" in stripped:
                return _function_snippet(lines, index)

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _class_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if line.strip().startswith("class "):
                return _trim_snippet(lines[index : min(len(lines), index + 6)])

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _constant_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        block: list[str] = []

        for line in lines:
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                if block:
                    break
                continue

            if re.match(r"^[A-Z][A-Z0-9_]+\s*=", stripped):
                block.append(stripped)
                continue

            if block:
                break

        return "\n".join(block) if block else None

    return _first_python_snippet(repo, analysis, matcher)


def _representative_test_snippet(repo: Path, analysis: dict) -> str | None:
    tests = analysis.get("tests", {}).get("python", {})
    rel_path = tests.get("representative_test")

    if not isinstance(rel_path, str) or not rel_path:
        return None

    content = read_text(repo / rel_path)

    if not content:
        return None

    lines = content.splitlines()
    start = None

    for index, line in enumerate(lines):
        if line.strip().startswith("def test_"):
            start = index
            break

    if start is None:
        return _trim_snippet(lines[: min(len(lines), 12)])

    end = min(len(lines), start + 8)
    return _trim_snippet(lines[start:end])


def _render_type_annotations(repo: Path, analysis: dict) -> RenderedSectionBody:
    scan = analysis.get("scan", {})
    paths = _python_source_paths(scan)
    annotated = 0
    total_defs = 0

    for rel_path in paths:
        content = read_text(repo / rel_path)

        for line in content.splitlines():
            stripped = line.strip()

            if not stripped.startswith("def "):
                continue

            total_defs += 1

            if "->" in stripped or ":" in stripped.split("(", 1)[1]:
                annotated += 1

    config = analysis.get("config", {}).get("python", {})
    type_checker = config.get("type_checker", {}).get("name")

    core = (
        "### Python\n\n"
        "- Prefer built-in generics like `list[str]` and union syntax like `str | None` instead of legacy `typing.List` or `Optional` spellings.\n"
        f"- Treat `{type_checker or 'the configured type checker'}` as part of the normal contract when it is present in repo config.\n"
    )

    expanded = (
        f"- Annotate most public and internal helpers directly in the function signature; "
        f"the current scan found `{annotated}` annotated definitions out of `{total_defs}` observed `def` lines.\n"
    )

    typed_signature = _typed_signature_snippet(repo, analysis)

    if typed_signature:
        expanded += "\n" + _code_block(typed_signature) + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _first_import_block(repo: Path, analysis: dict) -> str:
    scan = analysis.get("scan", {})

    for rel_path in scan.get("read_order", []):
        content = read_text(repo / rel_path)
        lines: list[str] = []

        for line in content.splitlines():
            stripped = line.strip()

            if stripped.startswith("import ") or stripped.startswith("from "):
                lines.append(line)
                continue

            if lines and not stripped:
                lines.append(line)
                continue

            if lines:
                break

        if lines:
            return "\n".join(lines).rstrip()

    return ""


def _render_imports(repo: Path, analysis: dict) -> RenderedSectionBody:
    block = _first_import_block(repo, analysis)

    if not block:
        return RenderedSectionBody(
            core="No representative import block was found in the scanned files.\n"
        )

    core = (
        "### Python\n\n"
        "- Keep imports one-per-line and separate major groups with a blank line.\n"
        "- In runtime modules, stdlib imports come first and local package imports follow.\n"
        "- In tests, local test helpers may appear before packaged runtime imports when that matches the file's setup style.\n"
    )

    expanded = "\n" + _code_block(block) + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _trim_snippet(lines: list[str]) -> str:
    start = 0
    end = len(lines)

    while start < end and not lines[start].strip():
        start += 1

    while end > start and not lines[end - 1].strip():
        end -= 1

    return "\n".join(lines[start:end]).rstrip()


def _function_snippet(lines: list[str], anchor: int) -> str:
    start = anchor

    while start > 0:
        candidate = lines[start].lstrip()

        if candidate.startswith("def "):
            break

        start -= 1

    base_indent = _indentation(lines[start]) if lines[start].strip() else 0
    end = len(lines)

    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()

        if not stripped:
            continue

        if _indentation(lines[index]) <= base_indent and not stripped.startswith("#"):
            end = index
            break

    return _trim_snippet(lines[start:end])


def _try_except_snippet(lines: list[str], anchor: int) -> str:
    start = anchor

    while start > 0:
        if lines[start].lstrip().startswith("try:"):
            break

        start -= 1

    if not lines[start].lstrip().startswith("try:"):
        start = anchor

    block_indent = _indentation(lines[start]) if lines[start].strip() else 0
    end = len(lines)

    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()

        if not stripped:
            continue

        if _indentation(lines[index]) <= block_indent and not stripped.startswith(
            ("except", "finally", "else:")
        ):
            end = index
            break

    return _trim_snippet(lines[start:end])


def _first_python_snippet(
    repo: Path,
    analysis: dict,
    matcher,
) -> str | None:
    scan = analysis.get("scan", {})

    for rel_path in _python_read_order(scan):
        content = read_text(repo / rel_path)

        if not content:
            continue

        lines = content.splitlines()
        snippet = matcher(lines)

        if snippet:
            return snippet

    return None


def _value_error_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if "raise ValueError(" in line:
                return _function_snippet(lines, index)

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _error_payload_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if 'return {"error":' in line and '"script"' in line:
                return _function_snippet(lines, index)

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _logged_exception_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if "logger.exception(" in line or (
                "print(" in line and "file=sys.stderr" in line
            ):
                return _try_except_snippet(lines, index)

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _fallback_helper_snippet(repo: Path, analysis: dict) -> str | None:
    def matcher(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            stripped = line.strip()

            if stripped not in {'return ""', "return 0"}:
                continue

            if index == 0 or lines[index - 1].strip() != "except Exception:":
                continue

            return _function_snippet(lines, index)

        return None

    return _first_python_snippet(repo, analysis, matcher)


def _render_error_handling(repo: Path, analysis: dict) -> RenderedSectionBody:
    value_error = _value_error_snippet(repo, analysis)
    error_payload = _error_payload_snippet(repo, analysis)
    logged_exception = _logged_exception_snippet(repo, analysis)
    fallback_helper = _fallback_helper_snippet(repo, analysis)

    core_bullets: list[str] = []
    expanded_bullets: list[str] = []
    snippets: list[str] = []

    if value_error:
        core_bullets.append(
            "- Low-level validators raise `ValueError` with specific message text for invalid caller input."
        )

        snippets.append("```python\n" + value_error + "\n```")

    if error_payload:
        core_bullets.append(
            '- Analyzer boundaries convert validation failures into exact `{"error": ..., "script": ...}` payloads.'
        )

        snippets.append("```python\n" + error_payload + "\n```")

    if logged_exception:
        core_bullets.append(
            "- Shared CLI wrappers catch broad exceptions and return non-zero status instead of letting failures escape unshaped."
        )

        snippets.append("```python\n" + logged_exception + "\n```")

    if fallback_helper:
        core_bullets.append(
            '- Best-effort file helpers swallow unreadable-file exceptions and fall back to `""` or `0` so scans can continue.'
        )

        snippets.append("```python\n" + fallback_helper + "\n```")

    if not core_bullets:
        return RenderedSectionBody(
            core="### Python\n\n- No stable error-handling pattern could be extracted from the scanned Python files.\n"
        )

    core_bullets.append(
        "- Match the existing boundary between raised validation errors and user-facing error payloads instead of introducing a new exception contract."
    )

    expanded_bullets.append(
        "- Shared CLI wrappers log or print diagnostics before converting failures into non-zero status."
    )

    core = "### Python\n\n" + "\n".join(core_bullets) + "\n"
    expanded = ""

    if snippets or expanded_bullets:
        expanded_text = "\n".join(expanded_bullets) + "\n\n" + "\n\n".join(snippets)
        expanded = "\n" + expanded_text + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_comments_and_docstrings(repo: Path, analysis: dict) -> RenderedSectionBody:
    scan = analysis.get("scan", {})
    docstrings = 0
    comments = 0

    for rel_path in scan.get("read_order", []):
        content = read_text(repo / rel_path)
        docstrings += content.count('"""')

        for line in content.splitlines():
            if line.strip().startswith("#"):
                comments += 1

    core = (
        "### Python\n\n"
        "- Prefer short, declarative docstrings and brief targeted inline comments when the code would otherwise be ambiguous.\n"
        "- Keep inline comments sparse; use them to clarify a non-obvious detail rather than narrating obvious code.\n"
    )

    expanded = (
        f"- Module docstrings are common in runtime files; the scan saw `{docstrings}` triple-quoted docstring markers across representative Python files.\n"
        f"- The scan saw `{comments}` comment lines in the representative pass.\n"
    )

    module_docstring = _module_docstring_snippet(repo, analysis)
    inline_comment = _inline_comment_snippet(repo, analysis)

    if module_docstring:
        expanded += "\n" + _code_block(module_docstring) + "\n"

    if inline_comment:
        expanded += "\n" + _code_block(inline_comment) + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_testing(repo: Path, analysis: dict) -> RenderedSectionBody:
    python_tests = analysis.get("tests", {}).get("python", {})
    coverage = python_tests.get("coverage_shape", {})
    fixtures = python_tests.get("fixtures", {})
    test_snippet = _representative_test_snippet(repo, analysis)

    core = (
        "### Python\n\n"
        f"- Use `{python_tests.get('framework', 'unknown')}` as the primary Python test framework and `{python_tests.get('run_command', 'unknown')}` as the full-suite command.\n"
        f"- Keep Python tests under the detected pattern `{python_tests.get('naming', {}).get('file_pattern', 'unknown')}` and follow function names like `{python_tests.get('naming', {}).get('function_pattern', 'test_<description>')}`.\n"
    )

    expanded = (
        f"- Reuse shared test bootstrap from `{', '.join(fixtures.get('conftest_locations', [])) or 'tests/conftest.py'}` when present.\n"
        f"- The current source-to-test mapping leaves `{len(coverage.get('untested_source_files', []))}` Python source files without a matched test file, so new source files should usually arrive with an adjacent or mirrored test.\n"
    )

    if test_snippet:
        expanded += "\n" + _code_block(test_snippet) + "\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_git(analysis: dict) -> RenderedSectionBody:
    git = analysis.get("git", {})

    if "error" in git:
        return RenderedSectionBody(
            core=f"- Git analysis unavailable: `{git['error']}`.\n"
        )

    commits = git.get("commits", {})
    prefixes = commits.get("prefixes", {})
    prefix_names = ", ".join(sorted(prefixes)) or "unknown"
    merge_strategy = git.get("merge_strategy", {}).get("detected", "unknown")

    core = (
        f"- Commit subjects follow conventional prefixes such as `{prefix_names}`.\n"
        f"- The observed merge strategy is `{merge_strategy}`.\n"
    )

    examples = [
        f"`{name}:` for commits like `{info.get('example', '')}`"
        for name, info in list(prefixes.items())[:5]
    ]

    expanded = ""

    if examples:
        expanded = f"- Representative commit examples include {', '.join(examples)}.\n"

    branch_example = git.get("branches", {}).get("naming_example")

    if branch_example:
        core += f"- Branch names use slash-separated prefixes with examples like `{branch_example}`.\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_dependencies_and_tooling(repo: Path, analysis: dict) -> RenderedSectionBody:
    config = analysis.get("config", {})
    tools: list[str] = []

    for lang_data in config.values():
        if not isinstance(lang_data, dict):
            continue

        for tool_type in ("formatter", "linter", "type_checker"):
            tool_info = lang_data.get(tool_type)

            if isinstance(tool_info, dict) and tool_info.get("name"):
                tools.append(tool_info["name"])

    counts = Counter(tools)
    tool_list = ", ".join(sorted(counts)) or "none detected"
    pyproject = _read_pyproject(repo)
    project = pyproject.get("project", {})
    requires_python = project.get("requires-python", "unknown")
    package_name = project.get("name", repo.name)
    scripts = project.get("scripts", {})
    script_names = ", ".join(sorted(scripts)) if isinstance(scripts, dict) else ""

    core = (
        "### Python\n\n"
        f"- Package metadata lives in `pyproject.toml`; the current project name is `{package_name}` and the declared Python floor is `{requires_python}`.\n"
        f"- Tooling detected from repo config includes `{tool_list}`.\n"
    )

    expanded = ""

    if script_names:
        expanded = f"- Published console scripts include `{script_names}`.\n"

    return RenderedSectionBody(core=core, expanded=expanded)


def _render_red_lines(repo: Path, analysis: dict) -> RenderedSectionBody:
    scan = analysis.get("scan", {})
    roots = ", ".join(
        sorted({path.split("/", 1)[0] for path in scan.get("read_order", [])})
    )

    commands = _python_commands(
        analysis.get("config", {}),
        analysis.get("tests", {}),
    )

    package_name = next(
        (
            root
            for root in sorted(
                {path.split("/", 1)[0] for path in scan.get("read_order", [])}
            )
            if root not in {"tests", "scripts", "examples"}
        ),
        "src",
    )

    core = (
        f"- Do not invent new top-level layout patterns when the scan already shows established roots such as `{roots or 'the detected source tree'}`.\n"
        f"- Do not move reusable runtime logic out of `{package_name}` into thin wrapper locations like `scripts/`.\n"
        "- Do not colocate new tests beside source modules when the repo already maintains a separate `tests/` tree.\n"
        "- Do not replace built-in generics and `| None` unions with older `typing.List` / `Optional` spellings in annotated Python code.\n"
        "- Do not switch import grouping to a flat unsplit block when runtime modules already separate stdlib and local imports.\n"
        "- Do not replace the documented verification stack with ad hoc commands; keep local checks aligned with `"
        + ", ".join(commands)
        + "`.\n"
    )

    expanded = (
        "- Do not introduce broad formatting drift such as tabs in Python, missing trailing newlines, or backslash-heavy continuation style.\n"
        "- Do not convert structured error payload boundaries into uncaught CLI exceptions when the repo already normalizes them at command boundaries.\n"
        "- Do not treat example or fixture repositories as runtime code when `examples/` is present as a separate root.\n"
        "- Do not assume missing analyzer signals imply permission to rewrite local conventions.\n"
    )

    return RenderedSectionBody(core=core, expanded=expanded)


def _apply_section_feedback(body: str, feedback: SectionFeedback | None) -> str:
    if feedback is None:
        return body

    parts: list[str] = []

    if feedback.prepend_notes:
        notes = "\n".join(f"- {note}" for note in feedback.prepend_notes)
        parts.append("Maintainer notes from `.agentskill-feedback.json`:\n" + notes)

    if feedback.pinned_facts:
        facts = "\n".join(f"- {fact}" for fact in feedback.pinned_facts)
        parts.append("Pinned facts from `.agentskill-feedback.json`:\n" + facts)

    parts.append(body.rstrip("\n"))
    return "\n\n".join(parts) + "\n"


def render_agents_sections(
    repo: Path,
    analysis: dict,
    feedback: UpdateFeedback | None = None,
    profile: str = "concise",
) -> dict[str, AgentsSection]:
    rendered: dict[str, RenderedSectionBody | None] = {
        "overview": _render_overview(repo, analysis),
        "repository structure": _render_repository_structure(analysis),
        "service map": _render_service_map(analysis),
        "cross-service boundaries": _render_cross_service_boundaries(analysis),
        "commands and workflows": _render_commands_and_workflows(analysis),
        "code formatting": _render_code_formatting(repo, analysis),
        "naming conventions": _render_naming_conventions(repo, analysis),
        "type annotations": _render_type_annotations(repo, analysis),
        "imports": _render_imports(repo, analysis),
        "error handling": _render_error_handling(repo, analysis),
        "comments and docstrings": _render_comments_and_docstrings(repo, analysis),
        "testing": _render_testing(repo, analysis),
        "git": _render_git(analysis),
        "dependencies and tooling": _render_dependencies_and_tooling(repo, analysis),
        "red lines": _render_red_lines(repo, analysis),
    }

    sections: dict[str, AgentsSection] = {}

    for name in SECTION_ORDER:
        body = rendered.get(name)

        if body is None:
            continue

        rendered_text = combine_section_body(profile, body)
        section_feedback = None if feedback is None else feedback.sections.get(name)
        sections[name] = build_section(
            SECTION_HEADINGS[name],
            _apply_section_feedback(rendered_text, section_feedback),
            heading_level=2,
        )

    return sections


def _resolve_update_path(repo: Path, out: str | None) -> Path:
    if out is None:
        return repo / AGENTS_FILENAME

    return validate_out_path(out)


def _validate_requested_sections(
    include_sections: list[str] | None,
    exclude_sections: list[str] | None,
    supported_sections: dict[str, AgentsSection],
) -> None:
    requested = {
        *[normalize_section_name(name) for name in include_sections or []],
        *[normalize_section_name(name) for name in exclude_sections or []],
    }
    unsupported = sorted(name for name in requested if name not in supported_sections)

    if unsupported:
        names = ", ".join(unsupported)
        raise ValueError(f"unsupported or unavailable sections: {names}")


def update_agents(
    repo: str,
    *,
    include_sections: list[str] | None = None,
    exclude_sections: list[str] | None = None,
    force: bool = False,
    out: str | None = None,
    profile: str = "concise",
    layout: str = "single",
) -> int:
    """Update or create AGENTS.md for a repository."""
    try:
        profile = validate_output_profile(profile)
        layout = validate_output_layout(layout)

        if layout == "split":
            raise NotImplementedError(
                "update with layout 'split' is not implemented yet"
            )

        if layout == "multifile":
            raise NotImplementedError(
                "update with layout 'multifile' is not implemented yet"
            )

        repo_path = validate_repo(repo)
        analysis = run_all(str(repo_path))
        feedback = load_feedback(repo_path)

        sections = render_agents_sections(
            repo_path, analysis, feedback, profile=profile
        )

        preserve_sections = [] if force else feedback.preserve_sections
        effective_excludes = [*(exclude_sections or []), *preserve_sections]
        _validate_requested_sections(include_sections, effective_excludes, sections)
        target_path = _resolve_update_path(repo_path, out)
        existing_path = repo_path / AGENTS_FILENAME

        existing_text = (
            read_text(existing_path, None) if existing_path.exists() else None
        )

        merged = merge_agents_document(
            existing_text,
            sections,
            include_sections=include_sections,
            exclude_sections=effective_excludes,
            force=force,
            document_preamble=DOCUMENT_TITLE,
            preferred_order=SECTION_ORDER,
        )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(merged.text)
    except Exception as exc:
        print(f"Update failed for repo {repo}: {exc}", file=sys.stderr)
        return 1

    return 0
