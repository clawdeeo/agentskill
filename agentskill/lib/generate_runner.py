"""Direct AGENTS.md generation workflow without merge/update semantics."""

import sys
from pathlib import Path

from agentskill.common.fs import validate_repo
from agentskill.lib.interactive_runner import (
    PromptIO,
    StdinPromptIO,
    apply_interactive_notes,
    ask_generation_questions,
    detect_generation_gaps,
    interactive_section_notes,
)
from agentskill.lib.multifile_output import (
    SECTION_DIR,
    build_root_index,
    build_section_file,
    section_file_path,
)
from agentskill.lib.output import validate_out_path
from agentskill.lib.output_layouts import validate_output_layout
from agentskill.lib.output_profiles import validate_output_profile
from agentskill.lib.profile_rendering import (
    build_companion_document,
    companion_path,
    inject_split_link,
)
from agentskill.lib.reference_flow import load_reference_documents
from agentskill.lib.reference_initialization import (
    initialize_from_references,
    render_reference_metadata_block,
)
from agentskill.lib.runner import run_all
from agentskill.lib.update_feedback import load_feedback
from agentskill.lib.update_merge import merge_agents_document
from agentskill.lib.update_runner import (
    DOCUMENT_TITLE,
    SECTION_ORDER,
    render_agents_sections,
)


def _inject_reference_metadata(markdown: str, metadata_block: str) -> str:
    if markdown.startswith(DOCUMENT_TITLE):
        return (
            DOCUMENT_TITLE
            + metadata_block
            + "\n\n"
            + markdown.removeprefix(DOCUMENT_TITLE)
        )

    return metadata_block + "\n\n" + markdown


def render_agents_markdown(
    repo: Path,
    *,
    references: list[str] | None = None,
    interactive: bool = False,
    prompt_io: PromptIO | None = None,
    profile: str = "concise",
) -> str:
    profile = validate_output_profile(profile)

    documents = load_reference_documents(references)
    analysis = run_all(str(repo))
    feedback = load_feedback(repo)
    sections = render_agents_sections(repo, analysis, feedback, profile=profile)

    if interactive:
        gaps = detect_generation_gaps(analysis, documents)
        answers = ask_generation_questions(gaps, prompt_io or StdinPromptIO())
        sections = apply_interactive_notes(sections, interactive_section_notes(answers))

    result = merge_agents_document(
        None,
        sections,
        force=True,
        document_preamble=DOCUMENT_TITLE,
        preferred_order=SECTION_ORDER,
    )

    markdown = result.text

    if not references:
        return markdown

    initialization = initialize_from_references(analysis, documents)
    metadata_block = render_reference_metadata_block(initialization.metadata)

    return _inject_reference_metadata(markdown, metadata_block)


def generate_agents(
    repo: str,
    *,
    out: str | None = None,
    references: list[str] | None = None,
    interactive: bool = False,
    prompt_io: PromptIO | None = None,
    profile: str = "concise",
    layout: str = "single",
) -> int:
    profile = validate_output_profile(profile)
    layout = validate_output_layout(layout)

    try:
        repo_path = validate_repo(repo)
    except ValueError as exc:
        print(f"Generate failed for repo {repo}: {exc}", file=sys.stderr)
        return 1

    if layout == "split":
        return _generate_split(
            repo_path,
            out=out,
            references=references,
            interactive=interactive,
            prompt_io=prompt_io,
            profile=profile,
        )

    if layout == "multifile":
        return _generate_multifile(
            repo_path,
            out=out,
            references=references,
            interactive=interactive,
            prompt_io=prompt_io,
            profile=profile,
        )

    try:
        markdown = render_agents_markdown(
            repo_path,
            references=references,
            interactive=interactive,
            prompt_io=prompt_io,
            profile=profile,
        )

        if out is not None:
            output_path = validate_out_path(out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown)
        else:
            print(markdown, end="")
    except Exception as exc:
        print(f"Generate failed for repo {repo}: {exc}", file=sys.stderr)
        return 1

    return 0


