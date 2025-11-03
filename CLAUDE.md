# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a web scraping and content processing pipeline that converts websites into markdown files for AI/ML processing. The workflow consists of four stages:

1. Web scraping using custom scraper with recursive crawling
2. Content cleaning to remove boilerplate (navigation, footers, ads, etc.)
3. Chunking markdown content for AI processing
4. Merging chunks to JSON for app bundle integration

## Configuration Sets (Recommended)

**Configuration sets are the recommended way to manage pipeline configurations.** Each config set contains all settings for scraping, cleaning, chunking, and merging a specific website.

### Quick Start with Config Sets

```bash
# Run complete pipeline for a config set
./run_pipeline.sh hackingwithswift

# Or run individual steps
python3 scrape.py hackingwithswift
python3 clean.py hackingwithswift
python3 chunk.py hackingwithswift
python3 merge.py hackingwithswift
```

### Directory Structure

```
config/                          # Configuration (version controlled)
  hackingwithswift/
    config.yaml                  # All pipeline configuration
    urls.txt                     # Seed URLs

data/                           # Generated data (gitignored)
  hackingwithswift/
    scrapes/                    # Raw scraped files
    cleaned/                    # Cleaned markdown
    chunks/                     # Chunked files
    merged.json                 # Final JSON output
    urls_to_scrape.txt          # Scraping state
    urls_scraped.txt            # Scraping state
```

### Benefits

- ✅ **Self-contained**: All configs for a site in one directory
- ✅ **Clear separation**: Config (git) vs Data (local)
- ✅ **Single config file**: All pipeline settings in config.yaml
- ✅ **Simple commands**: Just pass the config set name
- ✅ **Scalable**: Easy to add new sites
- ✅ **Safe**: No accidental cross-site contamination

### Creating a New Config Set

```bash
# 1. Create directories
mkdir -p config/mysite
mkdir -p data/mysite

# 2. Create config.yaml (copy and customize from config/hackingwithswift/config.yaml)
# Or see the template in feature/CONFIGURATION.md

# 3. Add seed URLs
echo "https://example.com" > config/mysite/urls.txt

# 4. Run pipeline
./run_pipeline.sh mysite
```

See `feature/CONFIGURATION.md` for complete specification and examples.

## Commands (Legacy & Config Set Modes)

### Web Scraping
```bash
# Using config set (recommended)
python3 scrape.py hackingwithswift

# Using legacy config file
python3 scrape.py  # Reads settings from scrape.yaml

# Or with command-line args
./crawl.sh  # Convenience script with recursive crawling
python3 scrape.py urls.txt --recursive --max-hops 2
```

### Content Cleaning
```bash
# Using config set (recommended)
python3 clean.py hackingwithswift

# Using legacy config file
python3 clean.py  # Reads settings from clean.yaml

# Or with command-line args
python3 clean.py scrapes/ cleaned/ --auto-detect
python3 clean.py scrapes/ cleaned/ --config clean_rules/hackingwithswift.yaml
```

### Chunking Markdown
```bash
# Using config set (recommended)
python3 chunk.py hackingwithswift

# Using legacy approach
python3 chunk.py cleaned/ --out chunks
python3 chunk.py cleaned/ --out chunks --chunk-size 1500 --chunk-overlap 200
```

### Merging to JSON
```bash
# Using config set (recommended)
python3 merge.py hackingwithswift

# Using legacy approach
python3 merge.py chunks -o merged.json --pretty
```

### Python Environment
The project uses Python 3.13.7 in `.venv`. Activate with:
```bash
source .venv/bin/activate
```

## Architecture

### Data Pipeline
1. **Scraping**: `scrape.py` crawls websites recursively, generates markdown files in `scrapes/`
   - Supports recursive crawling with hop limits
   - Skip patterns for excluding URLs
   - Resumable state management
   - Adds YAML frontmatter (original_url, scrape_date, title)

2. **Cleaning**: `clean.py` removes non-valuable content from scraped files
   - Site-specific rules defined in YAML (`clean_rules/`)
   - Auto-detection from file frontmatter domain
   - 25+ rules for HackingWithSwift (removes 34%+ of content)
   - Preserves YAML frontmatter and valuable content

3. **Chunking**: `chunk.py` splits markdown into smaller chunks
   - **Two-stage hierarchy-aware strategy**:
     - Stage 1: Split on markdown headers to preserve document structure
     - Stage 2: Split large sections further (code-fence aware)
   - Preserves original frontmatter from source files
   - Adds rich chunk metadata (breadcrumbs, hierarchy level, word/char counts)
   - Configurable chunk size, overlap, and header levels
   - Generates UUID for each chunk for tracking

