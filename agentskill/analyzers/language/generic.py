"""Generic language analyzer for languages without specific analyzers."""

from pathlib import Path
from typing import Dict, List, Any

from ..base import LanguageAnalyzer, AnalysisResult


class GenericAnalyzer(LanguageAnalyzer):
    """Generic analyzer for any language - uses file-level heuristics."""

    def __init__(self, language: str, sample_size: int = 30):
        super().__init__(sample_size)
        self.language = language

    def get_language_name(self) -> str:
        return self.language

    def detect_case_style(self, name: str) -> str:
        """Simple heuristic-based detection."""
        if name.isupper() and '_' in name:
            return "SCREAMING_SNAKE_CASE"
        if name.islower() and '_' in name:
            return "snake_case"
        if name.islower() and '-' in name:
            return "kebab-case"
        if name[0].islower():
            return "camelCase"
        if name[0].isupper():
            return "PascalCase"
        return "mixed"

    def analyze_files(self, files: List[Path]) -> AnalysisResult:
        """Generic analysis based on file patterns."""
        line_counts = []
        comment_lines = 0
        blank_lines = 0
        code_lines = 0

        for filepath in files[:self.sample_size]:
            try:
                content = filepath.read_text(errors='ignore')
                lines = content.split('\n')
                line_counts.append(len(lines))

                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        blank_lines += 1
                    elif stripped.startswith('//') or stripped.startswith('#') or stripped.startswith('/*'):
                        comment_lines += 1
                    else:
                        code_lines += 1
            except Exception:
                continue

        total_lines = sum(line_counts)
        avg_file_lines = total_lines / len(files) if files else 0

        return AnalysisResult(
            naming_patterns={
                "vars": {"dominant_case": "unknown", "counts": {}},
                "functions": {"dominant_case": "unknown", "counts": {}},
                "types": {"dominant_case": "unknown", "counts": {}},
            },
            error_handling={"note": "generic analyzer - no specific error patterns detected"},
            comments={
                "comment_lines": comment_lines,
                "code_lines": code_lines,
                "density": comment_lines / max(code_lines, 1),
            },
            spacing={
                "avg_blank_lines": blank_lines / max(len(files), 1),
            },
            imports={},
            metrics={
                "avg_file_lines": avg_file_lines,
                "total_lines": total_lines,
            },
            type_annotations={},
            import_order={"style": "unknown"},
            file_count=len(files),
        )
