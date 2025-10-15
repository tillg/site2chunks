# site2chunks

Transform web sites to markdown files and chunk them.

Websites I look at:

* getA12 / Doc (internal to [mgm technology partners](https://www.mgm-tp.com/a12.html) at thge time of writing)
* HackingWithSwift / [100 Days of SwiftUI](https://www.hackingwithswift.com/100/swiftui/)

## Setup

Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Scraping Websites

Scrape websites and convert them to markdown with frontmatter:

```bash
# Using config file (recommended): reads settings from scrape_config.yaml
python3 scraper.py

# Basic scraping: scrape all URLs from urls.txt
python3 scraper.py urls.txt

# Recursive crawling: discover and scrape linked pages from the same domain
python3 scraper.py urls.txt --recursive

# Recursive crawling with hop limit (max 2 hops from seed URLs)
python3 scraper.py urls.txt --recursive --max-hops 2

# Skip specific URL patterns (supports wildcards)
python3 scraper.py urls.txt --recursive --skip-pattern "*/users/*" --skip-pattern "*/login"

# Start from scratch (ignore previous scraping state)
python3 scraper.py urls.txt --recursive --ignore-scraping-state

# Scrape a single URL
python3 scraper.py "https://example.com/page" -o scrapes/custom_name.md

# Scrape URLs from a file to a custom directory
python3 scraper.py urls.txt -o my_scrapes/
```

#### Configuration File (scrape_config.yaml)

The scraper can be configured using a YAML file for easier management of scraping rules:

```yaml
# Input file containing seed URLs (one per line)
urls_file: urls.txt

# Output directory for scraped markdown files
output_dir: scrapes

# Enable recursive crawling
recursive: true

# Maximum number of hops from seed URLs (0 = only seed URLs, null = unlimited)
max_hops: 2

# URL patterns to skip (supports wildcards: * for any characters)
skip_patterns:
  - "https://www.hackingwithswift.com/users/*"
  - "*/login"
  - "*/register"
  - "*/auth/*"

# State files for tracking scraping progress
state_files:
  urls_to_scrape: urls_to_scrape.txt
  urls_scraped: urls_scraped.txt

# Whether to ignore existing scraping state and start fresh
ignore_scraping_state: false
```

When `scrape_config.yaml` exists, you can simply run:
```bash
python3 scraper.py
```

Command-line arguments will override config file settings.

#### Recursive Crawling Features

When using `--recursive`, the scraper will:
- Extract all URLs from each scraped page
- Only scrape URLs from the same domain
- Automatically convert relative URLs to absolute URLs
- Respect hop limits (distance from seed URLs)
- Skip URLs matching configured patterns
- Track scraping progress in state files:
  - `urls_to_scrape.txt` - URLs waiting to be scraped (with hop count)
  - `urls_scraped.txt` - URLs already processed

**Resumable Scraping**: If interrupted, simply run the command again without `--ignore-scraping-state` to continue where you left off. The scraper will skip already-scraped URLs automatically.

Each scraped file includes frontmatter with:
- `original_url`: The source URL
- `scrape_date`: When the content was scraped
- `title`: Page title

### 2. Chunking Markdown Files

Split markdown files into smaller chunks for AI/ML processing while preserving frontmatter:

```bash
# Chunk all files in scrapes/ directory
python3 chunkify.py scrapes/ --out chunks

# Chunk a single file
python3 chunkify.py scrapes/file.md --out chunks

# Custom chunk size and overlap
python3 chunkify.py scrapes/ --out chunks --chunk-size 1500 --chunk-overlap 200
```

Each chunk preserves the original frontmatter and adds:
- `chunk_id`: Unique chunk identifier
- `chunk_index`: Position in the source file
- `total_chunks`: Total number of chunks from source
- `section_path`: Hierarchical breadcrumb of headers
- `char_count` and `word_count`: Size metrics

### 3. Merging Chunks to JSON

Combine all chunks into a single JSON file for bulk processing:

```bash
# Merge all chunks into a JSON file
python3 merge_chunks.py chunks -o merged_chunks.json

# With pretty formatting for readability
python3 merge_chunks.py chunks -o merged_chunks.json --pretty

# From a custom directory
python3 merge_chunks.py my_chunks/ -o output.json
```

Each chunk in the JSON includes:
* `original_url` - Source URL
* `scrape_date` - When scraped
* `title` - Page title
* `chunk_index` - Position in source
* `content` - The chunk text

### Quick Start

```bash
# 1. Configure your scraping (optional but recommended)
#    Edit scrape_config.yaml to set:
#    - urls_file: path to your URLs file
#    - max_hops: how far to crawl from seed URLs
#    - skip_patterns: URL patterns to avoid

# 2. Add URLs to urls.txt (one per line)
echo "https://example.com/article" > urls.txt

# 3. Scrape the URLs
python3 scraper.py  # Uses scrape_config.yaml if present
# OR
./crawl.sh  # Uses default recursive settings

# 4. Chunk the scraped content
python3 chunkify.py scrapes/ --out chunks

# 5. Merge chunks to JSON (optional)
python3 merge_chunks.py chunks -o merged.json --pretty
```

**Note**: With `--recursive`, the scraper discovers and scrapes linked pages automatically. Use `max_hops` to limit crawling depth and `skip_patterns` to exclude unwanted URLs.

## File Structure

```
.
├── scrape_config.yaml    # Configuration file for scraping rules
├── urls.txt              # List of URLs to scrape (seed URLs)
├── urls_to_scrape.txt    # Queue of URLs to scrape (recursive mode, with hop counts)
├── urls_scraped.txt      # Already scraped URLs (recursive mode)
├── scraper.py            # Web scraping script
├── chunkify.py           # Markdown chunking script
├── merge_chunks.py       # Merge chunks to JSON
├── crawl.sh              # Convenience script for scraping
├── scrapes/              # Scraped markdown files (default output)
├── chunks/               # Chunked markdown files
└── merged.json           # Combined chunks in JSON format
```

**Configuration File**: `scrape_config.yaml` allows you to configure scraping behavior including hop limits, skip patterns, and output directories.

**State Files**: When using `--recursive`, the scraper maintains state in `urls_to_scrape.txt` (with hop counts stored as JSON) and `urls_scraped.txt`. Delete these files (or use `--ignore-scraping-state`) to start a fresh crawl.

