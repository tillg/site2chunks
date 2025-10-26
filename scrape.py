#!/usr/bin/env python3
"""
Web scraper that converts web pages to markdown with frontmatter.
Uses markdownify for HTML to markdown conversion.
Supports recursive crawling with state management.
Supports YAML configuration for flexible scraping rules.
"""

import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
import fnmatch
import json
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import yaml


def match_url_pattern(url, pattern):
    """
    Check if a URL matches a pattern (supports wildcards).

    Args:
        url: The URL to check
        pattern: The pattern to match against (supports * wildcard)

    Returns:
        True if the URL matches the pattern
    """
    return fnmatch.fnmatch(url, pattern)


def should_skip_url(url, skip_patterns):
    """
    Check if a URL should be skipped based on skip patterns.

    Args:
        url: The URL to check
        skip_patterns: List of patterns to match against

    Returns:
        True if the URL should be skipped
    """
    if not skip_patterns:
        return False

    for pattern in skip_patterns:
        if match_url_pattern(url, pattern):
            return True

    return False


class URLQueue:
    """Manages the queue of URLs to scrape and tracks scraped URLs with hop counting."""

    def __init__(self, urls_to_scrape_file="urls_to_scrape.txt",
                 urls_scraped_file="urls_scraped.txt",
                 ignore_state=False,
                 max_hops=None,
                 skip_patterns=None):
        """
        Initialize the URL queue manager.

        Args:
            urls_to_scrape_file: Path to file storing URLs to scrape
            urls_scraped_file: Path to file storing already scraped URLs
            ignore_state: If True, ignore existing state files and start fresh
            max_hops: Maximum number of hops from seed URLs (None = unlimited)
            skip_patterns: List of URL patterns to skip
        """
        self.urls_to_scrape_file = Path(urls_to_scrape_file)
        self.urls_scraped_file = Path(urls_scraped_file)
        self.max_hops = max_hops
        self.skip_patterns = skip_patterns or []
        self.current_url_hop = {}  # Track hop count for URLs being processed

        if ignore_state:
            # Start fresh - clear any existing state
            self.urls_to_scrape = []  # List of dicts: {'url': str, 'hop': int}
            self.urls_scraped = set()
            # Remove state files if they exist
            self.urls_to_scrape_file.unlink(missing_ok=True)
            self.urls_scraped_file.unlink(missing_ok=True)
        else:
            # Load existing state if available
            self.urls_to_scrape = self._load_urls_to_scrape()
            self.urls_scraped = self._load_urls_scraped()

    def _load_urls_to_scrape(self):
        """Load the list of URLs to scrape from file (with hop count)."""
        if self.urls_to_scrape_file.exists():
            with open(self.urls_to_scrape_file, 'r') as f:
                urls = []
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Try to parse as JSON (new format with hop count)
                    try:
                        url_data = json.loads(line)
                        urls.append(url_data)
                    except json.JSONDecodeError:
                        # Legacy format: just URL strings (assume hop 0)
                        urls.append({'url': line, 'hop': 0})
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
        """Save the list of URLs to scrape to file (with hop count)."""
        with open(self.urls_to_scrape_file, 'w') as f:
            for url_data in self.urls_to_scrape:
                f.write(json.dumps(url_data) + "\n")

    def save_urls_scraped(self):
        """Save the set of scraped URLs to file."""
        with open(self.urls_scraped_file, 'w') as f:
            for url in sorted(self.urls_scraped):
                f.write(f"{url}\n")

    def add_url_to_scrape(self, url, hop=0):
        """
        Add a URL to the scraping queue if not already scraped.

        Args:
            url: The URL to add
            hop: The hop count from seed URLs

        Returns:
            True if URL was added, False if skipped
        """
        # Check if URL should be skipped based on patterns
        if should_skip_url(url, self.skip_patterns):
            return False

        # Check if hop count exceeds max_hops
        if self.max_hops is not None and hop > self.max_hops:
            return False

        # Check if already scraped or in queue
        if url in self.urls_scraped:
            return False

        # Check if already in queue
        for url_data in self.urls_to_scrape:
            if url_data['url'] == url:
                return False

        # Add to queue
        self.urls_to_scrape.append({'url': url, 'hop': hop})
        self.save_urls_to_scrape()
        return True

    def mark_as_scraped(self, url):
        """Mark a URL as scraped."""
        self.urls_scraped.add(url)
        self.save_urls_scraped()
        # Remove from to_scrape list if present
        self.urls_to_scrape = [u for u in self.urls_to_scrape if u['url'] != url]
        self.save_urls_to_scrape()

    def get_next_url(self):
        """
        Get the next URL to scrape, or None if queue is empty.
        Also stores the hop count for the URL being processed.

        Returns:
            URL string or None
        """
        if self.urls_to_scrape:
            url_data = self.urls_to_scrape[0]
            url = url_data['url']
            # Store hop count for this URL
            self.current_url_hop[url] = url_data['hop']
            return url
        return None

    def get_url_hop_count(self, url):
        """
        Get the hop count for a URL.

        Args:
            url: The URL to look up

        Returns:
            The hop count for the URL (0 if not found, meaning it's a seed URL)
        """
        # First check if it's the current URL being processed
        if url in self.current_url_hop:
            return self.current_url_hop[url]

        # Check if URL is in the queue
        for url_data in self.urls_to_scrape:
            if url_data['url'] == url:
                return url_data['hop']

        # Default to 0 (seed URL hop count)
        return 0

    def has_urls_to_scrape(self):
        """Check if there are more URLs to scrape."""
        return len(self.urls_to_scrape) > 0

    def initialize_from_file(self, urls_file):
        """Initialize the queue from a URLs file (seed URLs at hop 0)."""
        urls_path = Path(urls_file)
        if not urls_path.exists():
            print(f"Error: URLs file '{urls_file}' not found")
            return

        with open(urls_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]

        # Add all URLs to the queue with hop count 0 (seed URLs)
        added_count = 0
        skipped_count = 0
        for url in urls:
            if self.add_url_to_scrape(url, hop=0):
                added_count += 1
            else:
                skipped_count += 1

        print(f"Initialized queue with {added_count} seed URLs from {urls_file}")
        if skipped_count > 0:
            print(f"Skipped {skipped_count} URLs (already scraped, in queue, or matched skip pattern)")


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

        # Create frontmatter using yaml.safe_dump for proper escaping
        scrape_date = datetime.now().strftime('%Y-%m-%d')
        frontmatter_dict = {
            'original_url': str(url),
            'scrape_date': str(scrape_date),
            'title': str(title)
        }
        frontmatter = "---\n" + yaml.safe_dump(frontmatter_dict, allow_unicode=True, sort_keys=False) + "---\n\n"

        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter + markdown_content)

        print(f"  ✓ Saved to: {file_path}")

        # Extract URLs if URL queue is provided
        discovered_urls = []
        if url_queue is not None:
            # Get current hop count for this URL
            current_hop = url_queue.get_url_hop_count(url)
            next_hop = current_hop + 1

            discovered_urls = extract_urls_from_html(html_content, url)
            new_urls_count = 0
            skipped_by_pattern = 0
            skipped_by_hop = 0

            for discovered_url in discovered_urls:
                # Check skip patterns first (for reporting)
                if should_skip_url(discovered_url, url_queue.skip_patterns):
                    skipped_by_pattern += 1
                    continue

                # Check hop limit
                if url_queue.max_hops is not None and next_hop > url_queue.max_hops:
                    skipped_by_hop += 1
                    continue

                # Try to add URL
                if url_queue.add_url_to_scrape(discovered_url, hop=next_hop):
                    new_urls_count += 1

            if new_urls_count > 0:
                print(f"  ↳ Discovered {new_urls_count} new URLs to scrape (hop {next_hop})")
            if skipped_by_pattern > 0:
                print(f"  ↳ Skipped {skipped_by_pattern} URLs (matched skip patterns)")
            if skipped_by_hop > 0:
                print(f"  ↳ Skipped {skipped_by_hop} URLs (exceeded max hops: {url_queue.max_hops})")

        return (file_path, discovered_urls)

    except requests.RequestException as e:
        print(f"  ✗ Error fetching {url}: {e}")
        return (None, [])
    except Exception as e:
        print(f"  ✗ Error processing {url}: {e}")
        return (None, [])


