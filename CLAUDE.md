# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a web scraping and content processing pipeline that converts websites into markdown files for AI/ML processing. The workflow consists of four stages:

1. Web scraping using custom scraper with recursive crawling
2. Content cleaning to remove boilerplate (navigation, footers, ads, etc.)
3. Chunking markdown content for AI processing
4. Merging chunks to JSON for app bundle integration

## Commands

### Web Scraping
```bash
# Using config file (recommended)
python3 scrape.py  # Reads settings from scrape.yaml

# Or with command-line args
./crawl.sh  # Convenience script with recursive crawling
python3 scrape.py urls.txt --recursive --max-hops 2
```

### Content Cleaning
```bash
# Using config file (recommended)
python3 clean.py  # Reads settings from clean.yaml

# Or with command-line args
python3 clean.py scrapes/ cleaned/ --auto-detect
python3 clean.py scrapes/ cleaned/ --config clean_rules/hackingwithswift.yaml
```

### Chunking Markdown
```bash
python3 chunk.py cleaned/ --out chunks
python3 chunk.py cleaned/ --out chunks --chunk-size 1500 --chunk-overlap 200
```

### Merging to JSON
```bash
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
   - Hierarchy-aware splitting based on headers
   - Preserves frontmatter and adds chunk metadata
   - Configurable chunk size and overlap

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
- Hierarchy-aware markdown splitting
- Preserves frontmatter, adds chunk metadata

**merge.py**
- Combines chunks into single JSON file

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
```

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
