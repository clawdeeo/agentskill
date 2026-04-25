"""Git extraction utilities."""

import subprocess
from typing import Dict, List

from ..constants import COMMIT_LOG_LIMIT, GIT_TIMEOUT, REMOTE_PREFIX, TOP_BRANCH_PREFIXES, TOP_COMMIT_PREFIXES


def run_git_log(repo_path: str) -> str:
    """Run git log and return output."""
    result = subprocess.run(
        ["git", "-C", repo_path, "log", "--pretty=format:%s", f"-{COMMIT_LOG_LIMIT}"],
        capture_output=True, text=True, timeout=GIT_TIMEOUT
    )
    return result.stdout if result.returncode == 0 else ""


def extract_commit_prefixes(commits: List[str]) -> Dict[str, int]:
    """Extract conventional commit prefixes from commit messages."""
    import re
    prefixes = {}
    for commit in commits:
        match = re.match(r'^(\[?\w+\]?)(?:\(|:)', commit.lower())
        if match:
            prefix = match.group(1).strip('[]')
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return prefixes


def analyze_git_commits(repo_path: str) -> Dict:
    """Analyze git commit patterns."""
    try:
        stdout = run_git_log(repo_path)
        commits = [c for c in stdout.strip().split('\n') if c]

        if not commits:
            return {"count": 0, "avg_length": 0, "common_prefixes": {}}

        lengths = [len(c) for c in commits]
        prefixes = extract_commit_prefixes(commits)

        return {
            "count": len(commits),
            "avg_length": sum(lengths) / len(lengths),
            "common_prefixes": dict(sorted(prefixes.items(), key=lambda x: -x[1])[:TOP_COMMIT_PREFIXES])
        }
    except Exception:
        return {"count": 0, "avg_length": 0, "common_prefixes": {}}


def run_git_branch(repo_path: str) -> str:
    """Run git branch and return output."""
    result = subprocess.run(
        ["git", "-C", repo_path, "branch", "-a"],
        capture_output=True, text=True, timeout=GIT_TIMEOUT
    )
    return result.stdout if result.returncode == 0 else ""


def extract_branch_prefixes(branches: List[str]) -> Dict[str, int]:
    """Extract branch naming prefixes."""
    prefixes = {}
    for branch in branches:
        branch = branch.replace(REMOTE_PREFIX, '')
        # Skip HEAD pointer lines and detached HEAD references
        if 'HEAD' in branch or ' -> ' in branch:
            continue
        parts = branch.split('/')
        if len(parts) > 1:
            prefix = parts[0]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return prefixes


def analyze_branches(repo_path: str) -> Dict:
    """Analyze branch naming patterns."""
    try:
        stdout = run_git_branch(repo_path)
        branches = [b.strip().strip('* ') for b in stdout.split('\n') if b.strip()]
        # Filter out HEAD pointers and detached HEAD refs
        branches = [b for b in branches if 'HEAD' not in b and ' -> ' not in b]

        prefixes = extract_branch_prefixes(branches)

        return {
            "count": len(branches),
            "common_prefixes": dict(sorted(prefixes.items(), key=lambda x: -x[1])[:TOP_BRANCH_PREFIXES])
        }
    except Exception:
        return {"count": 0, "common_prefixes": {}}


def analyze_git_config(repo_path: str) -> Dict:
    """Extract git configuration hints."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "config", "--list"],
            capture_output=True, text=True, timeout=10
        )
        config = result.stdout if result.returncode == 0 else ""

        has_gpg = "gpg.program" in config or "commit.gpgsign" in config
        has_signoff = "commit.signoff" in config

        return {
            "gpg_signing": has_gpg,
            "signoff": has_signoff,
        }
    except Exception:
        return {}


def get_remote_info(repo_path: str) -> Dict:
    """Extract remote repository info."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "remote", "-v"],
            capture_output=True, text=True, timeout=10
        )
        remotes = result.stdout if result.returncode == 0 else ""

        has_github = "github.com" in remotes
        has_gitlab = "gitlab" in remotes

        return {
            "github": has_github,
            "gitlab": has_gitlab,
            "remote_count": len([r for r in remotes.split('\n') if r.strip()])
        }
    except Exception:
        return {}