def _generate_split(
    repo_path: Path,
    *,
    out: str | None = None,
    references: list[str] | None = None,
    interactive: bool = False,
    prompt_io: PromptIO | None = None,
    profile: str = "concise",
) -> int:
    """Generate concise primary + comprehensive companion files."""
    if out is None:
        print(
            "generate with layout 'split' requires --out because it writes multiple files",
            file=sys.stderr,
        )
        return 1

    primary_path = validate_out_path(out)

    try:
        documents = load_reference_documents(references)
        analysis = run_all(str(repo_path))
        feedback = load_feedback(repo_path)

        concise_sections = render_agents_sections(
            repo_path, analysis, feedback, profile="concise"
        )

        if interactive:
            gaps = detect_generation_gaps(analysis, documents)
            answers = ask_generation_questions(gaps, prompt_io or StdinPromptIO())
            concise_sections = apply_interactive_notes(
                concise_sections, interactive_section_notes(answers)
            )

        comprehensive_sections = render_agents_sections(
            repo_path, analysis, feedback, profile="comprehensive"
        )

        if interactive:
            comprehensive_sections = apply_interactive_notes(
                comprehensive_sections, interactive_section_notes(answers)
            )

        concise_result = merge_agents_document(
            None,
            concise_sections,
            force=True,
            document_preamble=DOCUMENT_TITLE,
            preferred_order=SECTION_ORDER,
        )

        comprehensive_result = merge_agents_document(
            None,
            comprehensive_sections,
            force=True,
            document_preamble=DOCUMENT_TITLE,
            preferred_order=SECTION_ORDER,
        )

        primary_markdown = inject_split_link(concise_result.text, primary_path)
        companion_markdown = build_companion_document(comprehensive_result.text)

        if references:
            initialization = initialize_from_references(analysis, documents)
            metadata_block = render_reference_metadata_block(initialization.metadata)

            primary_markdown = _inject_reference_metadata(
                primary_markdown, metadata_block
            )

            companion_markdown = _inject_reference_metadata(
                companion_markdown, metadata_block
            )

        comp_path = companion_path(primary_path)

        primary_path.parent.mkdir(parents=True, exist_ok=True)
        primary_path.write_text(primary_markdown)
        comp_path.parent.mkdir(parents=True, exist_ok=True)
        comp_path.write_text(companion_markdown)
    except Exception as exc:
        print(f"Generate failed for repo {repo_path}: {exc}", file=sys.stderr)
        return 1

    return 0


def _generate_multifile(
    repo_path: Path,
    *,
    out: str | None = None,
    references: list[str] | None = None,
    interactive: bool = False,
    prompt_io: PromptIO | None = None,
    profile: str = "comprehensive",
) -> int:
    """Generate root index + per-section markdown files."""
    if out is None:
        print(
            "generate with layout 'multifile' requires --out because it writes multiple files",
            file=sys.stderr,
        )
        return 1

    primary_path = validate_out_path(out)

    try:
        documents = load_reference_documents(references)
        analysis = run_all(str(repo_path))
        feedback = load_feedback(repo_path)

        sections = render_agents_sections(
            repo_path, analysis, feedback, profile=profile
        )

        if interactive:
            gaps = detect_generation_gaps(analysis, documents)
            answers = ask_generation_questions(gaps, prompt_io or StdinPromptIO())
            sections = apply_interactive_notes(
                sections, interactive_section_notes(answers)
            )

        overview_body = sections.get("overview")
        overview_summary = ""

        if overview_body is not None:
            overview_text = overview_body.body.strip()
            lines = [
                line for line in overview_text.splitlines() if not line.startswith("#")
            ]

            if lines:
                overview_summary = " ".join(
                    line.strip() for line in lines if line.strip()
                )

        active_sections = [name for name in SECTION_ORDER if name in sections]

        root_markdown = build_root_index(
            primary_path, active_sections, overview_summary=overview_summary
        )

        if references:
            initialization = initialize_from_references(analysis, documents)
            metadata_block = render_reference_metadata_block(initialization.metadata)
            root_markdown = _inject_reference_metadata(root_markdown, metadata_block)

        primary_path.parent.mkdir(parents=True, exist_ok=True)
        primary_path.write_text(root_markdown)

        section_dir = primary_path.parent / SECTION_DIR
        section_dir.mkdir(parents=True, exist_ok=True)

        for name in active_sections:
            section = sections[name]
            file_path = section_file_path(primary_path, name)
            file_content = build_section_file(name, section.body)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_content)
    except Exception as exc:
        print(f"Generate failed for repo {repo_path}: {exc}", file=sys.stderr)
        return 1

    return 0
