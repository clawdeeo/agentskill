"""Direct AGENTS.md generation workflow without merge/update semantics."""

from pathlib import Path

from common.fs import validate_repo
from lib.logging_utils import get_logger
from lib.output import validate_out_path
from lib.runner import run_all
from lib.update_feedback import load_feedback
from lib.update_merge import merge_agents_document
from lib.update_runner import DOCUMENT_TITLE, SECTION_ORDER, render_agents_sections


def render_agents_markdown(repo: Path) -> str:
    analysis = run_all(str(repo))
    feedback = load_feedback(repo)
    sections = render_agents_sections(repo, analysis, feedback)

    result = merge_agents_document(
        None,
        sections,
        force=True,
        document_preamble=DOCUMENT_TITLE,
        preferred_order=SECTION_ORDER,
    )

    return result.text


def generate_agents(repo: str, *, out: str | None = None) -> int:
    logger = get_logger()

    try:
        repo_path = validate_repo(repo)
        markdown = render_agents_markdown(repo_path)

        if out is not None:
            output_path = validate_out_path(out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown)
        else:
            print(markdown, end="")
    except Exception as exc:
        logger.error("Generate failed for repo %s: %s", repo, exc)
        return 1

    return 0
