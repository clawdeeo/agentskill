"""Repository structure and convention extraction."""

import os
from pathlib import Path
from typing import Dict, List, Optional

FILE_NAMING_PATTERNS = {
    "snake_case": lambda f: '_' in f and f == f.lower() and not f.startswith('.'),
    "kebab-case": lambda f: '-' in f and f == f.lower() and not f.startswith('.'),
    "camelCase": lambda f: f[0].islower() and any(c.isupper() for c in f) and not f.startswith('.'),
    "PascalCase": lambda f: f[0].isupper() and not f.startswith('.'),
}

SOURCE_DIRS = {
    "src", "lib", "app", "pkg", "cmd", "internal",
    "core", "engine", "domain", "infra", "api",
}

TEST_DIR_MARKERS = {
    "test", "tests", "spec", "specs", "__tests__",
}

CONFIG_DIRS = {
    ".github", "config", "configs", "conf", "deploy", "deployment", "infra",
}

DOC_DIRS = {
    "docs", "doc", "documentation", "examples",
}

SCRIPT_DIRS = {
    "scripts", "script", "bin", "tools",
}

ASSET_DIRS = {
    "assets", "static", "public", "resources", "templates",
}


def extract_repo_structure(repo_path: str) -> Dict:
    """Extract repository directory structure and conventions."""
    repo = Path(repo_path)
    result = {
        "structure": {},
        "file_naming": {},
        "test_patterns": {},
        "module_patterns": {},
        "depth_stats": {},
    }

    if not repo.is_dir():
        return result

    structure = _scan_structure(repo, repo, depth=0, max_depth=4)
    result["structure"] = structure

    result["file_naming"] = _analyze_file_naming(repo)
    result["test_patterns"] = _analyze_test_patterns(repo, structure)
    result["module_patterns"] = _analyze_module_patterns(repo, structure)
    result["depth_stats"] = _analyze_depth(repo)

    return result


def _scan_structure(repo: Path, current: Path, depth: int, max_depth: int) -> Dict:
    """Recursively scan directory structure."""
    if depth > max_depth:
        return {"_truncated": True}

    result = {}
    try:
        entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return {"_error": "permission denied"}

    dirs = [e for e in entries if e.is_dir() and not e.name.startswith('.')]
    files = [e for e in entries if e.is_file() and not e.name.startswith('.')]

    result["_files"] = len(files)
    result["_dirs"] = len(dirs)

    for d in dirs:
        result[d.name] = _scan_structure(repo, d, depth + 1, max_depth)

    return result


def _analyze_file_naming(repo: Path) -> Dict:
    """Analyze file naming conventions across the repo."""
    style_counts = {style: 0 for style in FILE_NAMING_PATTERNS}
    total = 0
    extensions = {}

    for root, _, files in os.walk(repo):
        root_path = Path(root)
        if any(part.startswith('.') for part in root_path.parts) or \
           any(skip in root_path.parts for skip in {'node_modules', 'target', '__pycache__', 'vendor', 'dist', 'build'}):
            continue

        for f in files:
            if f.startswith('.'):
                continue

            stem = Path(f).stem
            if not stem:
                continue

            ext = Path(f).suffix
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1

            matched = False
            for style, check in FILE_NAMING_PATTERNS.items():
                if check(stem):
                    style_counts[style] += 1
                    matched = True
                    break

            if not matched:
                style_counts["mixed"] = style_counts.get("mixed", 0) + 1
            total += 1

    if total == 0:
        return {"dominant": "unknown", "counts": {}, "total": 0}

    dominant = max(style_counts, key=lambda k: style_counts.get(k, 0))

    return {
        "dominant": dominant,
        "counts": {k: v for k, v in style_counts.items() if v > 0},
        "total": total,
        "extensions": dict(sorted(extensions.items(), key=lambda x: -x[1])[:10]),
    }