4. **Merging**: `merge.py` combines chunks into single JSON file
   - For bulk processing or app bundle integration
   - Optional pretty-printing

### Output Structure
```
scrapes/          # Raw scraped markdown files
├── [domain]_[path].md
cleaned/          # Cleaned markdown files (default output)
├── [domain]_[path].md
chunks/           # Chunked markdown files
├── [file]_chunk_0.md
merged.json       # Combined JSON output
```

### Key Modules

**scrape.py**
- Recursive web crawler with state management
- Converts HTML to markdown with frontmatter
- Configurable via `scrape.yaml` or command-line args

**clean.py**
- Removes navigation, footers, ads, sponsored content, etc.
- Configurable via `clean.yaml` or command-line args
- Auto-detects site config from file frontmatter

**content_cleaner/** (module)
- `rules.py`: 5 rule types (ExactMatch, Regex, SectionBoundary, LinePattern, RepeatingPattern)
- `config.py`: YAML configuration loader with auto-detection
- `cleaner.py`: Main cleaning engine with validation

**chunk.py**
- Two-stage chunking strategy:
  1. **MarkdownHeaderTextSplitter**: Splits on markdown headers (#, ##, ###, etc.)
  2. **MarkdownTextSplitter**: Further splits long sections while preserving code fences
- Preserves original frontmatter and adds chunk-specific metadata
- Configurable via `chunk.yaml` or command-line args

**merge.py**
- Combines chunks into single JSON file

## Chunking Strategy Details

### Available Strategies

The chunker supports two strategies (configured via `chunk.yaml`):

1. **Smart Strategy** (Recommended, Default)
2. **Legacy Strategy** (Original LangChain two-stage approach)

### Smart Strategy (Default)

The smart strategy implements intelligent, content-aware chunking:

**Algorithm:**
1. Check if remaining content < chunk_size → keep as-is
2. Find the **last high-level header** (≤ H3 by default) before chunk_size limit
3. For the first chunk, skip headers before min_pos (1/3 of chunk_size, default ~400 chars) to prevent tiny chunks
4. Split at that header boundary
5. Continue with remaining content

**Benefits:**
- ✅ Prevents tiny first chunks via min_pos constraint (1/3 of chunk_size)
- ✅ Respects document hierarchy and semantic structure
- ✅ Natural boundaries at high-level headers
- ✅ More efficient (fewer, better-sized chunks)
- ✅ Configurable header level threshold
- ✅ No post-processing needed - chunks where it belongs

**Configuration:**
```yaml
strategy: "smart"
max_header_level: 3  # Split on H1, H2, H3 only
```

### Legacy Strategy

The original two-stage hierarchy-aware strategy from LangChain:

#### Stage 1: Header-Based Splitting (MarkdownHeaderTextSplitter)
Splits the document at markdown header boundaries to preserve document structure:
- Splits at specified header levels (default: `#` through `######`)
- Captures heading hierarchy in metadata (h1, h2, h3, etc.)
- Preserves headers in the chunk content (`strip_headers=False`)
- Creates section breadcrumbs (e.g., ["Introduction", "Getting Started", "Installation"])

#### Stage 2: Size-Based Splitting (MarkdownTextSplitter)
For each section from Stage 1, further splits content that exceeds `chunk_size`:
- **Code-fence aware**: Won't break code blocks mid-fence
- Respects `chunk_size` (characters) as target maximum
- Applies `chunk_overlap` for context continuity between chunks
- Creates multiple sub-chunks if section is very large

**Drawbacks:**
- ⚠️ Can create many tiny chunks from short sections
- ⚠️ Splits at ALL header levels (not just high-level ones)
- ⚠️ Pre-header content becomes tiny orphan chunks

**Configuration:**
```yaml
strategy: "legacy"
headers: "#,##,###,####,#####,######"  # All headers
```

### Chunking Variables

| Variable | Default | Unit | Description |
|----------|---------|------|-------------|
| **strategy** | `smart` | string | Chunking strategy: `"smart"` (recommended) or `"legacy"` |
| **chunk_size** | 1200 | characters | Target maximum size for each chunk. Sections exceeding this are split further. |
| **chunk_overlap** | 150 | characters | Overlap between consecutive chunks (legacy strategy only; smart uses natural boundaries). |
| **max_header_level** | 3 | 1-6 | Maximum header level to split on (smart strategy only). 1=H1 only, 3=H1-H3, 6=all headers. |
| **headers** | `#,##,###,####,#####,######` | markdown | Header levels to split on (legacy strategy only). |

### Output Metadata

Each chunk file includes YAML frontmatter with:

**Preserved from original file:**
- `original_url`: Source URL from scraping
- `scrape_date`: When content was scraped
- `title`: Original page title
- Any other custom frontmatter fields

**Added by chunker:**
- `chunk_id`: Unique UUID for this chunk
- `chunk_created_at`: ISO timestamp of chunking
- `source_file`: Relative path to source markdown file
- `chunk_index`: Zero-based index (e.g., 0, 1, 2...)
- `total_chunks`: Total number of chunks from this file
- `section_path`: Ordered list of headers (breadcrumb trail)
- `section_level`: Depth in hierarchy (1-6, or 0 if no headers)
- `section_headers`: Raw header mapping from LangChain
- `char_count`: Character count of chunk content
- `word_count`: Word count of chunk content
- `splitter`: Algorithm used (`SmartHeaderTextSplitter` or `MarkdownHeaderTextSplitter+MarkdownTextSplitter`)
- `chunk_size`: Configuration value used
- `chunk_overlap`: Configuration value used

### Example Chunk Output

```markdown
---
original_url: https://example.com/tutorial
scrape_date: '2025-01-15T10:30:00Z'
title: 'Swift Tutorial'
chunk_id: 550e8400-e29b-41d4-a716-446655440000
chunk_created_at: '2025-01-16T14:22:33Z'
source_file: example_com_tutorial.md
chunk_index: 2
total_chunks: 8
section_path:
  - Introduction
  - Basic Concepts
  - Variables
section_level: 3
char_count: 1150
word_count: 192
splitter: SmartHeaderTextSplitter
chunk_size: 1200
chunk_overlap: 150
---

### Variables

In Swift, you declare variables using the `var` keyword...
```

## Configuration Files

### scrape.yaml
```yaml
urls_file: urls.txt
output_dir: scrapes
recursive: true
max_hops: 2
skip_patterns:
  - "*/users/*"
  - "*/login"
