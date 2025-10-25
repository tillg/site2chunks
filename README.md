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

### Optional: Configure API Keys for QA Generation

If you plan to use the QA generation feature with AI models, set up your API keys:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

Add your keys to `.env`:
```bash
ANTHROPIC_API_KEY=your-anthropic-key-here
OPENAI_API_KEY=your-openai-key-here
```

The `.env` file is already in `.gitignore` to keep your keys safe. You can skip this step if you only want to extract existing questions (`--extract-only`) or use local models.

## Pipeline

The pipeline comprises multiple steps:

1. **Scrape** the raw data from the website and save it as MD files ✅
2. **Clean** MD files ✅
   * Remove navigation menus, footers, ads, and other boilerplate
   * Site-specific rules defined in YAML configuration
3. **Summarize** Add summaries to the MD files (TODO)
4. **Chunk** the MD files to small MD files ✅
   * Offer different chunker strategies
5. **Merge** the chunks to one big JSON so it can be added to an App bundle ✅
6. **GenerateQA** Generate test questions for retrieval evaluation ✅
   * Extract existing interview questions from content
   * Generate synthetic questions using LLM
   * Interactive review and curation interface
   * Export to standard test formats (JSON, CSV, TREC)

## Usage

### 1. Scraping Websites

Scrape websites and convert them to markdown with frontmatter:

```bash
# Using config file (recommended): reads settings from scrape.yaml
python3 scrape.py

# Basic scraping: scrape all URLs from urls.txt
python3 scrape.py urls.txt

# Recursive crawling: discover and scrape linked pages from the same domain
python3 scrape.py urls.txt --recursive

# Recursive crawling with hop limit (max 2 hops from seed URLs)
python3 scrape.py urls.txt --recursive --max-hops 2

# Skip specific URL patterns (supports wildcards)
python3 scrape.py urls.txt --recursive --skip-pattern "*/users/*" --skip-pattern "*/login"

# Start from scratch (ignore previous scraping state)
python3 scrape.py urls.txt --recursive --ignore-scraping-state

# Scrape a single URL
python3 scrape.py "https://example.com/page" -o scrapes/custom_name.md

# Scrape URLs from a file to a custom directory
python3 scrape.py urls.txt -o my_scrapes/
```

#### Configuration File (scrape.yaml)

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

When `scrape.yaml` exists, you can simply run:
```bash
python3 scrape.py
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

### 2. Cleaning Scraped Content

Remove non-valuable content like navigation menus, footers, sponsored content, and other boilerplate:

```bash
# Using config file (recommended): reads settings from clean.yaml
python3 clean.py

# Clean all files in scrapes/ directory using auto-detected config
python3 clean.py scrapes/ cleaned_scrapes/ --auto-detect

# Use specific configuration file
python3 clean.py scrapes/ cleaned_scrapes/ --config clean_rules/hackingwithswift.yaml

# Preview changes without modifying files (dry-run)
python3 clean.py scrapes/ --dry-run --config clean_rules/hackingwithswift.yaml

# Show detailed diff preview for first file
python3 clean.py scrapes/file.md --preview --config clean_rules/hackingwithswift.yaml

# Clean a single file
python3 clean.py scrapes/file.md cleaned_scrapes/file.md --config clean_rules/hackingwithswift.yaml
```

#### Configuration File (clean.yaml)

The cleaner can be configured using a YAML file for easier management:

```yaml
# Input directory containing scraped markdown files
input_dir: scrapes

# Output directory for cleaned markdown files
output_dir: cleaned

# Rules directory containing site-specific cleaning configurations
rules_dir: clean_rules

# Auto-detect site configuration from file frontmatter
auto_detect: true

# File pattern to match (glob pattern)
pattern: "*.md"

# Enable dry-run mode (preview changes without modifying files)
dry_run: false
```

When `clean.yaml` exists, you can simply run:
```bash
python3 clean.py
```

Command-line arguments will override config file settings.

#### Cleaning Rules Configuration

Create site-specific cleaning rules in YAML format in the `clean_rules/` directory:

```yaml
site: example.com

