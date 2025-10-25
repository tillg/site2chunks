#!/usr/bin/env python3
"""
Analyze content cleaning quality by comparing scraped vs cleaned files.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import yaml

def read_file(filepath: Path) -> Tuple[str, Dict]:
    """Read file and extract frontmatter and content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract frontmatter if present
    frontmatter = {}
    if content.startswith('---\n'):
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
            except:
                pass
            content = parts[2]

    return content, frontmatter

def analyze_file_pair(scraped_path: Path, cleaned_path: Path) -> Dict:
    """Analyze differences between scraped and cleaned file."""
    scraped_content, scraped_fm = read_file(scraped_path)
    cleaned_content, cleaned_fm = read_file(cleaned_path)

    scraped_lines = scraped_content.strip().split('\n')
    cleaned_lines = cleaned_content.strip().split('\n')

    scraped_size = len(scraped_content)
    cleaned_size = len(cleaned_content)
    reduction_pct = ((scraped_size - cleaned_size) / scraped_size * 100) if scraped_size > 0 else 0

    # Count code blocks
    scraped_code_blocks = len(re.findall(r'```[\s\S]*?```', scraped_content))
    cleaned_code_blocks = len(re.findall(r'```[\s\S]*?```', cleaned_content))
    code_blocks_removed = scraped_code_blocks - cleaned_code_blocks

    # Count headers
    scraped_headers = len(re.findall(r'^#{1,6}\s+.+$', scraped_content, re.MULTILINE))
    cleaned_headers = len(re.findall(r'^#{1,6}\s+.+$', cleaned_content, re.MULTILINE))
    headers_removed = scraped_headers - cleaned_headers

    # Count links
    scraped_links = len(re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', scraped_content))
    cleaned_links = len(re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', cleaned_content))
    links_removed = scraped_links - cleaned_links

    # Check for educational keywords
    educational_keywords = ['tutorial', 'example', 'learn', 'guide', 'lesson', 'project',
                           'challenge', 'exercise', 'practice', 'test', 'review']
    has_educational_content = any(keyword in scraped_path.stem.lower() for keyword in educational_keywords)

    return {
        'file': scraped_path.name,
        'scraped_size': scraped_size,
        'cleaned_size': cleaned_size,
        'reduction_pct': reduction_pct,
        'scraped_lines': len(scraped_lines),
        'cleaned_lines': len(cleaned_lines),
        'scraped_code_blocks': scraped_code_blocks,
        'cleaned_code_blocks': cleaned_code_blocks,
        'code_blocks_removed': code_blocks_removed,
        'scraped_headers': scraped_headers,
        'cleaned_headers': cleaned_headers,
        'headers_removed': headers_removed,
        'scraped_links': scraped_links,
        'cleaned_links': cleaned_links,
        'links_removed': links_removed,
        'has_educational_content': has_educational_content,
        'url': scraped_fm.get('original_url', 'N/A')
    }

def categorize_file(filename: str) -> str:
    """Categorize file based on naming pattern."""
    if filename.startswith('hackingwithswift.com_100_'):
        return 'tutorial_100days'
    elif filename.startswith('hackingwithswift.com_quick-start_'):
        return 'quick_start'
    elif filename.startswith('hackingwithswift.com_books_'):
        return 'books'
    elif filename.startswith('hackingwithswift.com_example-code_'):
        return 'example_code'
    elif filename.startswith('hackingwithswift.com_articles_'):
        return 'articles'
    elif filename.startswith('hackingwithswift.com_forums_'):
        return 'forums'
    elif filename.startswith('hackingwithswift.com_review_'):
        return 'review'
    elif filename.startswith('hackingwithswift.com_swift'):
        return 'swift_version'
    elif filename.startswith('hackingwithswift.com_guide_'):
        return 'guide'
    elif filename.startswith('hackingwithswift.com_interview-questions_'):
        return 'interview_questions'
    elif filename.startswith('hackingwithswift.com_glossary_'):
        return 'glossary'
    else:
        return 'other'

def main():
    base_dir = Path('/Users/tgartner/git/site2chunks')
    scrapes_dir = base_dir / 'scrapes'
    cleaned_dir = base_dir / 'cleaned'

    # Get all scraped files
    scraped_files = sorted(scrapes_dir.glob('*.md'))

    # Categorize and sample files
    categories = {}
    for scraped_file in scraped_files:
        category = categorize_file(scraped_file.name)
        if category not in categories:
            categories[category] = []
        categories[category].append(scraped_file)

    print(f"Total scraped files: {len(scraped_files)}")
    print(f"\nFile categories:")
    for cat, files in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {cat}: {len(files)} files")

    # Sample files from each category
    samples_per_category = {}
    for category, files in categories.items():
        # Sample based on category size
        if len(files) > 50:
            sample_size = 10
        elif len(files) > 20:
            sample_size = 5
        elif len(files) > 5:
            sample_size = 3
        else:
            sample_size = min(len(files), 2)

        # Take evenly distributed samples
        step = max(1, len(files) // sample_size)
        samples = files[::step][:sample_size]
        samples_per_category[category] = samples

    print(f"\nAnalyzing samples...")

    # Analyze all samples
    results = []
    for category, samples in samples_per_category.items():
        for scraped_file in samples:
            cleaned_file = cleaned_dir / scraped_file.name
            if not cleaned_file.exists():
                print(f"  WARNING: No cleaned version for {scraped_file.name}")
                continue

            result = analyze_file_pair(scraped_file, cleaned_file)
            result['category'] = category
            results.append(result)

    # Sort by reduction percentage
    results.sort(key=lambda x: x['reduction_pct'], reverse=True)

    # Output detailed results
    print(f"\n{'='*100}")
    print(f"DETAILED ANALYSIS RESULTS ({len(results)} files)")
    print(f"{'='*100}\n")

    # High reduction files (>60%)
    high_reduction = [r for r in results if r['reduction_pct'] > 60]
    print(f"\n{'='*100}")
    print(f"HIGH REDUCTION FILES (>60% reduction) - {len(high_reduction)} files")
    print(f"{'='*100}")
    for result in high_reduction:
        print(f"\nFile: {result['file']}")
        print(f"  Category: {result['category']}")
        print(f"  URL: {result['url']}")
        print(f"  Size: {result['scraped_size']:,} → {result['cleaned_size']:,} bytes ({result['reduction_pct']:.1f}% reduction)")
        print(f"  Lines: {result['scraped_lines']} → {result['cleaned_lines']}")
        print(f"  Code blocks: {result['scraped_code_blocks']} → {result['cleaned_code_blocks']} (removed: {result['code_blocks_removed']})")
        print(f"  Headers: {result['scraped_headers']} → {result['cleaned_headers']} (removed: {result['headers_removed']})")
        print(f"  Links: {result['scraped_links']} → {result['cleaned_links']} (removed: {result['links_removed']})")
        print(f"  Educational: {result['has_educational_content']}")

    # Files with code blocks removed
    code_removed = [r for r in results if r['code_blocks_removed'] > 0]
    print(f"\n{'='*100}")
    print(f"FILES WITH CODE BLOCKS REMOVED - {len(code_removed)} files")
    print(f"{'='*100}")
    for result in code_removed:
        print(f"\nFile: {result['file']}")
        print(f"  Category: {result['category']}")
        print(f"  Code blocks removed: {result['code_blocks_removed']} ({result['scraped_code_blocks']} → {result['cleaned_code_blocks']})")
        print(f"  Overall reduction: {result['reduction_pct']:.1f}%")

    # Category summary
    print(f"\n{'='*100}")
    print(f"CATEGORY SUMMARY")
    print(f"{'='*100}")

    category_stats = {}
    for result in results:
        cat = result['category']
        if cat not in category_stats:
            category_stats[cat] = {
                'count': 0,
                'total_reduction': 0,
                'code_blocks_removed': 0,
                'headers_removed': 0
            }
        category_stats[cat]['count'] += 1
        category_stats[cat]['total_reduction'] += result['reduction_pct']
        category_stats[cat]['code_blocks_removed'] += result['code_blocks_removed']
        category_stats[cat]['headers_removed'] += result['headers_removed']

    for cat, stats in sorted(category_stats.items()):
        avg_reduction = stats['total_reduction'] / stats['count']
        print(f"\n{cat}:")
        print(f"  Files analyzed: {stats['count']}")
        print(f"  Average reduction: {avg_reduction:.1f}%")
        print(f"  Total code blocks removed: {stats['code_blocks_removed']}")
        print(f"  Total headers removed: {stats['headers_removed']}")

    # Overall stats
    print(f"\n{'='*100}")
    print(f"OVERALL STATISTICS")
    print(f"{'='*100}")
    avg_reduction = sum(r['reduction_pct'] for r in results) / len(results)
    total_code_removed = sum(r['code_blocks_removed'] for r in results)
    total_headers_removed = sum(r['headers_removed'] for r in results)

    print(f"  Total files analyzed: {len(results)}")
    print(f"  Average reduction: {avg_reduction:.1f}%")
    print(f"  Files with >60% reduction: {len(high_reduction)} ({len(high_reduction)/len(results)*100:.1f}%)")
    print(f"  Files with >75% reduction: {len([r for r in results if r['reduction_pct'] > 75])} ({len([r for r in results if r['reduction_pct'] > 75])/len(results)*100:.1f}%)")
    print(f"  Total code blocks removed: {total_code_removed}")
    print(f"  Total headers removed: {total_headers_removed}")
    print(f"  Files with code blocks removed: {len(code_removed)} ({len(code_removed)/len(results)*100:.1f}%)")

    # Save detailed results for manual inspection
    output_file = base_dir / 'cleaning_analysis.txt'
    with open(output_file, 'w') as f:
        f.write("FILES REQUIRING MANUAL INSPECTION\n")
        f.write("="*100 + "\n\n")

        # Prioritize files for manual review
        priority_files = [r for r in results if
                         r['reduction_pct'] > 60 and
                         (r['code_blocks_removed'] > 0 or r['has_educational_content'])]

        f.write(f"Priority files for manual review: {len(priority_files)}\n\n")
        for result in sorted(priority_files, key=lambda x: x['reduction_pct'], reverse=True):
            f.write(f"{result['file']}\n")

    print(f"\n\nPriority files for manual review saved to: {output_file}")
    print(f"Total priority files: {len(priority_files)}")

if __name__ == '__main__':
    main()
