#!/usr/bin/env python3
"""
Export curated questions to standard test formats for retrieval evaluation.

Supports multiple output formats:
- JSON: Standard format with full metadata
- JSONL: One question per line for streaming
- CSV: Simple spreadsheet format
- TREC: TREC-style qrels format (query_id, chunk_id, relevance)
"""

import json
import csv
import argparse
from pathlib import Path
from datetime import datetime


def export_json(questions, output_path, pretty=True):
    """Export to JSON format."""
    test_set = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'total_questions': len(questions),
            'format': 'retrieval_test_set_v1'
        },
        'test_cases': [
            {
                'question_id': f"q_{i:04d}",
                'question': q['question'],
                'expected_chunk_id': q['chunk_id'],
                'expected_chunk_path': q['chunk_path'],
                'source_url': q.get('source_url'),
                'section_path': q.get('section_path', []),
                'source_type': q.get('source_type'),
                'metadata': {
                    'confidence': q.get('confidence'),
                    'status': q.get('status')
                }
            }
            for i, q in enumerate(questions, 1)
        ]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(test_set, f, indent=2 if pretty else None, ensure_ascii=False)

    return len(questions)


def export_jsonl(questions, output_path):
    """Export to JSONL format (one JSON object per line)."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, q in enumerate(questions, 1):
            test_case = {
                'question_id': f"q_{i:04d}",
                'question': q['question'],
                'expected_chunk_id': q['chunk_id'],
                'expected_chunk_path': q['chunk_path'],
                'source_url': q.get('source_url'),
                'section_path': q.get('section_path', []),
            }
            f.write(json.dumps(test_case, ensure_ascii=False) + '\n')

    return len(questions)


def export_csv(questions, output_path):
    """Export to CSV format."""
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['question_id', 'question', 'chunk_id', 'chunk_path', 'source_url', 'source_type'])

        for i, q in enumerate(questions, 1):
            writer.writerow([
                f"q_{i:04d}",
                q['question'],
                q['chunk_id'],
                Path(q['chunk_path']).name,
                q.get('source_url', ''),
                q.get('source_type', '')
            ])

    return len(questions)


def export_trec_qrels(questions, output_path):
    """
    Export to TREC qrels format for retrieval evaluation.
    Format: query_id iteration chunk_id relevance
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, q in enumerate(questions, 1):
            query_id = f"q_{i:04d}"
            chunk_id = q['chunk_id']
            # All ground truth chunks have relevance 1 (binary relevance)
            f.write(f"{query_id} 0 {chunk_id} 1\n")

    return len(questions)


def export_markdown_report(questions, output_path):
    """Export a markdown report for human review."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Test Questions Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total questions: {len(questions)}\n\n")

        # Stats by source type
        by_type = {}
        for q in questions:
            source_type = q.get('source_type', 'unknown')
            by_type[source_type] = by_type.get(source_type, 0) + 1

        f.write("## By Source Type\n\n")
        for source_type, count in sorted(by_type.items()):
            f.write(f"- {source_type}: {count}\n")

        f.write("\n## Questions\n\n")
        for i, q in enumerate(questions, 1):
            f.write(f"### Q{i:04d}: {q['question']}\n\n")
            f.write(f"- **Chunk**: `{Path(q['chunk_path']).name}`\n")
            f.write(f"- **Source**: {q.get('source_url', 'N/A')}\n")
            f.write(f"- **Type**: {q.get('source_type', 'N/A')}\n")
            if q.get('section_path'):
                f.write(f"- **Section**: {' > '.join(q['section_path'])}\n")
            f.write("\n")

    return len(questions)


def main():
    parser = argparse.ArgumentParser(description='Export curated questions to test format')
    parser.add_argument('input_file', help='Input JSON file with curated questions')
    parser.add_argument('-o', '--output', help='Output file base name (without extension)')
    parser.add_argument('-f', '--format', choices=['json', 'jsonl', 'csv', 'trec', 'all'],
                       default='json', help='Output format (default: json)')
    parser.add_argument('--pretty', action='store_true',
                       help='Pretty-print JSON output')
    parser.add_argument('--approved-only', action='store_true', default=True,
                       help='Only export approved/edited questions (default: True)')
    parser.add_argument('--include-all', action='store_true',
                       help='Include all questions regardless of status')

    args = parser.parse_args()

    # Load questions
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_questions = data['questions']
    print(f"Loaded {len(all_questions)} total questions")

    # Filter to approved questions only (unless --include-all)
    if not args.include_all and args.approved_only:
        questions = [q for q in all_questions if q.get('status') in ['approved', 'edited']]
        print(f"Filtered to {len(questions)} approved questions")
    else:
        questions = all_questions

    if not questions:
        print("Warning: No questions to export!")
        return 1

    # Determine output base name
    if args.output:
        output_base = Path(args.output)
    else:
        output_base = input_path.parent / 'test_set'

    # Export in requested format(s)
    formats_to_export = ['json', 'jsonl', 'csv', 'trec'] if args.format == 'all' else [args.format]

    results = []
    for fmt in formats_to_export:
        output_path = output_base.with_suffix(f'.{fmt}')

        if fmt == 'json':
            count = export_json(questions, output_path, args.pretty)
        elif fmt == 'jsonl':
            count = export_jsonl(questions, output_path)
        elif fmt == 'csv':
            count = export_csv(questions, output_path)
        elif fmt == 'trec':
            count = export_trec_qrels(questions, output_path)

        results.append((fmt, output_path, count))
        print(f"✓ Exported {count} questions to {output_path}")

    # Always create markdown report
    report_path = output_base.with_suffix('.md')
    export_markdown_report(questions, report_path)
    print(f"✓ Created report: {report_path}")

    print("\n" + "="*70)
    print("EXPORT COMPLETE")
    print("="*70)
    print(f"\nExported {len(questions)} questions in {len(results)} format(s)")
    print("\nFiles created:")
    for fmt, path, count in results:
        print(f"  - {path} ({fmt.upper()})")
    print(f"  - {report_path} (Report)")

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Use these test questions to evaluate your retrieval system")
    print("2. For each question, retrieve top-k chunks from your system")
    print("3. Compare retrieved chunks against expected_chunk_id")
    print("4. Calculate metrics:")
    print("   - Recall@k: Is the correct chunk in top-k results?")
    print("   - MRR (Mean Reciprocal Rank): What rank is the correct chunk?")
    print("   - Precision@k: How many of top-k are relevant?")
    print("\nExample evaluation workflow:")
    print("  python3 evaluate_retrieval.py test_set.json results.jsonl")

    return 0


if __name__ == '__main__':
    exit(main())