def _analyze_test_patterns(repo: Path, structure: Dict) -> Dict:
    """Detect test organization and patterns."""
    result = {
        "test_dirs": [],
        "test_file_patterns": {},
        "test_framework": [],
        "test_location": "unknown",
    }

    test_dirs = []
    test_file_patterns = {}
    for root, _, files in os.walk(repo):
        root_path = Path(root)
        if any(part.startswith('.') for part in root_path.parts):
            continue

        dir_name = root_path.name.lower()
        if dir_name in TEST_DIR_MARKERS or dir_name.endswith('test') or dir_name.endswith('tests'):
            test_dirs.append(str(root_path.relative_to(repo)))

        for f in files:
            lower = f.lower()
            if 'test' in lower or 'spec' in lower:
                stem = Path(f).stem
                if stem.startswith('test_'):
                    test_file_patterns["test_*.ext"] = test_file_patterns.get("test_*.ext", 0) + 1
                elif stem.endswith('_test'):
                    test_file_patterns["*_test.ext"] = test_file_patterns.get("*_test.ext", 0) + 1
                elif stem.endswith('.test'):
                    test_file_patterns["*.test.ext"] = test_file_patterns.get("*.test.ext", 0) + 1
                elif stem.endswith('.spec'):
                    test_file_patterns["*.spec.ext"] = test_file_patterns.get("*.spec.ext", 0) + 1
                elif 'test' in stem:
                    test_file_patterns["*test*.ext"] = test_file_patterns.get("*test*.ext", 0) + 1

    result["test_dirs"] = sorted(set(test_dirs))
    result["test_file_patterns"] = test_file_patterns

    if test_dirs and not any('__test__' in d for d in test_dirs):
        result["test_location"] = "separate_dirs"
    elif test_file_patterns:
        result["test_location"] = "colocated"

    frameworks = []
    framework_markers = {
        "pytest.ini": "pytest",
        "setup.cfg": "pytest",
        "pyproject.toml": "pytest",
        "tox.ini": "tox",
        "jest.config.js": "jest",
        "jest.config.ts": "jest",
        "vitest.config.ts": "vitest",
        "vitest.config.js": "vitest",
        "karma.conf.js": "karma",
        "Cargo.toml": "cargo test",
        "go.mod": "go test",
        "Gemfile": "rspec",
        "Makefile": "make test",
        "justfile": "just test",
    }
    for marker, framework in framework_markers.items():
        if (repo / marker).exists():
            frameworks.append(framework)

    result["test_framework"] = frameworks

    return result


def _analyze_module_patterns(repo: Path, structure: Dict) -> Dict:
    """Detect module organization patterns."""
    result = {
        "has_index_files": False,
        "has_barrel_files": False,
        "has_init_files": False,
        "source_dirs": [],
        "config_dirs": [],
    }

    index_markers = {"index.js", "index.ts", "index.mjs", "index.cjs"}
    barrel_markers = {"mod.rs", "lib.rs"}
    init_markers = {"__init__.py", "__init__.lua"}

    for root, _, files in os.walk(repo):
        root_path = Path(root)
        if any(part.startswith('.') for part in root_path.parts):
            continue

        file_set = set(files)
        if index_markers & file_set:
            result["has_index_files"] = True
        if barrel_markers & file_set:
            result["has_barrel_files"] = True
        if init_markers & file_set:
            result["has_init_files"] = True

    for d in sorted(repo.iterdir()):
        if d.is_dir() and not d.name.startswith('.'):
            if d.name in SOURCE_DIRS:
                result["source_dirs"].append(d.name)
            elif d.name in CONFIG_DIRS:
                result["config_dirs"].append(d.name)

    return result


def _analyze_depth(repo: Path) -> Dict:
    """Analyze directory depth distribution."""
    depths = []
    for root, _, files in os.walk(repo):
        root_path = Path(root)
        if any(part.startswith('.') for part in root_path.parts):
            continue
        depth = len(root_path.relative_to(repo).parts)
        if depth > 0:
            depths.append(depth)

    if not depths:
        return {"max": 0, "avg": 0}

    return {
        "max": max(depths),
        "avg": round(sum(depths) / len(depths), 1),
    }