# Files to delete entirely (no content value)
# These will be deleted from output directory and skipped during processing
delete_files:
  - example.com_homepage.md
  - example.com_about.md

rules:
  # Remove exact text matches
  - type: exact_match
    description: "Login prompts"
    pattern: "Please log in to continue"
    max_remove: -1  # -1 means remove all occurrences

  # Remove content matching regex patterns
  - type: regex
    description: "Sponsored content blocks"
    pattern: '\*\*SPONSORED\*\*.*?\n\n\[.*?\]\(.*?\)'
    flags: [MULTILINE, DOTALL]

  # Remove content between markers
  - type: section_boundary
    description: "Footer content"
    start_marker: "Follow us on social media"
    end_marker: "© 2025 Company Name"
    inclusive: true

  # Remove lines matching a pattern
  - type: line_pattern
    description: "Newsletter prompts"
    pattern: '^Subscribe to our newsletter'

  # Handle repeated elements
  - type: repeating_pattern
    description: "Store links"
    pattern: '[Visit our store](/store)'
    keep_first: false  # Remove all occurrences
```

**Available Rule Types:**
- `exact_match`: Remove exact text strings
- `regex`: Remove content matching regular expressions
- `section_boundary`: Remove content between start/end markers
- `line_pattern`: Remove entire lines matching a pattern
- `repeating_pattern`: Handle duplicate content (keep first/last/none)

**Features:**
- Preserves YAML frontmatter
- Site-specific configurations
- Auto-detection from file domain
- Dry-run mode for safe previewing
- Delete entire files with no content value
- Detailed statistics and warnings
- Whitespace normalization

### 3. Summarizing pages

TODO

### 4. Chunking Markdown Files

Split markdown files into smaller chunks for AI/ML processing while preserving frontmatter:

```bash
# Using config file (recommended): reads settings from chunk.yaml
python3 chunk.py

# Chunk all files in a directory
python3 chunk.py cleaned/ --out chunks

# Chunk a single file
python3 chunk.py cleaned/file.md --out chunks

# Custom chunk size and overlap
python3 chunk.py cleaned/ --out chunks --chunk-size 1500 --chunk-overlap 200
```

#### Configuration File (chunk.yaml)

The chunker can be configured using a YAML file for easier management:

```yaml
# Input directory containing markdown files to chunk
input_dir: cleaned

# Output directory for chunked markdown files
output_dir: chunks

# Target chunk size in characters
chunk_size: 1200

# Character overlap between consecutive chunks
chunk_overlap: 150

# Comma-separated heading levels to split on
# Use # for H1, ## for H2, etc.
headers: "#,##,###,####,#####,######"
```

When `chunk.yaml` exists, you can simply run:
```bash
python3 chunk.py
```

Command-line arguments will override config file settings.

Each chunk preserves the original frontmatter and adds:
- `chunk_id`: Unique chunk identifier
- `chunk_index`: Position in the source file
- `total_chunks`: Total number of chunks from source
- `section_path`: Hierarchical breadcrumb of headers
- `char_count` and `word_count`: Size metrics

### 5. Merging Chunks to JSON

Combine all chunks into a single JSON file for bulk processing:

```bash
# Merge all chunks into a JSON file
python3 merge.py chunks -o merged_chunks.json

# With pretty formatting for readability
python3 merge.py chunks -o merged_chunks.json --pretty

# From a custom directory
python3 merge.py my_chunks/ -o output.json
```

Each chunk in the JSON includes:
* `original_url` - Source URL
* `scrape_date` - When scraped
* `title` - Page title
* `chunk_index` - Position in source
* `content` - The chunk text

### 6. Generating QA Test Sets

Create test question sets for evaluating retrieval systems. This step extracts existing interview questions from your content and optionally generates synthetic questions using LLMs (Anthropic, OpenAI, or local models).

#### Setup API Keys

First, configure your API keys in a `.env` file (recommended) or as environment variables:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys
# ANTHROPIC_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
```

