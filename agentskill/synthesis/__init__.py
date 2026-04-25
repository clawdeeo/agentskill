"""AGENTS.md synthesis from analysis results."""

from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class SynthesisConfig:
    """Configuration for AGENTS.md generation."""
    include_overview: bool = True
    include_cross_language: bool = True
    include_git: bool = True
    include_tooling: bool = True
    include_red_lines: bool = True
    include_structure: bool = True
    include_commands: bool = True
    confidence_threshold: float = 0.6
    max_examples_per_section: int = 3

class AgentSynthesizer:
    """Synthesizes AGENTS.md from analysis results."""

    def __init__(self, config: SynthesisConfig = None):
        self.config = config or SynthesisConfig()

    def synthesize(self, analyses: List[Dict], repos: List[str]) -> str:
        """Generate AGENTS.md content from analysis results."""
        sections = []

        if self.config.include_overview:
            sections.append(self._generate_overview(analyses, repos))

        if self.config.include_cross_language:
            sections.append(self._generate_cross_language(analyses))

        sections.append(self._generate_language_sections(analyses))

        if self.config.include_structure:
            sections.append(self._generate_structure_section(analyses))

        if self.config.include_commands:
            sections.append(self._generate_commands_section(analyses))

        if self.config.include_git:
            sections.append(self._generate_git_section(analyses))

        if self.config.include_tooling:
            sections.append(self._generate_tooling_section(analyses))

        sections.append(self._generate_dependencies_section(analyses))

        if self.config.include_red_lines:
            sections.append(self._generate_red_lines(analyses))

        sections.append(self._generate_examples_section(analyses))

        sections.append(self._generate_footer(analyses, repos))

        return "\n\n".join(sections)

    def _generate_examples_section(self, analyses: List[Dict]) -> str:
        """Generate Code Examples section from actual codebase."""
        lines = [
            "## Code Examples",
            "",
            "Actual patterns from the codebase:",
            "",
        ]
        
        all_examples = []
        for analysis in analyses:
            examples = analysis.get("examples", [])
            all_examples.extend(examples)
        
        if not all_examples:
            lines.append("*No representative examples extracted.*")
            return "\n".join(lines)
        
        for i, example in enumerate(all_examples[:10], 1):
            lines.append(f"### Example {i}")
            lines.append("")
            lines.append("```")
            lines.append(example)
            lines.append("```")
            lines.append("")
        
        return "\n".join(lines)

    def _generate_overview(self, analyses: List[Dict], repos: List[str]) -> str:
        """Generate overview section."""
        languages = self._detected_languages(analyses)
        lang_str = ", ".join(sorted(languages)) if languages else "various languages"

        repo_count = len(repos)
        repo_desc = f"{repo_count} repositories" if repo_count > 1 else "1 repository"

        lines = [
            "# AGENTS.md — Coding Style",
            "",
            "## Overview",
            "",
            f"Multi-language codebase spanning {lang_str}. Analyzed {repo_desc}.",
            "",
            "Key principles distilled from actual patterns:",
        ]

        principles = self._extract_key_principles(analyses)
        for principle in principles[:3]:
            lines.append(f"- {principle}")

        return "\n".join(lines)

    def _generate_cross_language(self, analyses: List[Dict]) -> str:
        """Generate cross-language patterns section."""
        lines = [
            "## Cross-Language Patterns",
            "",
            "Patterns holding across all detected languages:",
        ]

        patterns = self._find_common_patterns(analyses)
        if patterns.get("naming"):
            lines.append("")
            lines.append("### Naming")
            for name_type, style in patterns["naming"].items():
                lines.append(f"- **{name_type}:** {style}")

        if patterns.get("comments"):
            lines.append("")
            lines.append("### Comments")
            lines.append(f"- **Philosophy:** {patterns['comments']}")

        if patterns.get("error_handling"):
            lines.append("")
            lines.append("### Error Handling")
            lines.append(f"- {patterns['error_handling']}")

        if patterns.get("spacing"):
            lines.append("")
            lines.append("### Spacing")
            lines.append(f"- {patterns['spacing']}")

        return "\n".join(lines)

    def _generate_language_sections(self, analyses: List[Dict]) -> str:
        """Generate per-language sections."""
        sections = []
        all_langs = self._detected_languages(analyses)

        for lang in sorted(all_langs):
            lang_sections = []
            for analysis in analyses:
                if lang in analysis.get("languages", {}):
                    lang_data = analysis["languages"][lang]
                    lang_sections.append(self._format_language_section(lang, lang_data))

            if lang_sections:
                sections.append(f"\n## {lang.title()}\n")
                sections.append("\n\n".join(lang_sections))

        return "".join(sections)

    def _format_language_section(self, lang: str, data: Dict) -> str:
        """Format a single language section."""
        lines = []

        naming = data.get("naming", {})
        if naming:
            lines.append("### Naming")
            for category, info in naming.items():
                if isinstance(info, dict):
                    dominant = info.get("dominant_case", "unknown")
                    lines.append(f"- **{category.title()}:** {dominant}")

        type_annotations = data.get("type_annotations", {})
        if type_annotations and type_annotations.get("total_functions", 0) > 0:
            lines.append("")
            lines.append("### Type Annotations")
            density = type_annotations.get("param_density", 0)
            return_density = type_annotations.get("return_density", 0)
            if density > 0.5:
                lines.append(f"- **Param density:** High ({density:.0%})")
            elif density > 0.2:
                lines.append(f"- **Param density:** Medium ({density:.0%})")
            else:
                lines.append(f"- **Param density:** Low ({density:.0%})")
            lines.append(f"- **Return density:** {return_density:.0%}")

        import_order = data.get("import_order", {})
        if import_order and import_order.get("style"):
            style = import_order["style"]
            if style != "unknown":
                lines.append("")
                lines.append("### Import Order")
                lines.append(f"- **Style:** {style}")

        errors = data.get("error_handling", {})
        if errors and not errors.get("note"):
            lines.append("")
            lines.append("### Error Handling")
            for pattern, count in errors.items():
                if isinstance(count, int) and count > 0:
                    lines.append(f"- `{pattern}`: {count} occurrences")

        comments = data.get("comments", {})
        if comments:
            lines.append("")
            lines.append("### Comments")
            density = comments.get("density", 0)
            if density > 0:
                lines.append(f"- **Density:** {density:.1%}")
            if "doc_style" in comments:
                lines.append(f"- **Style:** `{comments['doc_style']}`")

        spacing = data.get("spacing", {})
        if spacing:
            avg_blanks = spacing.get("avg_blank_lines", 0)
            if avg_blanks > 0:
                lines.append("")
                lines.append("### Spacing")
                lines.append(f"- **Avg blank lines between blocks:** {avg_blanks:.1f}")

        file_count = data.get("file_count", 0)
        if file_count > 0:
            lines.append(f"\n*{file_count} files analyzed*")

        return "\n".join(lines)

    def _generate_structure_section(self, analyses: List[Dict]) -> str:
        """Generate Repository Structure section."""
        lines = [
            "## Repository Structure",
            "",
        ]

        all_file_naming = []
        all_test_patterns = []
        all_module_patterns = []
        max_depths = []

        for analysis in analyses:
            structure = analysis.get("structure", {})

            file_naming = structure.get("file_naming", {})
            if file_naming.get("dominant"):
                all_file_naming.append(file_naming["dominant"])

            test_patterns = structure.get("test_patterns", {})
            if test_patterns:
                all_test_patterns.append(test_patterns)

            module_patterns = structure.get("module_patterns", {})
            if module_patterns:
                all_module_patterns.append(module_patterns)

            depth_stats = structure.get("depth_stats", {})
            if depth_stats.get("max"):
                max_depths.append(depth_stats["max"])

        if all_file_naming:
            from collections import Counter
            dominant = Counter(all_file_naming).most_common(1)[0][0]
            lines.append(f"### File Naming")
            lines.append(f"- **Dominant style:** {dominant}")
            lines.append("")

        if max_depths:
            avg_depth = sum(max_depths) / len(max_depths)
            lines.append(f"### Directory Depth")
            lines.append(f"- **Max:** {max(max_depths)} levels")
            lines.append(f"- **Average:** {avg_depth:.1f} levels")
            lines.append("")

        if all_test_patterns:
            lines.append(f"### Test Organization")
            test_locations = set()
            for tp in all_test_patterns:
                if tp.get("test_location"):
                    test_locations.add(tp["test_location"])
            if test_locations:
                lines.append(f"- **Location:** {', '.join(sorted(test_locations))}")
            frameworks = set()
            for tp in all_test_patterns:
                for fw in tp.get("test_framework", []):
                    frameworks.add(fw)
            if frameworks:
                lines.append(f"- **Frameworks:** {', '.join(sorted(frameworks))}")
            lines.append("")

        if all_module_patterns:
            lines.append(f"### Module Patterns")
            barrel_count = sum(1 for mp in all_module_patterns if mp.get("has_barrel_files"))
            init_count = sum(1 for mp in all_module_patterns if mp.get("has_init_files"))
            index_count = sum(1 for mp in all_module_patterns if mp.get("has_index_files"))
            if barrel_count > 0:
                lines.append("- **Barrel files:** mod.rs, lib.rs detected")
            if init_count > 0:
                lines.append("- **Init files:** __init__.py detected")
            if index_count > 0:
                lines.append("- **Index files:** index.js, index.ts detected")

        return "\n".join(lines)

    def _generate_commands_section(self, analyses: List[Dict]) -> str:
        """Generate Commands and Workflows section."""
        lines = [
            "## Commands and Workflows",
            "",
        ]

        all_commands = {}
        for analysis in analyses:
            commands = analysis.get("commands", {})
            for category, cmds in commands.items():
                if category not in all_commands:
                    all_commands[category] = []
                for cmd in cmds:
                    if cmd not in all_commands[category]:
                        all_commands[category].append(cmd)

        if not all_commands:
            lines.append("No explicit commands detected. Check README.md for manual instructions.")
            return "\n".join(lines)

        category_order = ["install", "dev", "build", "test", "lint", "format", "deploy", "ci"]

        for category in category_order:
            if category not in all_commands or not all_commands[category]:
                continue

            lines.append(f"### {category.title()}")
            for cmd in all_commands[category][:5]:
                cmd_str = cmd.get("command", "")
                source = cmd.get("source", "")
                if len(cmd_str) < 80:
                    lines.append(f"```bash")
                    lines.append(f"{cmd_str}")
                    lines.append(f"```")
            lines.append("")

        return "\n".join(lines)

    def _generate_dependencies_section(self, analyses: List[Dict]) -> str:
        """Generate Dependencies section."""
        lines = [
            "## Dependencies",
            "",
        ]

        all_managers = set()
        total_deps = []
        pin_styles = []

        for analysis in analyses:
            deps = analysis.get("dependencies", {})
            if deps.get("manager") and deps["manager"] != "unknown":
                all_managers.add(deps["manager"])
            if deps.get("total_deps"):
                total_deps.append(deps["total_deps"])
            if deps.get("pin_style") and deps["pin_style"] != "unknown":
                pin_styles.append(deps["pin_style"])

        if not all_managers:
            lines.append("No dependency information detected.")
            return "\n".join(lines)

        lines.append(f"### Package Managers")
        for manager in sorted(all_managers):
            lines.append(f"- {manager}")

        if total_deps:
            avg_deps = sum(total_deps) / len(total_deps)
            lines.append(f"")
            lines.append(f"### Philosophy")
            lines.append(f"- **Average dependency count:** {avg_deps:.0f} per project")

        if pin_styles:
            from collections import Counter
            dominant_pin = Counter(pin_styles).most_common(1)[0][0]
            lines.append(f"- **Pin style:** {dominant_pin}")

        return "\n".join(lines)

    def _generate_git_section(self, analyses: List[Dict]) -> str:
        """Generate Git section."""
        lines = [
            "## Git",
            "",
        ]

        commit_data = []
        prefixes = {}
        avg_lengths = []

        for analysis in analyses:
            git = analysis.get("git", {})
            commits = git.get("commits", {})
            if commits:
                avg_lengths.append(commits.get("avg_length", 0))
                for prefix, count in commits.get("common_prefixes", {}).items():
                    prefixes[prefix] = prefixes.get(prefix, 0) + count

        if prefixes:
            lines.append("### Commits")
            top_prefixes = sorted(prefixes.items(), key=lambda x: -x[1])[:5]
            prefix_str = ", ".join([f"`{p}`" for p, _ in top_prefixes])
            lines.append(f"- **Prefixes:** {prefix_str}")

            if avg_lengths:
                avg = sum(avg_lengths) / len(avg_lengths)
                lines.append(f"- **Avg length:** {avg:.0f} chars")

        branch_prefixes = {}
        for analysis in analyses:
            git = analysis.get("git", {})
            branches = git.get("branches", {})
            for prefix, count in branches.get("common_prefixes", {}).items():
                branch_prefixes[prefix] = branch_prefixes.get(prefix, 0) + count

        if branch_prefixes:
            lines.append("")
            lines.append("### Branches")
            top = sorted(branch_prefixes.items(), key=lambda x: -x[1])[:5]
            prefix_str = ", ".join([f"`{p}/`" for p, _ in top])
            lines.append(f"- **Prefixes:** {prefix_str}")

        return "\n".join(lines)

    def _generate_tooling_section(self, analyses: List[Dict]) -> str:
        """Generate Tooling section."""
        all_tools = set()
        for analysis in analyses:
            tools = analysis.get("tooling", {})
            all_tools.update(tools.keys())

        if not all_tools:
            return "## Tooling\n\nNo explicit tooling configs detected."

        lines = [
            "## Tooling",
            "",
            "Detected configurations:",
        ]

        for tool in sorted(all_tools):
            lines.append(f"- {tool}")

        return "\n".join(lines)

    def _generate_red_lines(self, analyses: List[Dict]) -> str:
        """Generate Red Lines section."""
        lines = [
            "## Red Lines",
            "",
            "Explicit avoidances based on actual patterns:",
            "",
        ]

        red_lines = self._extract_red_lines(analyses)
        if red_lines:
            for line in red_lines:
                lines.append(f"- {line}")
        else:
            lines.append("- No strong red lines detected from sample")

        return "\n".join(lines)

    def _generate_footer(self, analyses: List[Dict], repos: List[str]) -> str:
        """Generate footer with source and confidence."""
        from pathlib import Path
        repo_names = [Path(r).resolve().name for r in repos]
        source_str = ", ".join(repo_names) if repo_names else "unknown"

        total_files = sum(
            sum(lang.get("metrics", {}).get("file_count", 0) for lang in a.get("languages", {}).values())
            for a in analyses
        )

        lines = [
            "---",
            "",
            f"**Source:** {source_str}",
            f"**Files analyzed:** {total_files}",
            "**Confidence:** High on naming patterns; Medium on tooling (config-dependent)",
        ]

        return "\n".join(lines)

    def _detected_languages(self, analyses: List[Dict]) -> set:
        """Extract all detected languages."""
        langs = set()
        for analysis in analyses:
            langs.update(analysis.get("languages", {}).keys())
        return langs

    def _extract_key_principles(self, analyses: List[Dict]) -> List[str]:
        """Extract key principles from analyses."""
        principles = []

        low_comment_density = all(
            lang.get("comments", {}).get("density", 1) < 0.1
            for analysis in analyses
            for lang in analysis.get("languages", {}).values()
        )
        if low_comment_density:
            principles.append("Self-documenting code over verbose comments")

        principles.append("Descriptive names over terse abbreviations")

        has_unwrap = any(
            lang.get("error_handling", {}).get("unwrap", 0) > 0
            for analysis in analyses
            for lang in analysis.get("languages", {}).values()
        )
        if has_unwrap:
            principles.append("Fail-fast acceptable in CLI contexts")

        return principles

    def _find_common_patterns(self, analyses: List[Dict]) -> Dict:
        """Find patterns common across languages."""
        patterns = {}

        naming_consistency = {}
        for analysis in analyses:
            for lang, data in analysis.get("languages", {}).items():
                naming = data.get("naming", {})
                for cat, info in naming.items():
                    if isinstance(info, dict):
                        style = info.get("dominant_case")
                        if style:
                            naming_consistency[cat] = naming_consistency.get(cat, {})
                            naming_consistency[cat][style] = naming_consistency[cat].get(style, 0) + 1

        if naming_consistency:
            patterns["naming"] = {}
            for cat, styles in naming_consistency.items():
                if len(styles) == 1:
                    patterns["naming"][cat] = list(styles.keys())[0]

        doc_styles = set()
        for analysis in analyses:
            for lang, data in analysis.get("languages", {}).items():
                style = data.get("comments", {}).get("doc_style")
                if style:
                    doc_styles.add(style)

        if doc_styles:
            patterns["comments"] = f"Documentation via {', '.join(sorted(doc_styles))}"

        return patterns

    def _extract_red_lines(self, analyses: List[Dict]) -> List[str]:
        """Extract explicit avoidances from actual codebase patterns."""
        red_lines = []

        has_unwrap = False
        has_expect = False
        for analysis in analyses:
            for lang in analysis.get("languages", {}).values():
                eh = lang.get("error_handling", {})
                if eh.get("unwrap", 0) > 0:
                    has_unwrap = True
                if eh.get("expect", 0) > 0:
                    has_expect = True

        if has_unwrap and not has_expect:
            red_lines.append("Prefer unwrap() over expect() — fail fast without messages")
        elif has_expect and not has_unwrap:
            red_lines.append("Prefer expect() over unwrap() — always provide context on failure")

        naming_violations = []
        for analysis in analyses:
            for lang, data in analysis.get("languages", {}).items():
                naming = data.get("naming", {})
                for cat, info in naming.items():
                    if isinstance(info, dict):
                        counts = info.get("counts", {})
                        total = sum(counts.values())
                        if total > 0:
                            max_count = max(counts.values())
                            dominance = max_count / total
                            if dominance >= 0.95:
                                style = info.get("dominant_case", "unknown")
                                naming_violations.append(f"Strict {style} for {cat}")

        if naming_violations:
            seen = set()
            for violation in naming_violations:
                if violation not in seen:
                    seen.add(violation)
            if seen:
                red_lines.append("No mixing naming conventions within categories")

        for analysis in analyses:
            for lang, data in analysis.get("languages", {}).items():
                comments = data.get("comments", {})
                total = comments.get("total", 0)
                doc = comments.get("doc", 0)
                normal = comments.get("normal", 0)
                if total > 10 and doc > normal * 2:
                    red_lines.append("Doc comments over inline comments for API documentation")
                    break
            if "Doc comments over inline comments for API documentation" in red_lines:
                break

        return red_lines

    def write_to_file(self, content: str, output_path: str):
        """Write synthesized content to file."""
        Path(output_path).write_text(content)