#!/usr/bin/env python3
"""Analyze the git commit log. Extract commit conventions, branch patterns, merge strategy.

Reads actual history — never infers from config or documentation.

Usage:
    python scripts/git.py <repo>
    python scripts/git.py <repo> --pretty
"""

import json
import re
import subprocess
import sys
from pathlib import Path

GIT_TIMEOUT = 30
GIT_HASH_LENGTH = 40
MAX_SCOPE_EXAMPLES = 10
MERGE_COMMITS_SAMPLE = 50
SQUASH_PARENT_THRESHOLD = 1.2

TRUNK_BRANCH_NAMES = {"main", "master", "develop", "dev"}

CONVENTIONAL_PREFIX_RE = re.compile(
    r"^([a-z][a-z0-9_-]*)(\([^)]+\))?(!)?\s*:\s*(.+)$"
)


def _run(cmd: list[str], cwd: str) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


def _parse_commit_subject(subject: str) -> tuple[str | None, str | None, bool]:
    """Return (prefix, scope, is_breaking) or (None, None, False)."""
    m = CONVENTIONAL_PREFIX_RE.match(subject.strip())
    if not m:
        return None, None, False
    prefix = m.group(1)
    scope_raw = m.group(2)
    breaking = m.group(3) == "!"
    scope = scope_raw.strip("()") if scope_raw else None
    return prefix, scope, breaking


def _pct(data: list[int], p: int) -> int:
    if not data:
        return 0
    s = sorted(data)
    idx = max(0, int(len(s) * p / 100) - 1)
    return s[min(idx, len(s) - 1)]


def _analyze_subjects(out: str) -> tuple[dict, dict[str, int], int, int, list[int]]:
    """Parse subject log lines. Return (prefix_data, scope_counts, scoped_count, total, subject_lengths, signed_count)."""
    prefix_data: dict[str, dict] = {}
    scope_counts: dict[str, int] = {}
    scoped_count = 0
    total = 0
    subject_lengths: list[int] = []
    signed_count = 0

    for line in out.strip().splitlines():
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        _hash, subject, _email, gpg = parts
        total += 1
        subject_lengths.append(len(subject))

        if gpg == "G":
            signed_count += 1

        prefix, scope, _breaking = _parse_commit_subject(subject)
        bucket = prefix if prefix else "unprefixed"

        if bucket not in prefix_data:
            prefix_data[bucket] = {"count": 0, "example": subject}
        prefix_data[bucket]["count"] += 1

        if scope:
            scoped_count += 1
            scope_counts[scope] = scope_counts.get(scope, 0) + 1

    return prefix_data, scope_counts, scoped_count, total, subject_lengths, signed_count


def _analyze_bodies(cwd: str) -> int:
    """Return count of commits that have a body."""
    rc, out = _run(["git", "log", "--format=%H|%b", "--no-merges"], cwd)
    if rc != 0:
        return 0

    body_hashes: set[str] = set()
    current_hash = None
    has_body = False

    for line in out.splitlines():
        if "|" in line and len(line.split("|", 1)[0]) == GIT_HASH_LENGTH:
            if current_hash and has_body:
                body_hashes.add(current_hash)
            parts = line.split("|", 1)
            current_hash = parts[0]
            has_body = bool(parts[1].strip()) if len(parts) > 1 else False
        elif line.strip() and current_hash:
            has_body = True

    if current_hash and has_body:
        body_hashes.add(current_hash)

    return len(body_hashes)


def _analyze_branches(cwd: str) -> tuple[dict[str, int], int, list[str]]:
    """Return (branch_prefixes, active_count, examples)."""
    rc, out = _run(["git", "branch", "-a"], cwd)
    branch_prefixes: dict[str, int] = {}
    active_count = 0
    examples: list[str] = []

    if rc != 0:
        return branch_prefixes, active_count, examples

    for line in out.splitlines():
        name = line.strip().lstrip("* ").split("->")[0].strip()
        name = re.sub(r"^remotes/[^/]+/", "", name)
        if name in TRUNK_BRANCH_NAMES or name == "HEAD":
            continue
        active_count += 1
        if "/" in name:
            prefix = name.split("/")[0] + "/"
            branch_prefixes[prefix] = branch_prefixes.get(prefix, 0) + 1
        examples.append(name)

    return branch_prefixes, active_count, examples


def _detect_merge_strategy(cwd: str) -> tuple[str, str]:
    """Return (strategy, evidence)."""
    rc, out = _run(
        ["git", "log", "--merges", "--format=%P", f"-{MERGE_COMMITS_SAMPLE}"],
        cwd,
    )
    if rc != 0:
        return "unknown", "insufficient data"

    merge_lines = [l.strip() for l in out.splitlines() if l.strip()]
    if not merge_lines:
        return "rebase", "no merge commits in history"

    parent_counts = [len(l.split()) for l in merge_lines]
    avg_parents = sum(parent_counts) / len(parent_counts)
    if avg_parents <= SQUASH_PARENT_THRESHOLD:
        return "squash", "merge commits have single parent"

    return "merge", "merge commits have multiple parents"


def analyze(repo_path: str) -> dict:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return {"error": f"path does not exist: {repo_path}", "script": "git"}
    if not (repo / ".git").exists():
        return {"error": "not a git repository", "script": "git"}

    cwd = str(repo)

    rc, out = _run(
        ["git", "log", "--format=%H|%s|%ae|%G?", "--no-merges"],
        cwd,
    )
    if rc != 0:
        return {"error": "git log failed", "script": "git"}

    prefix_data, scope_counts, scoped_count, total, subject_lengths, signed_count = (
        _analyze_subjects(out)
    )

    if total == 0:
        return {"error": "empty repository", "script": "git"}

    prefixes: dict[str, dict] = {}
    for k, v in sorted(prefix_data.items(), key=lambda x: -x[1]["count"]):
        prefixes[k] = {
            "count": v["count"],
            "pct": round(v["count"] / total * 100, 1),
            "example": v["example"],
        }

    top_scopes = sorted(scope_counts, key=lambda k: -scope_counts[k])[:MAX_SCOPE_EXAMPLES]

    body_count = _analyze_bodies(cwd)
    branch_prefixes, active_count, examples = _analyze_branches(cwd)
    merge_strategy, merge_evidence = _detect_merge_strategy(cwd)

    return {
        "commits": {
            "total": total,
            "prefixes": prefixes,
            "scoped": {
                "uses_scopes": scoped_count > 0,
                "scope_examples": top_scopes,
                "pct_scoped": round(scoped_count / total * 100, 1) if total else 0,
            },
            "subject_length": {
                "p50": _pct(subject_lengths, 50),
                "p95": _pct(subject_lengths, 95),
                "max": max(subject_lengths, default=0),
            },
            "has_body": {
                "pct_with_body": round(body_count / total * 100, 1) if total else 0,
            },
            "gpg_signed": {
                "pct_signed": round(signed_count / total * 100, 1) if total else 0,
            },
        },
        "branches": {
            "prefixes": dict(sorted(branch_prefixes.items(), key=lambda x: -x[1])),
            "active_count": active_count,
            "naming_example": examples[0] if examples else None,
        },
        "merge_strategy": {
            "detected": merge_strategy,
            "evidence": merge_evidence,
        },
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="Path to repository")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output")
    args = parser.parse_args(argv)

    try:
        result = analyze(args.repo)
    except Exception as exc:
        result = {"error": str(exc), "script": "git"}

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