The `.env` file is automatically loaded and already included in `.gitignore` for security.

**Alternatively**, set environment variables directly:
```bash
export ANTHROPIC_API_KEY='your-key-here'
export OPENAI_API_KEY='your-key-here'
```

#### List Available Models

Before generating questions, you can list available models for each provider:

```bash
# List models for default provider (from config)
python3 generate_qa.py --list-models

# List models for specific provider
python3 generate_qa.py --list-models --provider openai
python3 generate_qa.py --list-models --provider local

# For Anthropic: Shows common Claude models
# For OpenAI: Queries API for available models
# For Local: Queries your local server (LM Studio, Ollama)
```

#### Generate Questions

```bash
# Using config file (recommended): reads settings from generate_qa.yaml
python3 generate_qa.py

# Extract all interview questions from chunks (no API required)
python3 generate_qa.py --extract-only

# Extract AND generate 50 synthetic questions using Anthropic
python3 generate_qa.py -n 50

# Use OpenAI instead
python3 generate_qa.py --provider openai -n 50

# Use local model via LM Studio or Ollama (no API key needed)
python3 generate_qa.py --provider local -n 50

# Generate more questions per chunk
python3 generate_qa.py -n 100 -q 5
```

#### Output Format

QA pairs are saved as individual markdown files in the `qa/` directory:

**File naming:**
- `<chunk_base>_001.md`, `<chunk_base>_002.md`, etc.
- Example: `hackingwithswift.com_interview-questions_001.md`

**Markdown structure:**
```markdown
---
chunk_file: chunks/hackingwithswift.com_100_0001.md
generation_model: claude-3-5-haiku-20241022
generation_date: 2025-10-25
source_type: interview_question
confidence: extracted
---

# Question

How do I create a new Swift project?

# Expected Chunk

**File:** `hackingwithswift.com_100_0001.md`
**Chunk ID:** `abc-123-def`
**Source URL:** https://www.hackingwithswift.com/100
**Section Path:** Getting Started > Creating Projects
```

#### Configuration File (generate_qa.yaml)

The generator can be configured using a YAML file for easier management:

```yaml
# Input/output settings
chunks_dir: chunks
output_dir: qa               # Output directory for markdown files
num_chunks: 50              # 0 = extract only, no synthetic generation
questions_per_chunk: 3
pattern: "*.md"
random_seed: 42

# Extract existing interview questions
extract_interview_questions: true

# LLM provider: anthropic, openai, or local
llm_provider: anthropic

# Model-specific settings
models:
  anthropic:
    model: claude-3-5-haiku-20241022
    max_tokens: 1000
    temperature: 0.7

  openai:
    model: gpt-4o-mini
    max_tokens: 1000
    temperature: 0.7

  local:
    model: llama-3.1-8b
    base_url: http://localhost:1234/v1  # LM Studio
    api_key: not-needed
    max_tokens: 1000
    temperature: 0.7
```

When `generate_qa.yaml` exists, you can simply run:
```bash
python3 generate_qa.py
```

Command-line arguments will override config file settings.

**Review and curate questions:**

```bash
# Show statistics
python3 review_qa.py questions.json --stats

# Auto-approve extracted interview questions (high confidence)
python3 review_qa.py questions.json --auto-approve-extracted -o curated.json

# Interactive review (approve/reject/edit questions)
python3 review_qa.py questions.json -o curated.json
```

**Export to standard test formats:**

```bash
# Export approved questions to JSON
python3 export_qa.py curated.json -o test_set.json --pretty

# Export to multiple formats
python3 export_qa.py curated.json -o test_set -f all
# Creates: test_set.json, test_set.jsonl, test_set.csv, test_set.trec, test_set.md

# Export to TREC qrels format for retrieval evaluation
python3 export_qa.py curated.json -o qrels.trec -f trec
```

