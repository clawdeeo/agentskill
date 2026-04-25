"""Python language analyzer."""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ..base import LanguageAnalyzer, AnalysisResult
from ...constants import (
    CASE_CAMEL, CASE_KEBAB, CASE_MIXED, CASE_PASCAL,
    CASE_SCREAMING_SNAKE, CASE_SNAKE,
    NAME_VAR, NAME_FUNCTION, NAME_TYPE,
    PYTHON_VAR_KEYWORDS,
)

PYTHON_STDLIB_MODULES = {
    'abc', 'argparse', 'ast', 'asyncio', 'base64', 'bisect', 'calendar',
    'collections', 'configparser', 'contextlib', 'copy', 'csv', 'datetime',
    'decimal', 'difflib', 'email', 'enum', 'faulthandler', 'functools',
    'glob', 'gzip', 'hashlib', 'http', 'importlib', 'inspect', 'io',
    'itertools', 'json', 'logging', 'math', 'multiprocessing', 'operator',
    'os', 'pathlib', 'pickle', 'platform', 'pprint', 'profile', 'queue',
    'random', 're', 'secrets', 'shutil', 'signal', 'socket', 'sqlite3',
    'statistics', 'string', 'struct', 'subprocess', 'sys', 'tempfile',
    'textwrap', 'threading', 'time', 'traceback', 'typing', 'unittest',
    'urllib', 'uuid', 'warnings', 'weakref', 'xml', 'zipfile',
}


