#!/usr/bin/env python3
"""
Merge all QA markdown files into a single JSON file for Swift/RAG systems.
Each QA becomes a JSON object with metadata and question text.
"""

import json
import yaml
from pathlib import Path
import argparse
import sys


def parse_qa_file(file_path):
    """
    Parse a QA markdown file and extract frontmatter and question.

    Returns a dict with metadata and question text.
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
                question_text = content[end_marker + 5:].strip()

                # Parse YAML frontmatter
                frontmatter = yaml.safe_load(frontmatter_str) or {}

                # Convert date objects to strings if necessary
                generation_date = frontmatter.get('generation_date', '')
                if hasattr(generation_date, 'isoformat'):
                    generation_date = generation_date.isoformat()
                elif not isinstance(generation_date, str):
                    generation_date = str(generation_date)

                qa_data = {
                    'question': question_text,
                    'chunk_file': frontmatter.get('chunk_file', ''),
                    'chunk_id': frontmatter.get('chunk_id', ''),
                    'source_url': frontmatter.get('source_url', ''),
                    'generation_model': frontmatter.get('generation_model', ''),
                    'generation_date': generation_date,
                    'source_type': frontmatter.get('source_type', ''),
                    'confidence': frontmatter.get('confidence', '')
                }

                # Optional: include section_path if present
                if 'section_path' in frontmatter:
                    qa_data['section_path'] = frontmatter['section_path']

                return qa_data

        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {file_path}: {e}", file=sys.stderr)
            return None

    # No frontmatter found - treat entire content as question
    return {
        'question': content.strip(),
        'chunk_file': '',
        'chunk_id': '',
        'source_url': '',
        'generation_model': '',
        'generation_date': '',
        'source_type': 'unknown',
        'confidence': 'unknown'
    }


def merge_qa(input_dir, output_file, pretty=False):
    """
    Merge all QA markdown files from input_dir into a single JSON file.

    Args:
        input_dir: Directory containing QA markdown files
        output_file: Path to output JSON file
        pretty: If True, format JSON with indentation
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"Error: Directory '{input_dir}' not found", file=sys.stderr)
        return False

    # Find all markdown QA files
    qa_files = sorted(input_path.glob('*.md'))

    if not qa_files:
        print(f"No markdown files found in {input_dir}", file=sys.stderr)
        return False

    print(f"Found {len(qa_files)} QA files to merge")

    # Process each QA file
    all_qa = []
    errors = 0

    for qa_file in qa_files:
        qa_data = parse_qa_file(qa_file)

        if qa_data:
            # Add filename for reference
            qa_data['qa_file'] = qa_file.name
            all_qa.append(qa_data)

            # Show progress for large datasets
            if len(all_qa) % 50 == 0:
                print(f"  Processed {len(all_qa)} files...")
        else:
            errors += 1
            print(f"  ✗ Failed to process: {qa_file.name}")

    # Sort QA by chunk_file and then by qa_file name for consistency
    all_qa.sort(key=lambda x: (x.get('chunk_file', ''), x.get('qa_file', '')))

    # Write to JSON file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(all_qa, f, ensure_ascii=False, indent=2)
        else:
            json.dump(all_qa, f, ensure_ascii=False)

    print(f"\n✅ Merged {len(all_qa)} QA pairs into: {output_file}")
    if errors > 0:
        print(f"⚠️  {errors} files failed to process")

    # Print summary statistics
    unique_chunks = len(set(qa['chunk_file'] for qa in all_qa if qa.get('chunk_file')))
    unique_urls = len(set(qa['source_url'] for qa in all_qa if qa.get('source_url')))

    # Count by source type
    source_types = {}
    for qa in all_qa:
        source_type = qa.get('source_type', 'unknown')
        source_types[source_type] = source_types.get(source_type, 0) + 1

    print(f"\nSummary:")
    print(f"  Total QA pairs: {len(all_qa)}")
    print(f"  Unique chunks referenced: {unique_chunks}")
    print(f"  Unique source URLs: {unique_urls}")
    print(f"\n  By source type:")
    for source_type, count in sorted(source_types.items()):
        print(f"    {source_type}: {count}")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Merge QA markdown files into a single JSON file for Swift/RAG systems',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge with default settings
  python3 merge_qa.py

  # Merge with pretty formatting
  python3 merge_qa.py --pretty

  # Specify custom input/output
  python3 merge_qa.py qa/ -o my_qa.json

  # For Swift integration
  python3 merge_qa.py qa/ -o Resources/qa.json --pretty
        """
    )
    parser.add_argument(
        'input',
        default='qa',
        nargs='?',
        help='Input directory containing QA files (default: qa)'
    )
    parser.add_argument(
        '-o', '--output',
        default='qa.json',
        help='Output JSON file (default: qa.json)'
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Format JSON with indentation for readability'
    )

    args = parser.parse_args()

    success = merge_qa(args.input, args.output, args.pretty)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
