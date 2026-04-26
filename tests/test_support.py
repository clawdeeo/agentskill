import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test User",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test User",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def write(repo: Path, rel_path: str, content: str) -> Path:
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def touch_tree(repo: Path, files: dict[str, str]) -> Path:
    for rel_path, content in files.items():
        write(repo, rel_path, content)

    return repo


def create_repo(
    tmp_path: Path, files: dict[str, str] | None = None, name: str = "sample_repo"
) -> Path:
    repo = tmp_path / name
    repo.mkdir(parents=True, exist_ok=True)

    if files:
        touch_tree(repo, files)

    return repo


def create_sample_repo(tmp_path: Path) -> Path:
    return create_repo(
        tmp_path,
        {
            "pyproject.toml": (
                "[tool.pytest.ini_options]\n"
                'testpaths = ["tests"]\n\n'
                "[tool.ruff]\n"
                "line-length = 88\n"
            ),
            ".editorconfig": (
                "root = true\n\n[*.py]\nindent_style = space\nindent_size = 4\n"
            ),
            "pkg/__init__.py": "\n",
            "pkg/util.py": (
                "VALUE_NAME = 1\n\n\ndef helper_value():\n    return VALUE_NAME\n"
            ),
            "pkg/main.py": (
                "from pkg.util import helper_value\n\n\n"
                "class SampleThing:\n"
                "    def run_task(self):\n"
                "        return helper_value()\n\n\n"
                "def main_entry():\n"
                "    return SampleThing().run_task()\n"
            ),
            "tests/test_main.py": (
                "import pytest\n\n"
                "from pkg.main import main_entry\n\n\n"
                "@pytest.fixture\n"
                "def sample_fixture():\n"
                "    return 1\n\n\n"
                "def test_main_entry(sample_fixture):\n"
                "    assert main_entry() == sample_fixture\n"
            ),
        },
    )


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(GIT_ENV)

    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
        env=env,
    )


def init_git_repo(repo: Path, branch: str = "main") -> None:
    git(repo, "init", "-b", branch)


def commit_all(repo: Path, message: str, body: str | None = None) -> None:
    git(repo, "add", ".")

    if body is None:
        git(repo, "commit", "-m", message)
        return

    git(repo, "commit", "-m", message, "-m", body)


def make_commit(
    repo: Path, rel_path: str, content: str, message: str, body: str | None = None
) -> None:
    write(repo, rel_path, content)
    commit_all(repo, message, body)
