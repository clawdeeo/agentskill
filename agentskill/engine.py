"""Language-agnostic code analysis engine.

Extracts patterns from any codebase by treating files as text.
Detects naming conventions, comments, spacing, imports, errors
without language-specific logic.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Optional


ERROR_PATTERNS: List[Tuple[str, str]] = [
    (r'\?\s*$', "try_operator"),
    (r'try\s*{|try\s*:', "try_block"),
    (r'catch|except', "catch_block"),
    (r'throw|raise|panic!', "throw"),
    (r'\.unwrap\(\)', "unwrap"),
    (r'\.expect\(', "expect"),
]

EXT_TO_COMMENT: Dict[str, str] = {
    '.py': '#', '.rb': '#', '.sh': '#', '.bash': '#', '.zsh': '#',
    '.pl': '#', '.pm': '#', '.r': '#', '.awk': '#', '.sed': '#',
    '.rs': '//', '.go': '//', '.js': '//', '.ts': '//', '.mjs': '//',
    '.java': '//', '.kt': '//', '.swift': '//', '.c': '//', '.cpp': '//',
    '.cc': '//', '.h': '//', '.hpp': '//', '.cs': '//', '.scala': '//',
    '.php': '//', '.lua': '--', '.sql': '--', '.vim': '"',
    '.hs': '--', '.ml': '(*', '.clj': ';;', '.ex': '#',
}

EXT_TO_LANG: Dict[str, str] = {
    '.py': 'python', '.rs': 'rust', '.go': 'go',
    '.js': 'javascript', '.ts': 'typescript', '.mjs': 'javascript',
    '.java': 'java', '.kt': 'kotlin', '.swift': 'swift',
    '.c': 'c', '.cpp': 'cpp', '.cc': 'cpp', '.h': 'c', '.hpp': 'cpp',
    '.rb': 'ruby', '.php': 'php', '.cs': 'csharp',
    '.scala': 'scala', '.clj': 'clojure', '.ex': 'elixir',
    '.hs': 'haskell', '.ml': 'ocaml', '.r': 'r',
    '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash',
    '.lua': 'lua', '.vim': 'vim',
    '.pl': 'perl', '.pm': 'perl',
}


@dataclass
class AnalysisResult:
    """Result of analyzing a codebase."""
    languages: Dict[str, Dict] = field(default_factory=dict)
    git: Dict = field(default_factory=dict)
    structure: Dict = field(default_factory=dict)
    tooling: Dict = field(default_factory=dict)
    commands: Dict = field(default_factory=dict)
    dependencies: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)


def detect_case_style(name: str) -> str:
    """Detect naming case style from a string."""
    if not name or not isinstance(name, str):
        return "unknown"

    if name.isupper() and '_' in name:
        return "SCREAMING_SNAKE_CASE"
    if name.islower() and '_' in name:
        return "snake_case"
    if name.islower() and '-' in name:
        return "kebab-case"
    if name[0].islower() and '_' not in name and '-' not in name:
        has_upper = any(c.isupper() for c in name[1:])
        return "camelCase" if has_upper else "snake_case"
    if name[0].isupper() and '_' not in name and '-' not in name:
        has_lower = any(c.islower() for c in name[1:])
        return "PascalCase" if has_lower else "SCREAMING_SNAKE_CASE"

    return "mixed"


def extract_identifiers(line: str) -> List[str]:
    """Extract potential identifiers from a line of code."""
    patterns = [
        r'(?:let|var|const|def|fn|func|function)\s+(mut\s+)?(\w+)',
        r'(?:struct|class|enum|trait|type|interface)\s+(\w+)',
        r'(?:use|import)\s+(?:[\w\.]*)?(\w+)',
        r'(\w+)\s*[=:]\s*[^=]',
    ]

    identifiers = []
    for pattern in patterns:
        for match in re.finditer(pattern, line):
            groups = match.groups()
            name = groups[-1] if groups else None
            if name and len(name) > 1 and not name.isdigit():
                identifiers.append(name)

    return identifiers


def analyze_file_content(filepath: Path, content: str) -> Dict:
    """Analyze a single file's content for patterns."""
    lines = content.split('\n')
    total_lines = len(lines)

    naming = {"vars": {}, "functions": {}, "types": {}, "consts": {}}
    comments = {"total": 0, "doc": 0, "normal": 0, "density": 0.0}
    spacing = {"blank_lines": 0, "avg_between_blocks": 0.0}
    imports = {"stdlib": 0, "third_party": 0, "local": 0}
    errors = {}

    blank_line_counts = []
    current_blank_streak = 0
    in_doc_comment = False
    doc_comment_marker = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            current_blank_streak += 1
            continue

        if current_blank_streak > 0:
            blank_line_counts.append(current_blank_streak)
            current_blank_streak = 0

        if in_doc_comment:
            comments["total"] += 1
            comments["doc"] += 1
            if doc_comment_marker and doc_comment_marker in stripped:
                in_doc_comment = False
                doc_comment_marker = None
        elif stripped.startswith('///') or stripped.startswith('//!'):
            comments["doc"] += 1
            comments["total"] += 1
        elif stripped.startswith('/*'):
            comments["doc"] += 1
            comments["total"] += 1
            if '*/' not in stripped:
                in_doc_comment = True
                doc_comment_marker = '*/'
        elif stripped.startswith('"""') or stripped.startswith("'''"):
            comments["doc"] += 1
            comments["total"] += 1
            quote = '"""' if stripped.startswith('"""') else "'''"
            if stripped.count(quote) < 2:
                in_doc_comment = True
                doc_comment_marker = quote
        elif stripped.startswith('//') or stripped.startswith('#'):
            comments["normal"] += 1
            comments["total"] += 1

        identifiers = extract_identifiers(line)
        for name in identifiers:
            style = detect_case_style(name)

            if re.search(r'\b(const|static)\b', line, re.I):
                naming["consts"][style] = naming["consts"].get(style, 0) + 1
            elif re.search(r'\b(struct|class|enum|trait|interface|type)\b', line):
                naming["types"][style] = naming["types"].get(style, 0) + 1
            elif re.search(r'\b(def|fn|func|function)\b', line):
                naming["functions"][style] = naming["functions"].get(style, 0) + 1
            elif style == "SCREAMING_SNAKE_CASE" and re.match(r'^\s*' + re.escape(name) + r'\s*[=:]', line):
                naming["consts"][style] = naming["consts"].get(style, 0) + 1
            else:
                naming["vars"][style] = naming["vars"].get(style, 0) + 1

        if re.match(r'^(import|from|use|require|include)\s+', stripped):
            if '.' in stripped and not re.search(r'\d', stripped.split()[-1]):
                imports["local"] += 1
            elif any(std in stripped for std in ['std', 'os', 'sys', 'io', 'fmt']):
                imports["stdlib"] += 1
            else:
                imports["third_party"] += 1

        for pattern, key in ERROR_PATTERNS:
            if re.search(pattern, stripped):
                errors[key] = errors.get(key, 0) + 1

    code_lines = total_lines - comments["total"] - sum(blank_line_counts)
    if code_lines > 0:
        comments["density"] = comments["total"] / code_lines

    if blank_line_counts:
        spacing["blank_lines"] = sum(blank_line_counts)
        spacing["avg_between_blocks"] = sum(blank_line_counts) / len(blank_line_counts)

    return {
        "naming": {k: _add_dominant(v) for k, v in naming.items()},
        "comments": comments,
        "spacing": spacing,
        "imports": imports,
        "error_handling": errors,

        "metrics": {
            "total_lines": total_lines,
            "code_lines": code_lines,
        }
    }


