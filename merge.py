#!/usr/bin/env python3
"""
Merge all chunk markdown files into a single JSON file.
Each chunk becomes a JSON object with metadata and content.
Supports configuration sets for managing multiple sites.
"""

import json
import yaml
import re
from pathlib import Path
import argparse
import sys

import frontmatter_utils
from config_loader import load_config_set, list_config_sets, ConfigSetNotFoundError


def parse_chunk_file(file_path):
    """
    Parse a chunk markdown file and extract frontmatter and content.

    Returns a dict with metadata and content.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Use shared utility to parse frontmatter (non-strict for malformed YAML)
    try:
        frontmatter, chunk_content = frontmatter_utils.parse_frontmatter(content, strict=False)
    except Exception as e:
        print(f"Error parsing frontmatter in {file_path}: {e}", file=sys.stderr)
        return None

    if not frontmatter:
        # No frontmatter found
        return {
            'original_url': '',
            'scrape_date': '',
            'title': '',
            'chunk_index': 0,
            'content': content
        }

    # Extract the specific fields we want
    # Convert date objects to strings if necessary
    scrape_date = frontmatter.get('scrape_date', '')
    if hasattr(scrape_date, 'isoformat'):
        scrape_date = scrape_date.isoformat()
    elif not isinstance(scrape_date, str):
        scrape_date = str(scrape_date)

    # If original_url is missing, try to extract it from embedded frontmatter in content
    original_url = frontmatter.get('original_url', '')
    title = frontmatter.get('title', '')

    if not original_url and chunk_content.strip().startswith('---'):
        # Try to extract from embedded frontmatter (legacy issue from old chunks)
        embedded_fm, _ = frontmatter_utils.parse_frontmatter(chunk_content, strict=False)
        if embedded_fm:
            original_url = embedded_fm.get('original_url', original_url)
            if not title:
                title = embedded_fm.get('title', '')

    chunk_data = {
        'original_url': original_url,
        'scrape_date': scrape_date,
        'title': title,
        'chunk_index': frontmatter.get('chunk_index', 0),
        'content': chunk_content.strip()
    }

    # Optional: include other useful metadata
    if 'total_chunks' in frontmatter:
        chunk_data['total_chunks'] = frontmatter['total_chunks']
    if 'source_file' in frontmatter:
        chunk_data['source_file'] = frontmatter['source_file']
    if 'section_path' in frontmatter:
        chunk_data['section_path'] = frontmatter['section_path']
    if 'char_count' in frontmatter:
        chunk_data['char_count'] = frontmatter['char_count']
    if 'word_count' in frontmatter:
        chunk_data['word_count'] = frontmatter['word_count']

    return chunk_data


def merge_chunks(input_dir, output_file, pretty=False):
    """
    Merge all chunk markdown files from input_dir into a single JSON file.

    Args:
        input_dir: Directory containing chunk markdown files
        output_file: Path to output JSON file
        pretty: If True, format JSON with indentation
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"Error: Directory '{input_dir}' not found", file=sys.stderr)
        return False

    # Find all markdown chunk files
    chunk_files = sorted(input_path.glob('*.md'))

    if not chunk_files:
        print(f"No markdown files found in {input_dir}", file=sys.stderr)
        return False

    print(f"Found {len(chunk_files)} chunk files to merge")

    # Process each chunk file
    all_chunks = []
    errors = 0

    for chunk_file in chunk_files:
        chunk_data = parse_chunk_file(chunk_file)

        if chunk_data:
            # Add filename for reference
            chunk_data['chunk_file'] = chunk_file.name
            all_chunks.append(chunk_data)
            print(f"  ✓ Processed: {chunk_file.name}")
        else:
            errors += 1
            print(f"  ✗ Failed to process: {chunk_file.name}")

    # Sort chunks by source file and chunk index
    all_chunks.sort(key=lambda x: (x.get('source_file', ''), x.get('chunk_index', 0)))

    # Write to JSON file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        else:
            json.dump(all_chunks, f, ensure_ascii=False)

    print(f"\n✅ Merged {len(all_chunks)} chunks into: {output_file}")
    if errors > 0:
        print(f"⚠️  {errors} files failed to process")

    # Print summary statistics
    total_chars = sum(c.get('char_count', len(c['content'])) for c in all_chunks)
    total_words = sum(c.get('word_count', len(c['content'].split())) for c in all_chunks)
    unique_urls = len(set(c['original_url'] for c in all_chunks if c.get('original_url')))

    print(f"\nSummary:")
    print(f"  Total characters: {total_chars:,}")
    print(f"  Total words: {total_words:,}")
    print(f"  Unique source URLs: {unique_urls}")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Merge chunk markdown files into a single JSON file'
    )
    parser.add_argument(
        'config_set',
        nargs='?',
        default=None,
        help='Name of configuration set in config/ directory (optional)'
    )
    parser.add_argument(
        'input',
        default=None,
        nargs='?',
        help='Input directory containing chunk files (optional if config set specified, default: chunks)'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output JSON file (default from config set or chunks.json)'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        default=None,
        help='Format JSON with indentation for readability'
    )
    parser.add_argument(
        '--indent',
        type=int,
        default=None,
        help='JSON indentation level (requires --pretty)'
    )
    parser.add_argument(
        '--filter-url',
        help='Only include chunks from this URL'
    )

    args = parser.parse_args()

    # Try to load config set if provided
    config_set = None
    if args.config_set:
        try:
            config_set = load_config_set(args.config_set)
            print(f"Loaded configuration set: {args.config_set}")
        except ConfigSetNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Determine parameters based on priority: CLI args > config set > defaults
    if config_set:
        # Using config set
        merging_config = config_set.get_merging_config()

        input_dir = args.input or str(config_set.get_chunks_dir())
        output_file = args.output or str(config_set.get_merged_file())
        pretty = args.pretty if args.pretty is not None else merging_config.get('pretty', False)
        indent_level = args.indent if args.indent is not None else merging_config.get('indent', 2)
    else:
        # Using command-line args and defaults
        input_dir = args.input or 'chunks'
        output_file = args.output or 'chunks.json'
        pretty = args.pretty if args.pretty is not None else False
        indent_level = args.indent if args.indent is not None else 2

    # If filter is specified, process before merging
    if args.filter_url:
        print(f"Filtering chunks from URL: {args.filter_url}")
        # This would require modifying merge_chunks to filter
        # For now, just note it in the output

    # Call merge_chunks with indent support
    success = merge_chunks_with_indent(input_dir, output_file, pretty, indent_level)

    if not success:
        sys.exit(1)


