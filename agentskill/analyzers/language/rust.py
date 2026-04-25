"""Rust language analyzer."""

import re
from pathlib import Path
from typing import Dict, List

from ..base import LanguageAnalyzer, AnalysisResult
from ...constants import (
    CASE_CAMEL, CASE_KEBAB, CASE_MIXED, CASE_PASCAL,
    CASE_SCREAMING_SNAKE, CASE_SNAKE,
    NAME_VAR, NAME_FUNCTION, NAME_TYPE, NAME_CONST,
)

RUST_STDLIB_CRATES = {'std', 'core', 'alloc'}


class RustAnalyzer(LanguageAnalyzer):
    """Analyzer for Rust source files."""

    PATTERNS = {
        "function_def": r'^\s*(pub\s+)?fn\s+',
        "class_def": r'^\s*(pub\s+)?(struct|enum|trait)\s+',
        "const_def": r'^\s*(pub\s+)?const\s+',
        "var_def": r'^\s*let\s+',
        "import_line": r'^\s*use\s+',
        "comment_line": r'^\s*//',
        "doc_comment": r'^\s*///',
        "module_comment": r'^\s*//!',
        "param_type": r':\s*',
        "return_type": r'-\u003e\s*',
    }

    STDLIB_NAMES = RUST_STDLIB_CRATES
    VAR_KEYWORDS = set()
    NAMING_CATEGORIES = [NAME_VAR, NAME_FUNCTION, NAME_TYPE, NAME_CONST]

    ERROR_PATTERNS = [
        (r'unwrap\(\)', "unwrap"),
        (r'expect\(', "expect"),
        (r'\?', "?"),
        (r'panic!', "panic"),
        (r'Result\u003c', "Result"),
    ]

    def get_language_name(self) -> str:
        return "rust"

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
        if 'std::' in stripped or 'core::' in stripped or 'alloc::' in stripped:
            return "stdlib"
        if 'crate::' in stripped:
            return "local"
        if stripped.startswith('use '):
            match = re.search(r'use\s+(\w+)', stripped)
            if match:
                crate = match.group(1)
                if crate in RUST_STDLIB_CRATES:
                    return "stdlib"
        return "third_party"

    def analyze_files(self, files: List[Path]) -> AnalysisResult:
        naming = {cat: {} for cat in self.NAMING_CATEGORIES}
        errors = {key: 0 for _, key in self.ERROR_PATTERNS}
        comments = {"lines": 0, "doc": 0, "normal": 0}
        spacing = {"blank_line_counts": []}
        imports = {"std": 0, "crate": 0, "external": 0}
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
            file_comments = {"lines": 0, "doc": 0, "normal": 0}
            file_spacing = {"blank_line_counts": []}
            file_imports = {"std": 0, "crate": 0, "external": 0}
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

            for key in ["lines", "doc", "normal"]:
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
                "doc_style": "///",
                "density": comments["lines"] / max(metrics["total_lines"], 1),
                "doc_comments": comments["doc"],
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
        """Analyze lines of a single Rust file."""
        prev_was_code = False
        blank_streak = 0

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

            # Comments
            if stripped.startswith('///') or stripped.startswith('//!'):
                comments["doc"] += 1
                comments["lines"] += 1
            elif stripped.startswith('//') and not stripped.startswith('///'):
                comments["normal"] += 1
                comments["lines"] += 1

            # Error patterns
            for pattern, key in self.ERROR_PATTERNS:
                if re.search(pattern, stripped):
                    errors[key] += 1

            # Naming
            self._extract_naming(line, naming)

            # Imports
            if stripped.startswith('use '):
                category = self.categorize_import(stripped)
                if category == "stdlib":
                    imports["std"] += 1
                elif category == "local":
                    imports["crate"] += 1
                else:
                    imports["external"] += 1

    def _extract_naming(self, line: str, naming: Dict):
        stripped = line.strip()

        if 'let ' in line:
            match = re.search(r'let\s+(?:mut\s+)?(\w+)', line)
            if match:
                style = self.detect_case_style(match.group(1))
                naming[NAME_VAR][style] = naming[NAME_VAR].get(style, 0) + 1

        if 'fn ' in stripped:
            match = re.search(r'fn\s+(\w+)', stripped)
            if match:
                style = self.detect_case_style(match.group(1))
                naming[NAME_FUNCTION][style] = naming[NAME_FUNCTION].get(style, 0) + 1

        if re.search(r'(?:struct|enum|trait)\s+', stripped):
            match = re.search(r'(?:struct|enum|trait)\s+(\w+)', stripped)
            if match:
                style = self.detect_case_style(match.group(1))
                naming[NAME_TYPE][style] = naming[NAME_TYPE].get(style, 0) + 1

        if 'const ' in stripped:
            match = re.search(r'const\s+(\w+)', stripped)
            if match:
                style = self.detect_case_style(match.group(1))
                naming[NAME_CONST][style] = naming[NAME_CONST].get(style, 0) + 1