def load_config(config_file="scrape.yaml"):
    """
    Load configuration from YAML file.

    Args:
        config_file: Path to configuration file

    Returns:
        Dictionary with configuration or None if file doesn't exist
    """
    config_path = Path(config_file)
    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"Loaded configuration from {config_file}")
        return config
    except Exception as e:
        print(f"Error loading config file: {e}")
        return None


def scrape_urls_file(urls_file, output_dir="scrapes", ignore_state=False, recursive=True,
                     max_hops=None, skip_patterns=None, state_files=None):
    """
    Scrape all URLs from a file with recursive crawling support.

    Args:
        urls_file: Path to file containing URLs (one per line)
        output_dir: Directory to save output files
        ignore_state: If True, start from scratch ignoring any existing state
        recursive: If True, discover and scrape linked pages from the same domain
        max_hops: Maximum number of hops from seed URLs (None = unlimited)
        skip_patterns: List of URL patterns to skip
        state_files: Dict with 'urls_to_scrape' and 'urls_scraped' file paths
    """
    # Prepare state file paths
    if state_files is None:
        state_files = {
            'urls_to_scrape': 'urls_to_scrape.txt',
            'urls_scraped': 'urls_scraped.txt'
        }

    # Initialize URL queue
    url_queue = URLQueue(
        urls_to_scrape_file=state_files['urls_to_scrape'],
        urls_scraped_file=state_files['urls_scraped'],
        ignore_state=ignore_state,
        max_hops=max_hops,
        skip_patterns=skip_patterns
    ) if recursive else None

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
        epilog='Supports recursive crawling with state management. Can be configured via scrape.yaml.'
    )
    parser.add_argument(
        'input',
        nargs='?',
        help='URL to scrape OR path to file containing URLs (optional if scrape.yaml exists)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file name (for single URL) or directory (for multiple URLs)',
        default=None
    )
    parser.add_argument(
        '-f', '--file',
        action='store_true',
        help='Treat input as a file containing URLs'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        default=None,
        help='Enable recursive crawling: discover and scrape linked pages from the same domain'
    )
    parser.add_argument(
        '--ignore-scraping-state',
        action='store_true',
        help='Start from scratch, ignoring any existing scraping state'
    )
    parser.add_argument(
        '--config',
        default='scrape.yaml',
        help='Path to configuration file (default: scrape.yaml)'
    )
    parser.add_argument(
        '--max-hops',
        type=int,
        default=None,
        help='Maximum number of hops from seed URLs'
    )
    parser.add_argument(
        '--skip-pattern',
        action='append',
        dest='skip_patterns',
        help='URL pattern to skip (can be specified multiple times)'
    )

    args = parser.parse_args()

    # Try to load config file
    config = load_config(args.config)

    # Determine parameters (command line args override config file)
    if config:
        urls_file = args.input if args.input else config.get('urls_file', 'urls.txt')
        output_dir = args.output if args.output else config.get('output_dir', 'scrapes')
        recursive = args.recursive if args.recursive is not None else config.get('recursive', False)
        max_hops = args.max_hops if args.max_hops is not None else config.get('max_hops')
        skip_patterns = args.skip_patterns if args.skip_patterns else config.get('skip_patterns', [])
        state_files = config.get('state_files', {
            'urls_to_scrape': 'urls_to_scrape.txt',
            'urls_scraped': 'urls_scraped.txt'
        })
        ignore_state = args.ignore_scraping_state or config.get('ignore_scraping_state', False)
    else:
        # No config file - use command line args and defaults
        if not args.input:
            parser.error("input is required when no config file is present")
        urls_file = args.input
        output_dir = args.output if args.output else 'scrapes'
        recursive = args.recursive if args.recursive is not None else False
        max_hops = args.max_hops
        skip_patterns = args.skip_patterns or []
        state_files = {
            'urls_to_scrape': 'urls_to_scrape.txt',
            'urls_scraped': 'urls_scraped.txt'
        }
        ignore_state = args.ignore_scraping_state

    # Check if input is a file or URL
    if args.file or (urls_file and Path(urls_file).exists() and urls_file.endswith('.txt')):
        # Process URLs from file
        scrape_urls_file(
            urls_file,
            output_dir,
            ignore_state=ignore_state,
            recursive=recursive,
            max_hops=max_hops,
            skip_patterns=skip_patterns,
            state_files=state_files
        )
    else:
        # Process single URL
        if output_dir and output_dir.endswith('.md'):
            # Specific output file provided
            output_path = Path(output_dir).parent
            output_file = Path(output_dir).name
            result, _ = scrape(urls_file, output_file, output_path or ".")
        else:
            # Output directory provided
            result, _ = scrape(urls_file, output_dir=output_dir)


if __name__ == "__main__":
    main()