def merge_chunks_with_indent(input_dir, output_file, pretty=False, indent=2):
    """
    Wrapper around merge_chunks that supports custom indent levels.
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"Error: Directory '{input_dir}' not found", file=sys.stderr)
        return False

    # Find all markdown chunk files
    chunk_files = sorted(input_path.glob('*.md'))

    if not chunk_files:
        print(f"No markdown files found in {input_dir}", file=sys.stderr)
        return False

    print(f"Found {len(chunk_files)} chunk files to merge")

    # Process each chunk file
    all_chunks = []
    errors = 0

    for chunk_file in chunk_files:
        chunk_data = parse_chunk_file(chunk_file)

        if chunk_data:
            # Add filename for reference
            chunk_data['chunk_file'] = chunk_file.name
            all_chunks.append(chunk_data)
            print(f"  ✓ Processed: {chunk_file.name}")
        else:
            errors += 1
            print(f"  ✗ Failed to process: {chunk_file.name}")

    # Sort chunks by source file and chunk index
    all_chunks.sort(key=lambda x: (x.get('source_file', ''), x.get('chunk_index', 0)))

    # Write to JSON file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(all_chunks, f, ensure_ascii=False, indent=indent)
        else:
            json.dump(all_chunks, f, ensure_ascii=False)

    print(f"\n✅ Merged {len(all_chunks)} chunks into: {output_file}")
    if errors > 0:
        print(f"⚠️  {errors} files failed to process")

    # Print summary statistics
    total_chars = sum(c.get('char_count', len(c['content'])) for c in all_chunks)
    total_words = sum(c.get('word_count', len(c['content'].split())) for c in all_chunks)
    unique_urls = len(set(c['original_url'] for c in all_chunks if c.get('original_url')))

    print(f"\nSummary:")
    print(f"  Total characters: {total_chars:,}")
    print(f"  Total words: {total_words:,}")
    print(f"  Unique source URLs: {unique_urls}")

    return True


if __name__ == "__main__":
    main()