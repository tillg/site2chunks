#!/usr/bin/env python3
"""
Interactive CLI tool to review and curate test questions.
Allows you to approve, reject, or edit questions before final export.
"""

import json
import argparse
from pathlib import Path


def display_question(q, index, total):
    """Display a single question with its metadata."""
    print(f"\n{'='*70}")
    print(f"Question {index}/{total} [{q.get('source_type', 'unknown')}]")
    print(f"{'='*70}")
    print(f"\nQ: {q['question']}")
    print(f"\nSource: {q.get('source_url', 'N/A')}")
    print(f"Chunk: {Path(q['chunk_path']).name}")
    if q.get('section_path'):
        print(f"Section: {' > '.join(q['section_path'])}")
    print(f"Confidence: {q.get('confidence', 'N/A')}")
    print(f"Status: {'✓ Reviewed' if q.get('reviewed') else '○ Not reviewed'}")


def review_interactive(questions):
    """Interactively review questions."""
    print("\n" + "="*70)
    print("INTERACTIVE QUESTION REVIEW")
    print("="*70)
    print("\nCommands:")
    print("  [a]pprove  - Mark question as good")
    print("  [r]eject   - Mark question as rejected")
    print("  [e]dit     - Edit the question text")
    print("  [s]kip     - Skip for now")
    print("  [q]uit     - Save and exit")
    print("  [?]        - Show this help")

    unreviewed = [q for q in questions if not q.get('reviewed')]
    print(f"\n{len(unreviewed)} questions need review")

    for i, q in enumerate(unreviewed, 1):
        display_question(q, i, len(unreviewed))

        while True:
            choice = input("\n[a/r/e/s/q/?] > ").strip().lower()

            if choice == 'a':
                q['reviewed'] = True
                q['status'] = 'approved'
                print("✓ Approved")
                break
            elif choice == 'r':
                q['reviewed'] = True
                q['status'] = 'rejected'
                print("✗ Rejected")
                break
            elif choice == 'e':
                print(f"\nCurrent: {q['question']}")
                new_text = input("Enter new question text (or press Enter to cancel): ").strip()
                if new_text:
                    q['question'] = new_text
                    q['reviewed'] = True
                    q['status'] = 'edited'
                    print("✓ Question updated and approved")
                    break
                else:
                    print("Edit cancelled")
            elif choice == 's':
                print("○ Skipped")
                break
            elif choice == 'q':
                return True  # Signal to quit
            elif choice == '?':
                print("\nCommands:")
                print("  [a]pprove  - Mark question as good")
                print("  [r]eject   - Mark question as rejected")
                print("  [e]dit     - Edit the question text")
                print("  [s]kip     - Skip for now")
                print("  [q]uit     - Save and exit")
            else:
                print("Invalid command. Press '?' for help.")

    return False  # Completed all questions


def show_stats(questions):
    """Display statistics about the questions."""
    total = len(questions)
    reviewed = sum(1 for q in questions if q.get('reviewed'))
    approved = sum(1 for q in questions if q.get('status') == 'approved')
    edited = sum(1 for q in questions if q.get('status') == 'edited')
    rejected = sum(1 for q in questions if q.get('status') == 'rejected')
    pending = total - reviewed

    by_type = {}
    for q in questions:
        source_type = q.get('source_type', 'unknown')
        by_type[source_type] = by_type.get(source_type, 0) + 1

    print("\n" + "="*70)
    print("QUESTION STATISTICS")
    print("="*70)
    print(f"\nTotal questions: {total}")
    print(f"  Reviewed: {reviewed} ({reviewed/total*100:.1f}%)")
    print(f"  Pending:  {pending} ({pending/total*100:.1f}%)")
    print(f"\nReview status:")
    print(f"  ✓ Approved: {approved}")
    print(f"  ✎ Edited:   {edited}")
    print(f"  ✗ Rejected: {rejected}")
    print(f"\nBy source type:")
    for source_type, count in sorted(by_type.items()):
        print(f"  {source_type}: {count}")


def main():
    parser = argparse.ArgumentParser(description='Review and curate test questions')
    parser.add_argument('input_file', help='Input JSON file with questions')
    parser.add_argument('-o', '--output', help='Output file (default: input_file with _curated suffix)')
    parser.add_argument('--stats', action='store_true', help='Show stats only, no review')
    parser.add_argument('--auto-approve-extracted', action='store_true',
                       help='Automatically approve all extracted interview questions')

    args = parser.parse_args()

    # Load questions
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data['questions']
    metadata = data.get('metadata', {})

    print(f"Loaded {len(questions)} questions from {input_path}")

    # Auto-approve extracted questions if requested
    if args.auto_approve_extracted:
        count = 0
        for q in questions:
            if q.get('source_type') == 'interview_question' and not q.get('reviewed'):
                q['reviewed'] = True
                q['status'] = 'approved'
                count += 1
        print(f"✓ Auto-approved {count} extracted interview questions")

    # Show stats
    show_stats(questions)

    # Interactive review (skip if stats-only or auto-approve-extracted)
    if not args.stats and not args.auto_approve_extracted:
        print("\n" + "="*70)
        proceed = input("\nStart interactive review? [y/N] > ").strip().lower()
        if proceed == 'y':
            review_interactive(questions)

    # Save results (always save if changes were made)
    if args.auto_approve_extracted or not args.stats:
        output_path = Path(args.output) if args.output else input_path.parent / f"{input_path.stem}_curated.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': metadata,
                'questions': questions
            }, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Saved to {output_path}")

        # Final stats
        show_stats(questions)

        approved_count = sum(1 for q in questions if q.get('status') in ['approved', 'edited'])
        print(f"\nReady to export: {approved_count} approved questions")
        print(f"Next: python3 export_qa.py {output_path}")

    return 0


if __name__ == '__main__':
    exit(main())
