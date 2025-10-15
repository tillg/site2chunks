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
# Basic scraping: scrape all URLs from urls.txt
python3 scraper.py urls.txt

# Recursive crawling: discover and scrape linked pages from the same domain
python3 scraper.py urls.txt --recursive

# Start from scratch (ignore previous scraping state)
python3 scraper.py urls.txt --recursive --ignore-scraping-state

# Scrape a single URL
python3 scraper.py "https://example.com/page" -o scrapes/custom_name.md

# Scrape URLs from a file to a custom directory
python3 scraper.py urls.txt -o my_scrapes/
```

#### Recursive Crawling Features

When using `--recursive`, the scraper will:
- Extract all URLs from each scraped page
- Only scrape URLs from the same domain
- Automatically convert relative URLs to absolute URLs
- Track scraping progress in state files:
  - `urls_to_scrape.txt` - URLs waiting to be scraped
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
# 1. Add URLs to urls.txt (one per line)
echo "https://example.com/article" > urls.txt

# 2. Scrape the URLs with recursive crawling
./crawl.sh  # or: python3 scraper.py urls.txt --recursive

# 3. Chunk the scraped content
python3 chunkify.py scrapes/ --out chunks

# 4. Merge chunks to JSON (optional)
python3 merge_chunks.py chunks -o merged.json --pretty
```

**Note**: The scraper with `--recursive` will discover and scrape linked pages automatically. To start fresh, use `--ignore-scraping-state`.

## File Structure

```
.
├── urls.txt              # List of URLs to scrape (seed URLs)
├── urls_to_scrape.txt    # Queue of URLs to scrape (recursive mode)
├── urls_scraped.txt      # Already scraped URLs (recursive mode)
├── scraper.py            # Web scraping script
├── chunkify.py           # Markdown chunking script
├── merge_chunks.py       # Merge chunks to JSON
├── crawl.sh              # Convenience script for scraping
├── scrapes/              # Scraped markdown files (default output)
├── chunks/               # Chunked markdown files
└── merged.json           # Combined chunks in JSON format
```

**State Files**: When using `--recursive`, the scraper maintains state in `urls_to_scrape.txt` and `urls_scraped.txt`. Delete these files (or use `--ignore-scraping-state`) to start a fresh crawl.