class PythonAnalyzer(LanguageAnalyzer):
    """Analyzer for Python source files."""

    PATTERNS = {
        "function_def": r'^def\s+',
        "class_def": r'^class\s+',
        "var_def": r'^\s*\w+\s*=\s*',
        "import_line": r'^(import\s+|from\s+)',
        "comment_line": r'#',
        "doc_comment": r'("""|\'\'\')',
        "doc_comment_end": r'("""|\'\'\')',
        "param_type": r':',
        "return_type": r'->',
    }

    STDLIB_NAMES = PYTHON_STDLIB_MODULES
    VAR_KEYWORDS = PYTHON_VAR_KEYWORDS
    NAMING_CATEGORIES = [NAME_VAR, NAME_FUNCTION, NAME_TYPE]

    ERROR_PATTERNS = [
        (r'^(try|except|finally)\s*:', "try_except"),
        (r'^raise\s+', "raise"),
        (r'^assert\s+', "assert"),
        (r'^with\s+', "with_context"),
    ]

    def get_language_name(self) -> str:
        return "python"

    def detect_case_style(self, name: str) -> str:
        if name.isupper() and '_' in name:
            return CASE_SCREAMING_SNAKE
        if name.islower() and '_' in name:
            return CASE_SNAKE
        if name.islower() and '-' in name:
            return CASE_KEBAB
        if name[0].islower() and '_' not in name and '-' not in name:
            return CASE_CAMEL
        if name[0].isupper() and '_' not in name and '-' not in name:
            return CASE_PASCAL
        return CASE_MIXED

    def categorize_import(self, line: str) -> str:
        stripped = line.strip()
        module = ""
        if stripped.startswith("from "):
            match = re.search(r'from\s+(\S+)', stripped)
            if match:
                module = match.group(1).split('.')[0]
        elif stripped.startswith("import "):
            match = re.search(r'import\s+(\S+)', stripped)
            if match:
                module = match.group(1).split('.')[0]

        if module in PYTHON_STDLIB_MODULES:
            return "stdlib"
        if module.startswith('.'):
            return "local"
        return "third_party"

    def analyze_files(self, files: List[Path]) -> AnalysisResult:
        naming = {cat: {} for cat in self.NAMING_CATEGORIES}
        errors = {key: 0 for _, key in self.ERROR_PATTERNS}
        comments = {"lines": 0, "docstrings": 0, "normal": 0}
        spacing = {"blank_line_counts": []}
        imports = {"stdlib": 0, "third_party": 0, "local": 0}
        metrics = {"total_lines": 0}
        types_aggregate = {
            "total_functions": 0, "annotated_params": 0,
            "total_params": 0, "return_annotations": 0,
        }
        import_orders = []

        for filepath in files[:self.sample_size]:
            lines = self._read_file_lines(filepath)
            if not lines:
                continue

            file_naming = {cat: {} for cat in self.NAMING_CATEGORIES}
            file_errors = {key: 0 for _, key in self.ERROR_PATTERNS}
            file_comments = {"lines": 0, "docstrings": 0, "normal": 0}
            file_spacing = {"blank_line_counts": []}
            file_imports = {"stdlib": 0, "third_party": 0, "local": 0}
            file_metrics = {"total_lines": 0}

            self._analyze_file_lines(
                lines, file_naming, file_errors, file_comments,
                file_spacing, file_imports, file_metrics
            )

            for cat in self.NAMING_CATEGORIES:
                for style, count in file_naming.get(cat, {}).items():
                    naming[cat][style] = naming[cat].get(style, 0) + count

            for key in errors:
                errors[key] += file_errors.get(key, 0)

            for key in ["lines", "docstrings", "normal"]:
                comments[key] += file_comments.get(key, 0)

            spacing["blank_line_counts"].extend(file_spacing.get("blank_line_counts", []))

            for key in imports:
                imports[key] += file_imports.get(key, 0)

            metrics["total_lines"] += file_metrics.get("total_lines", 0)

            # Type annotations
            file_types = self.detect_type_annotations(lines)
            for key in types_aggregate:
                types_aggregate[key] += file_types.get(key, 0)

            # Import order
            order = self.detect_import_order(lines)
            if order["blocks"] > 0:
                import_orders.append(order)

        type_density = types_aggregate["annotated_params"] / max(types_aggregate["total_params"], 1)
        return_density = types_aggregate["return_annotations"] / max(types_aggregate["total_functions"], 1)

        dominant_order = "mixed"
        if import_orders:
            styles = [o["style"] for o in import_orders]
            if styles.count("stdlib_first") > len(styles) / 2:
                dominant_order = "stdlib_first"

        return AnalysisResult(
            naming_patterns=self._format_naming(naming),
            error_handling=errors,
            comments={
                "doc_style": '"""',
                "density": comments["lines"] / max(metrics["total_lines"], 1),
                "docstrings": comments["docstrings"],
                "normal_comments": comments["normal"],
            },
            spacing={
                "avg_blank_lines": self._calculate_avg(spacing["blank_line_counts"]),
            },
            imports=imports,
            metrics={
                "avg_var_length": 0.0,
                "avg_fn_length": 0.0,
            },
            type_annotations={
                "param_density": round(type_density, 2),
                "return_density": round(return_density, 2),
                "total_functions": types_aggregate["total_functions"],
                "total_params": types_aggregate["total_params"],
            },
            import_order={
                "style": dominant_order,
                "separators": sum(o.get("separators", 0) for o in import_orders),
                "blocks": sum(o.get("blocks", 0) for o in import_orders),
            },
            file_count=len(files),
        )

    def _analyze_file_lines(self, lines, naming, errors, comments, spacing, imports, metrics):
        """Analyze lines of a single Python file."""
        prev_was_code = False
        blank_streak = 0
        in_docstring = False

        for line in lines:
            stripped = line.strip()
            metrics["total_lines"] += 1

            if not stripped:
                blank_streak += 1
                continue

            if prev_was_code and blank_streak > 0:
                spacing["blank_line_counts"].append(blank_streak)
            blank_streak = 0
            prev_was_code = True

            # Comments and docstrings
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if in_docstring:
                    in_docstring = False
                else:
                    in_docstring = True
                    comments["docstrings"] += 1
                    comments["lines"] += 1
            elif stripped.startswith('#'):
                comments["normal"] += 1
                comments["lines"] += 1
            elif in_docstring:
                comments["lines"] += 1

            # Error handling patterns
            for pattern, key in self.ERROR_PATTERNS:
                if re.match(pattern, stripped):
                    errors[key] += 1

            # Naming
            self._extract_naming(line, naming)

            # Imports
            if re.match(r'^import\s+', stripped):
                category = self.categorize_import(stripped)
                imports[category] += 1
            elif re.match(r'^from\s+', stripped):
                category = self.categorize_import(stripped)
                imports[category] += 1

    def _extract_naming(self, line: str, naming: Dict):
        stripped = line.strip()

        if re.match(r'^\s*\w+\s*=\s*', line) and not stripped.startswith('#'):
            match = re.match(r'^\s*(\w+)\s*=', line)
            if match and match.group(1) not in self.VAR_KEYWORDS:
                style = self.detect_case_style(match.group(1))
                naming[NAME_VAR][style] = naming[NAME_VAR].get(style, 0) + 1

        if re.match(r'^def\s+', stripped):
            match = re.search(r'def\s+(\w+)', stripped)
            if match:
                style = self.detect_case_style(match.group(1))
                naming[NAME_FUNCTION][style] = naming[NAME_FUNCTION].get(style, 0) + 1

        if re.match(r'^class\s+', stripped):
            match = re.search(r'class\s+(\w+)', stripped)
            if match:
                style = self.detect_case_style(match.group(1))
                naming[NAME_TYPE][style] = naming[NAME_TYPE].get(style, 0) + 1