```

### clean.yaml
```yaml
input_dir: scrapes
output_dir: cleaned
rules_dir: clean_rules
auto_detect: true
pattern: "*.md"
dry_run: false
flush: true  # Delete output directory before cleaning (flush-and-fill)
```

### chunk.yaml
```yaml
input_dir: cleaned
output_dir: chunks
chunk_size: 1200
chunk_overlap: 150
headers: "#,##,###,####,#####,######"
strategy: "smart"
max_header_level: 3
flush: true
```

Configuration variables:
- **flush** (default: false): When true, deletes the entire output directory before processing. Ensures clean state and removes orphaned chunks from previous runs. Can be overridden with `--flush` or `--no-flush` flags.
- **strategy** (default: "smart"): Chunking strategy to use. See "Chunking Strategy Details" section above.
- **chunk_size** (default: 1200): Target size in characters for each chunk. After splitting by headers, any section exceeding this size will be split further into smaller chunks.
- **chunk_overlap** (default: 150): Number of characters to overlap between consecutive chunks. Helps maintain context across chunk boundaries for better AI/ML processing.
- **max_header_level** (default: 3): Maximum header level for smart strategy splits (1-6).
- **headers** (default: all 6 levels): Comma-separated list of header levels to split on (e.g., "#,##,###"). Used by legacy strategy.

### clean_rules/[domain].yaml
Site-specific cleaning rules with pattern matching:
- `exact_match`: Remove exact text
- `regex`: Remove content matching regex
- `section_boundary`: Remove content between markers
- `line_pattern`: Remove lines matching pattern
- `repeating_pattern`: Handle duplicates

## Dependencies

Key packages in `.venv`:
- `beautifulsoup4==4.13.4` - HTML parsing
- `markdownify==1.2.0` - HTML to markdown conversion
- `ruamel.yaml==0.18.15` - YAML processing
- `pyyaml==6.0.2` - YAML parsing
- `mdformat==0.7.22` - Markdown formatting
- `langchain-text-splitters` - Text chunking for chunk.py

## State Files

When using `--recursive` with scrape.py:
- `urls_to_scrape.txt` - Queue of URLs to scrape (with hop counts)
- `urls_scraped.txt` - Already processed URLs

Delete these files (or use `--ignore-scraping-state`) to start a fresh crawl.
