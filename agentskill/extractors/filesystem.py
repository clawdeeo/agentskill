"""Filesystem extraction utilities."""

import json
import os
from pathlib import Path
from typing import Dict, List

from ..constants import EXTENSIONS, LOCKFILES, SKIP_DIRS, HIDDEN_PREFIX, GIT_DIR, TOOL_FILES


def is_hidden_path(root: Path) -> bool:
    """Check if path contains hidden directories."""
    return any(part.startswith(HIDDEN_PREFIX) for part in root.parts)


def should_skip_dir(root: Path) -> bool:
    """Check if directory should be skipped."""
    return bool(SKIP_DIRS.intersection(root.parts))


def is_git_repo(repo_path: str) -> bool:
    """Check if path is a git repository."""
    return os.path.isdir(os.path.join(repo_path, GIT_DIR))


def scan_source_files(repo_path: str) -> Dict[str, List[Path]]:
    """Scan for source files by language."""
    files_by_lang = {lang: [] for lang in EXTENSIONS}

    for root_str, _, files in os.walk(repo_path):
        root = Path(root_str)
        if is_hidden_path(root) or should_skip_dir(root):
            continue

        for file in files:
            filepath = root / file
            for lang, exts in EXTENSIONS.items():
                if any(file.endswith(ext) for ext in exts):
                    files_by_lang[lang].append(filepath)

    return {k: v for k, v in files_by_lang.items() if v}


def analyze_dependency_philosophy(repo_path: str) -> Dict:
    """Analyze dependency management philosophy."""
    repo = Path(repo_path)
    result = {
        "lockfiles": [],
        "pin_style": "unknown",
        "total_deps": 0,
        "dev_deps": 0,
        "manager": "unknown",
    }

    for lf, manager in LOCKFILES.items():
        if (repo / lf).exists():
            result["lockfiles"].append(lf)
            result["manager"] = manager

    pkg = repo / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(errors='ignore'))
            deps = len(data.get("dependencies", {}))
            dev_deps = len(data.get("devDependencies", {}))
            result["total_deps"] += deps
            result["dev_deps"] += dev_deps
            if result["manager"] == "unknown":
                result["manager"] = "npm"
        except Exception:
            pass

    cargo = repo / "Cargo.toml"
    if cargo.exists():
        try:
            content = cargo.read_text(errors='ignore')
            deps = content.count('version =')
            result["total_deps"] += deps
            if result["manager"] == "unknown":
                result["manager"] = "cargo"
        except Exception:
            pass

    reqs = repo / "requirements.txt"
    if reqs.exists():
        try:
            lines = reqs.read_text(errors='ignore').strip().split('\n')
            result["total_deps"] += len([l for l in lines if l.strip() and not l.startswith('#')])
            if result["manager"] == "unknown":
                result["manager"] = "pip"
        except Exception:
            pass

    if result["lockfiles"]:
        result["pin_style"] = "locked"
    elif result["total_deps"] > 0:
        result["pin_style"] = "pinned"
    else:
        result["pin_style"] = "unknown"

    return result


def detect_tooling(repo_path: str) -> Dict:
    """Detect tooling configs (linters, formatters, CI)."""
    repo = Path(repo_path)
    detected = {}

    for file_pattern, tool in TOOL_FILES.items():
        if (repo / file_pattern).exists():
            detected[tool] = True

    if (repo / ".github" / "workflows").exists():
        detected["GitHub Actions CI"] = True

    for lockfile, tool in LOCKFILES.items():
        if (repo / lockfile).exists():
            detected[f"{tool} (locked)"] = True

    test_configs = [
        "pytest.ini", "setup.cfg", "tox.ini", ".pytest_cache",
        "jest.config.js", "vitest.config.ts", "karma.conf.js",
        "Cargo.toml",
        "go.mod",
    ]
    for tc in test_configs:
        if (repo / tc).exists():
            detected["test-framework"] = True
            break

    return detected


def get_project_metadata(repo_path: str) -> Dict:
    """Extract project metadata from common files."""
    repo = Path(repo_path)
    meta = {}

    readme_files = ["README.md", "README.rst", "README.txt", "README"]
    for rf in readme_files:
        if (repo / rf).exists():
            content = (repo / rf).read_text(errors='ignore')[:500]
            lines = content.split('\n')
            if lines:
                meta["project_name"] = lines[0].strip().lstrip('#').strip()
            break

    license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "LICENSE-MIT", "LICENSE-APACHE"]
    for lf in license_files:
        if (repo / lf).exists():
            meta["has_license"] = True
            content = (repo / lf).read_text(errors='ignore')[:500].lower()
            if "mit" in content:
                meta["license_type"] = "MIT"
            elif "apache" in content:
                meta["license_type"] = "Apache-2.0"
            elif "gpl" in content:
                meta["license_type"] = "GPL"
            elif "bsd" in content:
                meta["license_type"] = "BSD"
            break

    return meta
