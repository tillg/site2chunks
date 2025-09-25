# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a web scraping and content processing pipeline that converts websites into markdown files for AI/ML processing. The workflow consists of three stages:

1. Web crawling using `crawler-to-md` tool
2. Adding frontmatter metadata to scraped markdown files
3. Chunking markdown content for AI processing

## Commands

### Web Crawling
```bash
./crawl.sh  # Runs crawler-to-md with urls from urls.txt
```

### Adding Frontmatter
```bash
python3 add_frontmatter.py  # Adds YAML frontmatter to all markdown files in output/
```

### Chunking Markdown (requires langchain-text-splitters)
```bash
python3 md_to_chunks.py <input_file> <output_dir> [--chunk-size 500] [--header-level 3]
```

### Python Environment
The project uses Python 3.13.7 in `.venv`. Activate with:
```bash
source .venv/bin/activate
```

## Architecture

### Data Pipeline
1. **Input**: URLs listed in `urls.txt`
2. **Crawling**: `crawler-to-md` generates JSON metadata + markdown files in `output/`
3. **Enhancement**: `add_frontmatter.py` extracts URLs from file paths and adds metadata
4. **Chunking**: `md_to_chunks.py` creates hierarchy-aware chunks with comprehensive metadata

### Output Structure
```
output/
└── [domain_path]/
    ├── [main_page].json         # Page metadata
    ├── [main_page].md           # Main content with frontmatter
    └── files/
        └── [subpages].md        # Individual pages with frontmatter
```

### Key Modules

**add_frontmatter.py**
- Adds `original_url` and `scrape_date` to markdown files
- Uses regex to extract URLs from file paths
- Processes directories recursively

**md_to_chunks.py**
- Hierarchy-aware splitting based on markdown headers
- Preserves code blocks during chunking
- Generates YAML frontmatter with chunk metadata
- Note: Requires `langchain-text-splitters` (not currently installed)

## Dependencies

Key packages in `.venv`:
- `crawler-to-md==0.5.0` - Web scraping
- `markdownify==1.2.0` - HTML to markdown
- `beautifulsoup4==4.13.4` - HTML parsing
- `mdformat==0.7.22` - Markdown formatting
- `ruamel.yaml==0.18.15` - YAML processing

Missing dependency:
- `langchain-text-splitters` - Required for md_to_chunks.py