**What you get:**

Each test case includes:
* `question` - The test question
* `expected_chunk_id` - Ground truth chunk that should be retrieved
* `chunk_path` - Path to the expected chunk file
* `source_url` - Original page URL
* `source_type` - `interview_question` (extracted) or `synthetic` (generated)

**Use cases:**
* Evaluate retrieval/search quality (Recall@k, MRR)
* Test semantic search systems
* Benchmark different embedding models
* A/B test chunking strategies

### Quick Start

```bash
# 1. Configure your scraping (optional but recommended)
#    Edit scrape.yaml to set:
#    - urls_file: path to your URLs file
#    - max_hops: how far to crawl from seed URLs
#    - skip_patterns: URL patterns to avoid

# 2. Add URLs to urls.txt (one per line)
echo "https://example.com/article" > urls.txt

# 3. Scrape the URLs
python3 scrape.py  # Uses scrape.yaml if present
# OR
./crawl.sh  # Uses default recursive settings

# 4. Clean the scraped content (removes boilerplate)
python3 clean.py  # Uses clean.yaml if present

# 5. Chunk the cleaned content
python3 chunk.py  # Uses chunk.yaml if present

# 6. Merge chunks to JSON (optional)
python3 merge.py chunks -o merged.json --pretty

# 7. Generate QA test set for retrieval evaluation (optional)
python3 generate_qa.py --extract-only  # Creates markdown files in qa/
```

**Note**: With `--recursive`, the scraper discovers and scrapes linked pages automatically. Use `max_hops` to limit crawling depth and `skip_patterns` to exclude unwanted URLs.

## File Structure

```
.
├── .env.example            # Example environment variables file
├── .env                    # Your API keys (create from .env.example, gitignored)
├── scrape.yaml             # Scraping configuration
├── clean.yaml              # Cleaning configuration
├── chunk.yaml              # Chunking configuration
├── generate_qa.yaml        # QA generation configuration
├── urls.txt                # List of URLs to scrape (seed URLs)
├── urls_to_scrape.txt      # Queue of URLs to scrape (recursive mode)
├── urls_scraped.txt        # Already scraped URLs (recursive mode)
├── scrape.py               # Web scraping script
├── clean.py                # Content cleaning script
├── chunk.py                # Markdown chunking script
├── merge.py                # Merge chunks to JSON
├── generate_qa.py          # Generate QA test questions
├── review_qa.py            # Review and curate questions
├── export_qa.py            # Export to test formats
├── crawl.sh                # Convenience script for scraping
├── clean_rules/            # Site-specific cleaning configurations
│   └── hackingwithswift.yaml
├── content_cleaner/        # Cleaning engine module
│   ├── __init__.py
│   ├── rules.py            # Cleaning rule implementations
│   ├── config.py           # Configuration loader
│   └── cleaner.py          # Main cleaning engine
├── scrapes/                # Scraped markdown files (raw)
├── cleaned/                # Cleaned markdown files (default)
├── chunks/                 # Chunked markdown files
├── qa/                     # QA pairs as markdown files
│   ├── <chunk_base>_001.md
│   ├── <chunk_base>_002.md
│   └── ...
├── merged.json             # Combined chunks in JSON format
└── test_set.json           # Legacy: final test set for evaluation
```

**Configuration Files**:
- `.env` - API keys and secrets (create from `.env.example`, already in `.gitignore`)
- `scrape.yaml` - Configure scraping (hop limits, skip patterns, output directories)
- `clean.yaml` - Configure cleaning (input/output dirs, auto-detection, rules)
- `chunk.yaml` - Configure chunking (chunk size, overlap, header levels)
- `generate_qa.yaml` - Configure QA generation (LLM provider, models, generation settings)

**State Files**: When using `--recursive`, the scraper maintains state in `urls_to_scrape.txt` (with hop counts stored as JSON) and `urls_scraped.txt`. Delete these files (or use `--ignore-scraping-state`) to start a fresh crawl.

