"""Main content cleaning engine."""

import re
from pathlib import Path
from typing import Dict, List, Optional
from .config import CleaningConfig


class ContentCleaner:
    """Apply cleaning rules to markdown files."""

    def __init__(self, config: CleaningConfig):
        self.config = config
        self.stats = {
            'files_processed': 0,
            'files_cleaned': 0,
            'bytes_removed': 0,
            'errors': []
        }

    def clean_content(self, content: str) -> str:
        """Apply all cleaning rules to content string."""
        original_length = len(content)
        cleaned = content

        # Apply each rule in sequence
        for rule in self.config.get_rules():
            try:
                cleaned = rule.apply(cleaned)
            except Exception as e:
                error_msg = f"Error applying {rule}: {str(e)}"
                self.stats['errors'].append(error_msg)
                print(f"Warning: {error_msg}")

        # Clean up excessive whitespace
        cleaned = self._normalize_whitespace(cleaned)

        # Update statistics
        bytes_removed = original_length - len(cleaned)
        self.stats['bytes_removed'] += bytes_removed

        return cleaned

    def clean_file(self, file_path: str, output_path: Optional[str] = None, dry_run: bool = False) -> Dict:
        """Clean a single markdown file."""
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read original content
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Clean content
        cleaned_content = self.clean_content(original_content)

        # Calculate statistics
        original_size = len(original_content)
        cleaned_size = len(cleaned_content)
        reduction_pct = ((original_size - cleaned_size) / original_size * 100) if original_size > 0 else 0

        result = {
            'file': str(file_path),
            'original_size': original_size,
            'cleaned_size': cleaned_size,
            'bytes_removed': original_size - cleaned_size,
            'reduction_percent': reduction_pct,
            'content_changed': original_content != cleaned_content
        }

        # Validate cleaned content
        validation_warnings = self._validate_cleaned_content(cleaned_content, original_content)
        if validation_warnings:
            result['warnings'] = validation_warnings

        # Write output if not dry run
        if not dry_run:
            output_file = Path(output_path) if output_path else file_path_obj

            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            self.stats['files_cleaned'] += 1

        self.stats['files_processed'] += 1

        return result

    def clean_directory(self, input_dir: str, output_dir: Optional[str] = None,
                       pattern: str = "*.md", dry_run: bool = False) -> List[Dict]:
        """Clean all markdown files in a directory."""
        input_path = Path(input_dir)

        if not input_path.exists():
            raise FileNotFoundError(f"Directory not found: {input_dir}")

        # Find all matching files
        files = list(input_path.glob(pattern))

        if not files:
            print(f"No files matching '{pattern}' found in {input_dir}")
            return []

        print(f"Found {len(files)} files to process")

        results = []

        for file_path in files:
            try:
                # Calculate output path
                if output_dir:
                    output_path = Path(output_dir) / file_path.name
                else:
                    output_path = None

                result = self.clean_file(str(file_path), str(output_path) if output_path else None, dry_run)
                results.append(result)

                # Show progress
                if result['content_changed']:
                    reduction = result['reduction_percent']
                    print(f"  ✓ {file_path.name}: {reduction:.1f}% reduction")
                else:
                    print(f"  - {file_path.name}: No changes needed")

            except Exception as e:
                error_msg = f"Error processing {file_path.name}: {str(e)}"
                self.stats['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")

        return results

    def get_statistics(self) -> Dict:
        """Return cleaning statistics."""
        return self.stats.copy()

    def preview_changes(self, file_path: str, context_lines: int = 3) -> str:
        """Generate a diff-like preview of changes."""
        file_path_obj = Path(file_path)

        with open(file_path_obj, 'r', encoding='utf-8') as f:
            original = f.read()

        cleaned = self.clean_content(original)

        if original == cleaned:
            return "No changes would be made."

        # Simple diff generation
        original_lines = original.split('\n')
        cleaned_lines = cleaned.split('\n')

        preview = []
        preview.append(f"File: {file_path}")
        preview.append(f"Original lines: {len(original_lines)}")
        preview.append(f"Cleaned lines: {len(cleaned_lines)}")
        preview.append(f"Lines removed: {len(original_lines) - len(cleaned_lines)}")
        preview.append("")

        # Show sample of removed content (first few differences)
        preview.append("Sample of changes:")
        preview.append("-" * 60)

        # Find first significant difference
        i = 0
        shown_diffs = 0
        max_diffs = 5

        while i < min(len(original_lines), len(cleaned_lines)) and shown_diffs < max_diffs:
            if i < len(original_lines) and i < len(cleaned_lines):
                if original_lines[i] != cleaned_lines[i]:
                    # Show context
                    start = max(0, i - context_lines)
                    end = min(len(original_lines), i + context_lines + 1)

                    for j in range(start, end):
                        if j < len(original_lines):
                            if j == i:
                                preview.append(f"- {original_lines[j][:100]}")
                            else:
                                preview.append(f"  {original_lines[j][:100]}")

                    shown_diffs += 1
                    preview.append("")

            i += 1

        return '\n'.join(preview)

    def _normalize_whitespace(self, content: str) -> str:
        """Clean up excessive blank lines and trailing whitespace."""
        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in content.split('\n')]

        # Reduce multiple blank lines to maximum 2
        normalized = []
        blank_count = 0

        for line in lines:
            if line == '':
                blank_count += 1
                if blank_count <= 2:
                    normalized.append(line)
            else:
                blank_count = 0
                normalized.append(line)

        # Join and ensure file ends with single newline
        result = '\n'.join(normalized)
        return result.rstrip() + '\n' if result else ''

    def _validate_cleaned_content(self, cleaned: str, original: str) -> List[str]:
        """Validate cleaned content for potential issues."""
        warnings = []

        # Check if too much content was removed
        reduction_pct = ((len(original) - len(cleaned)) / len(original) * 100) if len(original) > 0 else 0

        if reduction_pct > 75:
            warnings.append(f"Warning: {reduction_pct:.1f}% of content removed (>75%)")

        # Check if main content markers still exist
        if '# ' in original and '# ' not in cleaned:
            warnings.append("Warning: All H1 headers were removed")

        # Check if frontmatter was preserved
        if original.startswith('---\n') and not cleaned.startswith('---\n'):
            warnings.append("Warning: YAML frontmatter may have been removed")

        # Check minimum content length
        if len(cleaned.strip()) < 100:
            warnings.append(f"Warning: Cleaned content is very short ({len(cleaned)} chars)")

        return warnings
