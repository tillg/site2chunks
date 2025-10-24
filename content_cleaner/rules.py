"""Cleaning rule implementations for content processing."""

from abc import ABC, abstractmethod
import re
from typing import Dict, Any, List


class CleaningRule(ABC):
    """Abstract base class for all cleaning rules."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.description = config.get('description', 'Unnamed rule')

    @abstractmethod
    def apply(self, content: str) -> str:
        """Apply the cleaning rule to content and return cleaned version."""
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(description='{self.description}')"


class ExactMatchRule(CleaningRule):
    """Remove exact text matches from content."""

    def apply(self, content: str) -> str:
        pattern = self.config.get('pattern', '')
        max_remove = self.config.get('max_remove', 1)  # -1 means all

        if max_remove == -1:
            # Remove all occurrences
            content = content.replace(pattern, '')
        else:
            # Remove up to max_remove occurrences
            for _ in range(max_remove):
                content = content.replace(pattern, '', 1)

        return content


class RegexRule(CleaningRule):
    """Remove content matching regex patterns."""

    def apply(self, content: str) -> str:
        pattern = self.config.get('pattern', '')
        flags_list = self.config.get('flags', [])
        max_remove = self.config.get('max_remove', 0)  # 0 means all

        # Convert flag strings to re flags
        flag_map = {
            'IGNORECASE': re.IGNORECASE,
            'MULTILINE': re.MULTILINE,
            'DOTALL': re.DOTALL,
            'VERBOSE': re.VERBOSE
        }

        flags = 0
        for flag_name in flags_list:
            flags |= flag_map.get(flag_name, 0)

        if max_remove == 0:
            # Remove all matches
            content = re.sub(pattern, '', content, flags=flags)
        else:
            # Remove up to max_remove matches
            content = re.sub(pattern, '', content, count=max_remove, flags=flags)

        return content


class SectionBoundaryRule(CleaningRule):
    """Remove content between start and end markers."""

    def apply(self, content: str) -> str:
        start_marker = self.config.get('start_marker', '')
        end_marker = self.config.get('end_marker', '')
        inclusive = self.config.get('inclusive', True)

        if not start_marker or not end_marker:
            return content

        lines = content.split('\n')
        cleaned_lines = []
        in_section = False
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for start marker
            if start_marker in line and not in_section:
                in_section = True
                if not inclusive:
                    cleaned_lines.append(line)
                i += 1
                continue

            # Check for end marker
            if end_marker in line and in_section:
                in_section = False
                if not inclusive:
                    cleaned_lines.append(line)
                i += 1
                continue

            # Add line if not in section
            if not in_section:
                cleaned_lines.append(line)

            i += 1

        return '\n'.join(cleaned_lines)


class LinePatternRule(CleaningRule):
    """Remove lines matching a pattern."""

    def apply(self, content: str) -> str:
        pattern = self.config.get('pattern', '')
        flags_list = self.config.get('flags', [])

        # Convert flag strings to re flags
        flag_map = {
            'IGNORECASE': re.IGNORECASE,
            'MULTILINE': re.MULTILINE
        }

        flags = 0
        for flag_name in flags_list:
            flags |= flag_map.get(flag_name, 0)

        lines = content.split('\n')
        cleaned_lines = [
            line for line in lines
            if not re.search(pattern, line, flags=flags)
        ]

        return '\n'.join(cleaned_lines)


class RepeatingPatternRule(CleaningRule):
    """Handle repeated elements (keep first/last/none)."""

    def apply(self, content: str) -> str:
        pattern = self.config.get('pattern', '')
        keep_first = self.config.get('keep_first', False)
        keep_last = self.config.get('keep_last', False)

        if not pattern:
            return content

        # Find all matches with their positions
        matches = list(re.finditer(re.escape(pattern), content))

        if len(matches) <= 1:
            return content

        # Determine which matches to remove
        if keep_first:
            # Remove all but first
            for match in reversed(matches[1:]):
                content = content[:match.start()] + content[match.end():]
        elif keep_last:
            # Remove all but last
            for match in reversed(matches[:-1]):
                content = content[:match.start()] + content[match.end():]
        else:
            # Remove all matches
            for match in reversed(matches):
                content = content[:match.start()] + content[match.end():]

        return content


class FrontmatterPreservingRule(CleaningRule):
    """Wrapper rule that preserves YAML frontmatter while applying another rule."""

    def __init__(self, config: Dict[str, Any], wrapped_rule: CleaningRule):
        super().__init__(config)
        self.wrapped_rule = wrapped_rule

    def apply(self, content: str) -> str:
        # Extract frontmatter if present
        frontmatter = ""
        body = content

        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                frontmatter = f"---\n{parts[1]}---\n"
                body = parts[2]

        # Apply wrapped rule to body only
        cleaned_body = self.wrapped_rule.apply(body)

        # Recombine
        return frontmatter + cleaned_body
