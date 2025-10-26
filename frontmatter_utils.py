"""
Shared utilities for handling YAML frontmatter in markdown files.

This module provides consistent frontmatter extraction and parsing across
the entire pipeline (scraping, cleaning, chunking, merging).
"""

import yaml
import re
from typing import Tuple, Dict, Any


def extract_frontmatter_text(content: str) -> Tuple[str, str]:
    """
    Extract YAML frontmatter as raw text with delimiters.

    Args:
        content: Full markdown file content

    Returns:
        Tuple of (frontmatter_with_delimiters, body_content)
        If no frontmatter found, returns ('', content)

    Example:
        >>> content = "---\\nkey: value\\n---\\n\\nBody text"
        >>> fm, body = extract_frontmatter_text(content)
        >>> fm
        '---\\nkey: value\\n---\\n'
        >>> body
        '\\nBody text'
    """
    if not content.startswith('---\n'):
        return '', content

    # Find the closing ---
    end_marker = content.find('\n---\n', 4)
    if end_marker == -1:
        # No closing marker found, treat as no frontmatter
        return '', content

    # frontmatter includes the delimiters: '---\n...content...\n---\n'
    frontmatter = content[:end_marker + 5]
    body = content[end_marker + 5:]

    return frontmatter, body


def parse_frontmatter(content: str, strict: bool = True) -> Tuple[Dict[str, Any], str]:
    """
    Extract and parse YAML frontmatter into a dictionary.

    Args:
        content: Full markdown file content
        strict: If True, raises on YAML parse errors. If False, uses regex fallback

    Returns:
        Tuple of (frontmatter_dict, body_content)
        If no frontmatter or parse error, returns ({}, content) or ({}, body)

    Example:
        >>> content = "---\\ntitle: Test\\nurl: https://example.com\\n---\\n\\nBody"
        >>> fm, body = parse_frontmatter(content)
        >>> fm
        {'title': 'Test', 'url': 'https://example.com'}
        >>> body
        '\\n\\nBody'
    """
    fm_text, body = extract_frontmatter_text(content)

    if not fm_text:
        return {}, content

    # Extract just the YAML part (without --- delimiters)
    # fm_text is '---\nYAML\n---\n', we want just 'YAML'
    yaml_lines = fm_text.split('\n')
    yaml_text = '\n'.join(yaml_lines[1:-2])  # Skip first '---' and last '---\n'

    try:
        fm_dict = yaml.safe_load(yaml_text) or {}
        return fm_dict, body
    except (yaml.YAMLError, yaml.scanner.ScannerError) as e:
        if strict:
            raise

        # Non-strict mode: try to extract common fields with regex
        # This handles malformed YAML from old scrapers (unquoted colons in titles)
        fm_dict = {}

        # Try to extract all key-value pairs using regex
        # This works for simple "key: value" patterns
        for line in yaml_text.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                # Split on first colon only
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                if key and value:
                    # Try to parse common data types
                    if value.lower() in ('true', 'false'):
                        fm_dict[key] = value.lower() == 'true'
                    elif value.isdigit():
                        fm_dict[key] = int(value)
                    else:
                        # Strip quotes if present
                        if (value.startswith("'") and value.endswith("'")) or \
                           (value.startswith('"') and value.endswith('"')):
                            value = value[1:-1]
                        fm_dict[key] = value

        return fm_dict, body


def build_frontmatter(data: Dict[str, Any]) -> str:
    """
    Build properly formatted YAML frontmatter from a dictionary.

    Args:
        data: Dictionary of frontmatter fields

    Returns:
        Formatted frontmatter string with delimiters: '---\\n...\\n---\\n\\n'

    Example:
        >>> data = {'title': 'Test: Example', 'count': 42}
        >>> fm = build_frontmatter(data)
        >>> print(fm)
        ---
        title: 'Test: Example'
        count: 42
        ---
        <BLANKLINE>
    """
    if not data:
        return ''

    yaml_text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_text}---\n\n"


def merge_frontmatter(original: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two frontmatter dictionaries, with updates taking precedence.

    Args:
        original: Original frontmatter dict
        updates: New fields to add or override

    Returns:
        Merged dictionary

    Example:
        >>> original = {'title': 'Old', 'url': 'http://example.com'}
        >>> updates = {'title': 'New', 'date': '2025-10-26'}
        >>> merge_frontmatter(original, updates)
        {'title': 'New', 'url': 'http://example.com', 'date': '2025-10-26'}
    """
    result = dict(original) if original else {}
    result.update(updates)
    return result
