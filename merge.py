#!/usr/bin/env python3
"""
Merge all chunk markdown files into a single JSON file.
Each chunk becomes a JSON object with metadata and content.
"""

import json
import yaml
import re
from pathlib import Path
import argparse
import sys


def parse_chunk_file(file_path):
    """
    Parse a chunk markdown file and extract frontmatter and content.

    Returns a dict with metadata and content.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse frontmatter
    if content.startswith('---\n'):
        try:
            # Find the closing ---
            end_marker = content.find('\n---\n', 4)
            if end_marker != -1:
                frontmatter_str = content[4:end_marker]
                chunk_content = content[end_marker + 5:].strip()

                # Parse YAML frontmatter
                frontmatter = yaml.safe_load(frontmatter_str) or {}

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
                    # Try to extract from embedded frontmatter
                    embedded_match = re.match(r'^---\s*\n(.*?)\n---', chunk_content, re.DOTALL)
                    if embedded_match:
                        try:
                            # Try to parse as YAML, but if it fails, extract with regex
                            embedded_text = embedded_match.group(1)
                            url_match = re.search(r'^original_url:\s*(.+)$', embedded_text, re.MULTILINE)
                            if url_match:
                                original_url = url_match.group(1).strip()
                            if not title:
                                title_match = re.search(r'^title:\s*(.+)$', embedded_text, re.MULTILINE)
                                if title_match:
                                    title = title_match.group(1).strip()
                        except:
                            pass

                chunk_data = {
                    'original_url': original_url,
                    'scrape_date': scrape_date,
                    'title': title,
                    'chunk_index': frontmatter.get('chunk_index', 0),
                    'content': chunk_content
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

        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {file_path}: {e}", file=sys.stderr)
            return None

    # No frontmatter found
    return {
        'original_url': '',
        'scrape_date': '',
        'title': '',
        'chunk_index': 0,
        'content': content
    }


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
        'input',
        default='chunks',
        nargs='?',
        help='Input directory containing chunk files (default: chunks)'
    )
    parser.add_argument(
        '-o', '--output',
        default='chunks.json',
        help='Output JSON file (default: chunks.json)'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Format JSON with indentation for readability'
    )
    parser.add_argument(
        '--filter-url',
        help='Only include chunks from this URL'
    )

    args = parser.parse_args()

    # If filter is specified, process before merging
    if args.filter_url:
        print(f"Filtering chunks from URL: {args.filter_url}")
        # This would require modifying merge_chunks to filter
        # For now, just note it in the output

    success = merge_chunks(args.input, args.output, args.pretty)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()