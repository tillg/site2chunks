#!/usr/bin/env python3
"""
Web scraper that converts web pages to markdown with frontmatter.
Uses markdownify for HTML to markdown conversion.
Supports recursive crawling with state management.
"""

import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


class URLQueue:
    """Manages the queue of URLs to scrape and tracks scraped URLs."""

    def __init__(self, urls_to_scrape_file="urls_to_scrape.txt",
                 urls_scraped_file="urls_scraped.txt",
                 ignore_state=False):
        """
        Initialize the URL queue manager.

        Args:
            urls_to_scrape_file: Path to file storing URLs to scrape
            urls_scraped_file: Path to file storing already scraped URLs
            ignore_state: If True, ignore existing state files and start fresh
        """
        self.urls_to_scrape_file = Path(urls_to_scrape_file)
        self.urls_scraped_file = Path(urls_scraped_file)

        if ignore_state:
            # Start fresh - clear any existing state
            self.urls_to_scrape = []
            self.urls_scraped = set()
            # Remove state files if they exist
            self.urls_to_scrape_file.unlink(missing_ok=True)
            self.urls_scraped_file.unlink(missing_ok=True)
        else:
            # Load existing state if available
            self.urls_to_scrape = self._load_urls_to_scrape()
            self.urls_scraped = self._load_urls_scraped()

    def _load_urls_to_scrape(self):
        """Load the list of URLs to scrape from file."""
        if self.urls_to_scrape_file.exists():
            with open(self.urls_to_scrape_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(urls)} URLs from {self.urls_to_scrape_file}")
            return urls
        return []

    def _load_urls_scraped(self):
        """Load the set of already scraped URLs from file."""
        if self.urls_scraped_file.exists():
            with open(self.urls_scraped_file, 'r') as f:
                urls = set(line.strip() for line in f if line.strip())
            print(f"Loaded {len(urls)} already scraped URLs from {self.urls_scraped_file}")
            return urls
        return set()

    def save_urls_to_scrape(self):
        """Save the list of URLs to scrape to file."""
        with open(self.urls_to_scrape_file, 'w') as f:
            for url in self.urls_to_scrape:
                f.write(f"{url}\n")

    def save_urls_scraped(self):
        """Save the set of scraped URLs to file."""
        with open(self.urls_scraped_file, 'w') as f:
            for url in sorted(self.urls_scraped):
                f.write(f"{url}\n")

    def add_url_to_scrape(self, url):
        """Add a URL to the scraping queue if not already scraped."""
        if url not in self.urls_scraped and url not in self.urls_to_scrape:
            self.urls_to_scrape.append(url)
            self.save_urls_to_scrape()
            return True
        return False

    def mark_as_scraped(self, url):
        """Mark a URL as scraped."""
        self.urls_scraped.add(url)
        self.save_urls_scraped()
        # Remove from to_scrape list if present
        if url in self.urls_to_scrape:
            self.urls_to_scrape.remove(url)
            self.save_urls_to_scrape()

    def get_next_url(self):
        """Get the next URL to scrape, or None if queue is empty."""
        if self.urls_to_scrape:
            return self.urls_to_scrape[0]
        return None

    def has_urls_to_scrape(self):
        """Check if there are more URLs to scrape."""
        return len(self.urls_to_scrape) > 0

    def initialize_from_file(self, urls_file):
        """Initialize the queue from a URLs file."""
        urls_path = Path(urls_file)
        if not urls_path.exists():
            print(f"Error: URLs file '{urls_file}' not found")
            return

        with open(urls_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

        # Add all URLs to the queue
        added_count = 0
        for url in urls:
            if self.add_url_to_scrape(url):
                added_count += 1

        print(f"Initialized queue with {added_count} URLs from {urls_file}")
        if len(urls) > added_count:
            skipped = len(urls) - added_count
            print(f"Skipped {skipped} URLs (already scraped or in queue)")


def extract_urls_from_html(html_content, base_url):
    """
    Extract all URLs from HTML content that belong to the same domain.

    Args:
        html_content: The HTML content as string
        base_url: The base URL to resolve relative URLs

    Returns:
        List of absolute URLs from the same domain
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    base_parsed = urlparse(base_url)
    base_domain = base_parsed.netloc

    found_urls = set()

    # Find all links
    for link in soup.find_all('a', href=True):
        href = link['href']

        # Convert relative URL to absolute
        absolute_url = urljoin(base_url, href)

        # Parse the absolute URL
        parsed_url = urlparse(absolute_url)

        # Check if same domain (ignoring www prefix)
        url_domain = parsed_url.netloc.replace('www.', '')
        compare_domain = base_domain.replace('www.', '')

        if url_domain == compare_domain:
            # Remove fragment identifier
            clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            if parsed_url.query:
                clean_url += f"?{parsed_url.query}"

            found_urls.add(clean_url)

    return list(found_urls)


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


def scrape(url, output_file=None, output_dir="scrapes", url_queue=None):
    """
    Scrape a URL and save as markdown with frontmatter.

    Args:
        url: The URL to scrape
        output_file: Optional output filename (will auto-generate if not provided)
        output_dir: Directory to save output files (default: "output")
        url_queue: Optional URLQueue instance for discovering new URLs

    Returns:
        Tuple of (Path to the created file or None if failed, list of discovered URLs)
    """
    try:
        # Fetch the page
        print(f"Fetching: {url}")
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()

        # Store the HTML content for URL extraction
        html_content = response.text

        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

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

        # Extract URLs if URL queue is provided
        discovered_urls = []
        if url_queue is not None:
            discovered_urls = extract_urls_from_html(html_content, url)
            new_urls_count = 0
            for discovered_url in discovered_urls:
                if url_queue.add_url_to_scrape(discovered_url):
                    new_urls_count += 1

            if new_urls_count > 0:
                print(f"  ↳ Discovered {new_urls_count} new URLs to scrape")

        return (file_path, discovered_urls)

    except requests.RequestException as e:
        print(f"  ✗ Error fetching {url}: {e}")
        return (None, [])
    except Exception as e:
        print(f"  ✗ Error processing {url}: {e}")
        return (None, [])


def scrape_urls_file(urls_file, output_dir="scrapes", ignore_state=False, recursive=True):
    """
    Scrape all URLs from a file with recursive crawling support.

    Args:
        urls_file: Path to file containing URLs (one per line)
        output_dir: Directory to save output files
        ignore_state: If True, start from scratch ignoring any existing state
        recursive: If True, discover and scrape linked pages from the same domain
    """
    # Initialize URL queue
    url_queue = URLQueue(ignore_state=ignore_state) if recursive else None

    if url_queue:
        # Initialize from URLs file
        url_queue.initialize_from_file(urls_file)
    else:
        # Non-recursive mode: just read URLs from file
        urls_path = Path(urls_file)
        if not urls_path.exists():
            print(f"Error: URLs file '{urls_file}' not found")
            return

        with open(urls_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

    print("=" * 60)

    # Process URLs
    successful = 0
    failed = 0
    processed_count = 0

    if recursive and url_queue:
        # Recursive crawling mode
        while url_queue.has_urls_to_scrape():
            url = url_queue.get_next_url()
            processed_count += 1

            print(f"\n[{processed_count}] Processing (Queue: {len(url_queue.urls_to_scrape)} remaining)...")
            result, discovered_urls = scrape(url, output_dir=output_dir, url_queue=url_queue)

            if result:
                successful += 1
                url_queue.mark_as_scraped(url)
            else:
                failed += 1
                # Still mark as scraped to avoid retrying
                url_queue.mark_as_scraped(url)
    else:
        # Non-recursive mode
        for i, url in enumerate(urls, 1):
            processed_count += 1
            print(f"\n[{i}/{len(urls)}] Processing...")
            result, _ = scrape(url, output_dir=output_dir)
            if result:
                successful += 1
            else:
                failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Complete!")
    print(f"   Total processed: {processed_count}")
    print(f"   Successful: {successful}")
    if failed > 0:
        print(f"   Failed: {failed}")

    if recursive and url_queue:
        print(f"   Total scraped: {len(url_queue.urls_scraped)}")
        print(f"\nState saved to:")
        print(f"   - {url_queue.urls_to_scrape_file}")
        print(f"   - {url_queue.urls_scraped_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Scrape web pages and convert to markdown with frontmatter',
        epilog='Supports recursive crawling with state management for resumable scraping.'
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
    parser.add_argument(
        '--recursive',
        action='store_true',
        default=False,
        help='Enable recursive crawling: discover and scrape linked pages from the same domain'
    )
    parser.add_argument(
        '--ignore-scraping-state',
        action='store_true',
        help='Start from scratch, ignoring any existing scraping state (urls_to_scrape.txt, urls_scraped.txt)'
    )

    args = parser.parse_args()

    if args.file or args.input.endswith('.txt'):
        # Process URLs from file
        scrape_urls_file(
            args.input,
            args.output,
            ignore_state=args.ignore_scraping_state,
            recursive=args.recursive
        )
    else:
        # Process single URL
        if args.output.endswith('.md'):
            # Specific output file provided
            output_dir = Path(args.output).parent
            output_file = Path(args.output).name
            result, _ = scrape(args.input, output_file, output_dir or ".")
        else:
            # Output directory provided
            result, _ = scrape(args.input, output_dir=args.output)


if __name__ == "__main__":
    main()