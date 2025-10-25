#!/usr/bin/env python3
"""
Perform detailed inspection of specific problematic files.
"""

import os
from pathlib import Path

def inspect_file_diff(scraped_path: Path, cleaned_path: Path):
    """Detailed inspection of what was removed."""
    with open(scraped_path, 'r', encoding='utf-8') as f:
        scraped_lines = f.readlines()

    with open(cleaned_path, 'r', encoding='utf-8') as f:
        cleaned_lines = f.readlines()

    # Find differences
    scraped_set = set(scraped_lines)
    cleaned_set = set(cleaned_lines)

    removed = scraped_set - cleaned_set
    added = cleaned_set - scraped_set

    return {
        'scraped_lines': len(scraped_lines),
        'cleaned_lines': len(cleaned_lines),
        'unique_removed': len(removed),
        'unique_added': len(added),
        'removed_content': sorted(removed)[:20]  # Sample of removed content
    }

def main():
    base_dir = Path('/Users/tgartner/git/site2chunks')
    scrapes_dir = base_dir / 'scrapes'
    cleaned_dir = base_dir / 'cleaned'

    # Focus on high-impact categories
    priority_files = [
        # Review pages (very high reduction)
        'hackingwithswift.com_review_sixty_protocols.md',
        'hackingwithswift.com_review_sixty_dictionary-default-values.md',

        # Tutorial pages
        'hackingwithswift.com_100_swiftui_78.md',
        'hackingwithswift.com_100_26.md',

        # Quick start tutorials
        'hackingwithswift.com_quick-start_swiftui_how-to-create-stacks-using-vstack-and-hstack.md',

        # Books
        'hackingwithswift.com_books_ios-swiftui_absolute-positioning-for-swiftui-views.md',

        # Articles
        'hackingwithswift.com_articles_279_level-up-your-swiftui.md',

        # Interview questions
        'hackingwithswift.com_interview-questions_apart-from-the-built-in-ones-can-you-give-an-example-of-property-wrappers.md',
    ]

    print("DETAILED FILE INSPECTION")
    print("=" * 100)

    for filename in priority_files:
        scraped_path = scrapes_dir / filename
        cleaned_path = cleaned_dir / filename

        if not scraped_path.exists() or not cleaned_path.exists():
            print(f"\nSkipping {filename} (file not found)")
            continue

        print(f"\n\n{'=' * 100}")
        print(f"FILE: {filename}")
        print('=' * 100)

        result = inspect_file_diff(scraped_path, cleaned_path)

        print(f"\nLines: {result['scraped_lines']} → {result['cleaned_lines']}")
        print(f"Reduction: {(result['scraped_lines'] - result['cleaned_lines']) / result['scraped_lines'] * 100:.1f}%")
        print(f"Unique lines removed: {result['unique_removed']}")
        print(f"Unique lines added: {result['unique_added']}")

        print("\nSample of removed content (first 20 unique lines):")
        for i, line in enumerate(result['removed_content'][:20], 1):
            # Clean up for display
            line = line.strip()
            if line and not line.startswith('---'):
                print(f"  {i}. {line[:100]}")

if __name__ == '__main__':
    main()
