#!/usr/bin/env python3
"""
Web scraper that converts web pages to markdown with frontmatter.
Uses markdownify for HTML to markdown conversion.
"""

import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def clean_filename(url):
    """Generate a clean filename from a URL."""
    parsed = urlparse(url)
    # Create filename from domain and path
    domain = parsed.netloc.replace('www.', '')
    path = parsed.path.strip('/')

    if path:
        # Replace slashes with underscores
        path_clean = path.replace('/', '_')
        return f"{domain}_{path_clean}.md"
    else:
        return f"{domain}.md"


def scrape(url, output_file=None, output_dir="scrapes"):
    """
    Scrape a URL and save as markdown with frontmatter.

    Args:
        url: The URL to scrape
        output_file: Optional output filename (will auto-generate if not provided)
        output_dir: Directory to save output files (default: "output")

    Returns:
        Path to the created file or None if failed
    """
    try:
        # Fetch the page
        print(f"Fetching: {url}")
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract title for potential use
        title = soup.title.string if soup.title else "Untitled"

        # Convert to markdown
        # Using markdownify with some options for better conversion
        markdown_content = md(
            str(soup),
            heading_style="ATX",  # Use # for headings
            bullets="-",  # Use - for bullet points
            code_language="",  # Don't add language hints to code blocks
            strip=["img", "svg"],  # Remove images for cleaner text
        )

        # Clean up excessive newlines
        lines = markdown_content.split('\n')
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            is_empty = len(line.strip()) == 0
            if is_empty and prev_empty:
                continue  # Skip multiple empty lines
            cleaned_lines.append(line)
            prev_empty = is_empty

        markdown_content = '\n'.join(cleaned_lines)

        # Prepare output
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Determine output file
        if output_file:
            file_path = output_path / output_file
        else:
            file_path = output_path / clean_filename(url)

        # Create frontmatter
        scrape_date = datetime.now().strftime('%Y-%m-%d')
        frontmatter = f"""---
original_url: {url}
scrape_date: {scrape_date}
title: {title}
---

"""

        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter + markdown_content)

        print(f"  ✓ Saved to: {file_path}")
        return file_path

    except requests.RequestException as e:
        print(f"  ✗ Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"  ✗ Error processing {url}: {e}")
        return None


def scrape_urls_file(urls_file, output_dir="scrapes"):
    """
    Scrape all URLs from a file.

    Args:
        urls_file: Path to file containing URLs (one per line)
        output_dir: Directory to save output files
    """
    urls_path = Path(urls_file)
    if not urls_path.exists():
        print(f"Error: URLs file '{urls_file}' not found")
        return

    # Read URLs
    with open(urls_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Found {len(urls)} URLs to scrape")
    print("=" * 60)

    # Process each URL
    successful = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing...")
        result = scrape(url, output_dir=output_dir)
        if result:
            successful += 1
        else:
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Complete!")
    print(f"   Successful: {successful}")
    if failed > 0:
        print(f"   Failed: {failed}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Scrape web pages and convert to markdown with frontmatter'
    )
    parser.add_argument(
        'input',
        help='URL to scrape OR path to file containing URLs'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file name (for single URL) or directory (for multiple URLs)',
        default='scrapes'
    )
    parser.add_argument(
        '-f', '--file',
        action='store_true',
        help='Treat input as a file containing URLs'
    )

    args = parser.parse_args()

    if args.file or args.input.endswith('.txt'):
        # Process URLs from file
        scrape_urls_file(args.input, args.output)
    else:
        # Process single URL
        if args.output.endswith('.md'):
            # Specific output file provided
            output_dir = Path(args.output).parent
            output_file = Path(args.output).name
            scrape(args.input, output_file, output_dir or ".")
        else:
            # Output directory provided
            scrape(args.input, output_dir=args.output)


if __name__ == "__main__":
    main()