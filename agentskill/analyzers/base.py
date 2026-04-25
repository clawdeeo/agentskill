"""Base analyzer interface with generic analysis loop."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple


@dataclass
class AnalysisResult:
    """Result of analyzing a source file or set of files."""
    naming_patterns: Dict[str, Any]
    error_handling: Dict[str, Any]
    comments: Dict[str, Any]
    spacing: Dict[str, Any]
    imports: Dict[str, Any]
    metrics: Dict[str, float]
    type_annotations: Dict[str, Any] = field(default_factory=dict)
    import_order: Dict[str, Any] = field(default_factory=dict)
    file_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "naming": self.naming_patterns,
            "error_handling": self.error_handling,
            "comments": self.comments,
            "spacing": self.spacing,
            "imports": self.imports,
            "metrics": self.metrics,
            "type_annotations": self.type_annotations,
            "import_order": self.import_order,
            "file_count": self.file_count,
        }


IMPORT_ORDER_STYLES = {
    "stdlib_first": "stdlib -> third-party -> local (separated by blank lines)",
    "mixed": "No consistent import ordering",
    "grouped": "Grouped by module but not separated by category",
}


class LanguageAnalyzer(ABC):
    """Abstract base class for language-specific analyzers.

    Language analyzers provide configuration via class attributes and method
    overrides. The base class handles the analysis loop generically.

    To add a new language, subclass and override:
    - get_language_name()
    - PATTERNS dict (regex patterns for this language)
    - STDLIB_NAMES set (standard library module names)
    - VAR_KEYWORDS set (keywords to exclude from variable naming)
    - detect_case_style(name)
    - categorize_import(line) [optional, if language has imports]
    """

    # Regex patterns for this language. Override in subclasses.
    PATTERNS = {
        "function_def": r"",
        "class_def": r"",
        "const_def": r"",
        "var_def": r"",
        "import_line": r"",
        "comment_line": r"",
        "doc_comment": r"",
        "doc_comment_end": r"",
    }

    # Standard library names for import categorization.
    STDLIB_NAMES: Set[str] = set()

    # Keywords that look like variable names but aren't.
    VAR_KEYWORDS: Set[str] = set()

    # Naming categories to track.
    NAMING_CATEGORIES: List[str] = ["vars", "functions", "types"]

    # Error patterns as (regex, key) pairs.
    ERROR_PATTERNS: List[Tuple[str, str]] = []

    def __init__(self, sample_size: int = 30):
        self.sample_size = sample_size

    @abstractmethod
    def analyze_files(self, files: List[Path]) -> AnalysisResult:
        """Analyze a list of source files and return style metrics."""
        pass

    @abstractmethod
    def detect_case_style(self, name: str) -> str:
        """Detect the naming case style of a string."""
        pass

    @abstractmethod
    def get_language_name(self) -> str:
        """Return the language name."""
        pass

    def _read_file_lines(self, filepath: Path, max_lines: int = 1000) -> List[str]:
        """Safely read file and return lines."""
        try:
            content = filepath.read_text(errors='ignore')
            lines = content.split('\n')
            return lines[:max_lines]
        except Exception:
            return []

    def _calculate_avg(self, values: List[float]) -> float:
        """Calculate average, handling empty lists."""
        return sum(values) / len(values) if values else 0.0

    def _get_top_items(self, counts: Dict[str, int], n: int = 3) -> Dict[str, int]:
        """Get top n items by count."""
        return dict(sorted(counts.items(), key=lambda x: -x[1])[:n])

    def detect_import_order(self, lines: List[str]) -> Dict:
        """Detect import ordering style from file lines."""
        import_pattern = self.PATTERNS.get("import_line", "")
        if not import_pattern:
            return {"style": "unknown", "separators": 0, "blocks": 0}

        import_blocks = []
        current_block = []
        prev_was_blank = False

        for line in lines:
            stripped = line.strip()

            if re.match(import_pattern, stripped):
                category = self.categorize_import(stripped)
                current_block.append(category)
                prev_was_blank = False
            elif not stripped:
                if current_block:
                    prev_was_blank = True
                continue
            else:
                if current_block:
                    import_blocks.append({
                        "imports": current_block,
                        "had_separator": prev_was_blank,
                    })
                    current_block = []
                prev_was_blank = False

        if current_block:
            import_blocks.append({
                "imports": current_block,
                "had_separator": False,
            })

        if not import_blocks:
            return {"style": "unknown", "separators": 0, "blocks": 0}

        separators = sum(1 for b in import_blocks if b["had_separator"])

        all_imports = []
        for block in import_blocks:
            all_imports.extend(block["imports"])

        category_order = {"stdlib": 0, "third_party": 1, "local": 2}
        ordered_transitions = 0
        out_of_order = 0

        for i in range(1, len(all_imports)):
            prev_cat = category_order.get(all_imports[i - 1], 1)
            curr_cat = category_order.get(all_imports[i], 1)
            if curr_cat >= prev_cat:
                ordered_transitions += 1
            else:
                out_of_order += 1

        total_transitions = ordered_transitions + out_of_order
        if total_transitions == 0:
            style = "unknown"
        elif out_of_order == 0 and separators > 0:
            style = "stdlib_first"
        elif out_of_order == 0:
            style = "grouped"
        else:
            style = "mixed"

        return {
            "style": style,
            "separators": separators,
            "blocks": len(import_blocks),
            "description": IMPORT_ORDER_STYLES.get(style, style),
        }

    def categorize_import(self, line: str) -> str:
        """Categorize an import line as stdlib, third_party, or local.

        Override in subclasses for language-specific categorization.
        """
        return "third_party"

    def detect_type_annotations(self, lines: List[str]) -> Dict:
        """Detect type annotation density from file lines.

        Uses PATTERNS["function_def"], PATTERNS["param_type"],
        and PATTERNS["return_type"] if available.
        """
        fn_pattern = self.PATTERNS.get("function_def", "")
        if not fn_pattern:
            return {
                "total_functions": 0,
                "annotated_params": 0,
                "total_params": 0,
                "return_annotations": 0,
                "param_density": 0.0,
                "return_density": 0.0,
            }

        total_functions = 0
        annotated_params = 0
        total_params = 0
        return_annotations = 0

        for line in lines:
            stripped = line.strip()
            if not re.match(fn_pattern, stripped):
                continue

            total_functions += 1

            paren_content = re.search(r'\((.+?)\)', stripped)
            if paren_content:
                param_str = paren_content.group(1)
                total_params += param_str.count(',') + 1
                # Count type annotations (colons in params)
                param_type_pattern = self.PATTERNS.get("param_type", r":")
                annotated_params += len(re.findall(param_type_pattern, param_str))

            return_pattern = self.PATTERNS.get("return_type", "")
            if return_pattern and re.search(return_pattern, stripped):
                return_annotations += 1

        return {
            "total_functions": total_functions,
            "annotated_params": annotated_params,
            "total_params": max(total_params, 0),
            "return_annotations": return_annotations,
            "param_density": round(annotated_params / max(total_params, 1), 2),
            "return_density": round(return_annotations / max(total_functions, 1), 2),
        }

    def _format_naming(self, naming: Dict) -> Dict:
        """Format naming patterns with dominance info."""
        result = {}
        for category, styles in naming.items():
            if styles:
                dominant = max(styles.items(), key=lambda x: x[1])
                result[category] = {
                    "dominant_case": dominant[0],
                    "counts": styles,
                }
            else:
                result[category] = {"dominant_case": "unknown", "counts": {}}
        return result