def _add_dominant(style_counts: Dict[str, int]) -> Dict:
    """Add dominant case style to a counts dict."""
    if not style_counts:
        return {"dominant_case": "unknown", "counts": {}}
    dominant = max(style_counts.items(), key=lambda x: x[1])
    return {
        "dominant_case": dominant[0],
        "counts": style_counts,
    }


def extract_code_examples(files: List[Path], max_examples: int = 10) -> List[str]:
    """Extract representative code examples from files."""
    examples = []

    for filepath in files[:max_examples]:
        try:
            content = filepath.read_text(errors='ignore')
            lines = content.split('\n')

            interesting = []
            for i, line in enumerate(lines):
                if any(kw in line for kw in ['def ', 'fn ', 'func ', 'function ',
                                              'class ', 'struct ', 'enum ', 'trait ']):
                    context = []
                    if i > 0:
                        context.append(lines[i-1].rstrip())
                    context.append(line.rstrip())
                    if i < len(lines) - 1:
                        context.append(lines[i+1].rstrip())
                    interesting.append('\n'.join(context))

            if interesting:
                comment = EXT_TO_COMMENT.get(filepath.suffix, '//')
                examples.append(f"{comment} From {filepath.name}:\n" + interesting[0])
        except Exception:
            continue

    return examples[:max_examples]


def analyze_codebase(repo_path: str, files_by_ext: Dict[str, List[Path]]) -> AnalysisResult:
    """Analyze a codebase given files grouped by extension."""
    languages = {}
    all_files = []

    for ext, files in files_by_ext.items():
        if not files:
            continue

        lang = EXT_TO_LANG.get(ext, ext.lstrip('.') if ext else 'unknown')
        lang_data = {
            "naming": {"vars": {}, "functions": {}, "types": {}, "consts": {}},
            "comments": {"total": 0, "doc": 0, "normal": 0},
            "spacing": {"blank_lines": 0, "avg_between_blocks": 0.0},
            "imports": {"stdlib": 0, "third_party": 0, "local": 0},
            "error_handling": {},
            "metrics": {"total_lines": 0, "file_count": 0},
        }

        for filepath in files[:50]:
            try:
                content = filepath.read_text(errors='ignore')
                file_analysis = analyze_file_content(filepath, content)

                for category in ["vars", "functions", "types", "consts"]:
                    for style, count in file_analysis["naming"].get(category, {}).get("counts", {}).items():
                        current = lang_data["naming"][category].get(style, 0)
                        lang_data["naming"][category][style] = current + count

                for key in ["total", "doc", "normal"]:
                    lang_data["comments"][key] += file_analysis["comments"].get(key, 0)

                for key in ["stdlib", "third_party", "local"]:
                    lang_data["imports"][key] += file_analysis["imports"].get(key, 0)

                for key, count in file_analysis["error_handling"].items():
                    lang_data["error_handling"][key] = lang_data["error_handling"].get(key, 0) + count

                lang_data["metrics"]["total_lines"] += file_analysis["metrics"].get("total_lines", 0)
                lang_data["metrics"]["file_count"] += 1
                all_files.append(filepath)
            except Exception:
                continue

        for category in ["vars", "functions", "types", "consts"]:
            lang_data["naming"][category] = _add_dominant(lang_data["naming"][category])

        total_lines = lang_data["metrics"]["total_lines"]
        comment_lines = lang_data["comments"]["total"]
        if total_lines > comment_lines:
            lang_data["comments"]["density"] = comment_lines / (total_lines - comment_lines)

        languages[lang] = lang_data

    examples = extract_code_examples(all_files, max_examples=15)

    return AnalysisResult(
        languages=languages,
        examples=examples,
    )
