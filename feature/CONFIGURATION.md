# Configuration Sets Feature Specification

## Overview

This document specifies the **Configuration Sets** feature for the site2chunks pipeline. A configuration set is a named collection of all configurations required to scrape, clean, chunk, and merge content from a single website. This feature enables:

- **Organization**: Group all configs for one website in a single directory
- **Reusability**: Run complete pipelines with a single command
- **Maintainability**: Easy to add new sites without cluttering the root directory
- **Isolation**: Each site's data and configs are self-contained
- **Version Control**: Configurations can be committed to git, while data remains separate

## Motivation

### Current State Problems

**Current directory structure:**
```
site2chunks/
├── scrape.yaml           # Global scraping config
├── clean.yaml            # Global cleaning config
├── chunk.yaml            # Global chunking config
├── urls.txt              # Seed URLs for current site
├── clean_rules/
│   └── hackingwithswift.yaml  # Site-specific cleaning rules
├── scrapes/              # All scraped content mixed together
├── cleaned/              # All cleaned content mixed together
└── chunks/               # All chunks mixed together
```

**Problems:**
1. **Configuration scattered**: Site-specific configs (urls.txt, clean rules) separated from pipeline configs
2. **No site isolation**: All sites share same output directories (scrapes/, cleaned/, chunks/)
3. **Not scalable**: Adding new sites clutters root directory with more config files
4. **Manual coordination**: User must manually update multiple config files to switch sites
5. **Error-prone**: Easy to accidentally run hackingwithswift cleaning rules on different site's data
6. **Config/data mixing**: No clear separation between version-controlled configs and generated data

### Desired State

**New directory structure:**
```
site2chunks/
├── config/
│   ├── hackingwithswift/
│   │   ├── config.yaml         # ALL configuration (includes clean rules)
│   │   └── urls.txt            # Seed URLs
│   └── swiftui-docs/           # Example: another config set
│       ├── config.yaml
│       └── urls.txt
├── data/                       # Data directory (separate from config)
│   ├── hackingwithswift/
│   │   ├── scrapes/
│   │   ├── cleaned/
│   │   ├── chunks/
│   │   ├── merged.json
│   │   ├── urls_to_scrape.txt  # State files
│   │   └── urls_scraped.txt
│   └── swiftui-docs/
│       ├── scrapes/
│       ├── cleaned/
│       └── chunks/
├── scrape.yaml          # [Deprecated] Global config for backward compatibility
├── clean.yaml           # [Deprecated] Global config for backward compatibility
└── chunk.yaml           # [Deprecated] Global config for backward compatibility
```

**Benefits:**
1. ✅ **Self-contained**: All configs for a site in one directory
2. ✅ **Clear separation**: Config (version-controlled) vs Data (gitignored)
3. ✅ **Simple commands**: `python3 scrape.py hackingwithswift`
4. ✅ **Scalable**: Easy to add new sites without root directory clutter
5. ✅ **Safe**: No accidental cross-site contamination
6. ✅ **Git-friendly**: Config goes in repo, data stays local

---

## Configuration Set Structure

### Directory Layout

Each configuration set lives in `config/{config_set_name}/`:

```
config/{config_set_name}/
├── config.yaml          # REQUIRED: All pipeline configuration
└── urls.txt             # REQUIRED: Seed URLs for scraping
```

**Data is stored separately:**
```
data/{config_set_name}/
├── scrapes/             # Raw scraped files
├── cleaned/             # Cleaned markdown files
├── chunks/              # Chunked files
├── merged.json          # Merged JSON output
├── urls_to_scrape.txt   # Scraping state
└── urls_scraped.txt     # Scraping state
```

### Master Configuration File: `config.yaml`

The `config.yaml` file consolidates **all** pipeline configurations into a single file, including cleaning rules:

```yaml
# Configuration Set Metadata
config_set:
  name: hackingwithswift
  description: "Hacking with Swift - Swift and SwiftUI tutorials"
  version: 1.0
  created: 2025-01-15
  updated: 2025-01-15

# Data directory paths
# By default, data is stored in: data/{config_set_name}/
# All paths can be absolute or relative to project root
paths:
  data_dir: data/hackingwithswift           # Base data directory
  scrapes_dir: data/hackingwithswift/scrapes
  cleaned_dir: data/hackingwithswift/cleaned
  chunks_dir: data/hackingwithswift/chunks
  merged_file: data/hackingwithswift/merged.json
  urls_file: urls.txt                       # Relative to config set directory
  state_dir: data/hackingwithswift          # Directory for state files

# Scraping Configuration
scraping:
  recursive: true
  max_hops: 2
  skip_patterns:
    - "https://www.hackingwithswift.com/users/*"
    - "*/login"
    - "*/register"
    - "*/auth/*"
    - "*.zip"
    - "*.pdf"
    - "*.jpg"
    - "*.png"
    - "*.gif"
    - "*.svg"
    - "*.mp4"
    - "*.mp3"
  state_files:
    urls_to_scrape: urls_to_scrape.txt      # Stored in state_dir
    urls_scraped: urls_scraped.txt          # Stored in state_dir
  ignore_scraping_state: false

# Cleaning Configuration (includes all cleaning rules)
cleaning:
  pattern: "*.md"
  dry_run: false
  flush: true               # Delete output directory before cleaning

  # Site identifier (for logging/reference)
  site: hackingwithswift.com

  # Files to delete entirely (no content value)
  # These files will be deleted from the output directory
  delete_files:
    - hackingwithswift.com_unwrap.md
    - hackingwithswift.com_update-policy.md
    - hackingwithswift.com_videos.md
    - hackingwithswift.com.md
    - hackingwithswift.com_samples_friendface.json.md
    - hackingwithswift.com_articles_rss.md
    - hackingwithswift.com_playgrounds_feed.json.md
    - hackingwithswift.com_forums_*.md  # Wildcard support

  # Cleaning rules (same format as clean_rules/{domain}.yaml)
  rules:
    # Remove navigation menu
    - type: section_boundary
      description: "Navigation menu"
      start_marker: "- [Forums](/forums)"
      end_marker: "- [SUBSCRIBE](/plus)"
      inclusive: true

    # Remove promotional book banner
    - type: exact_match
      description: "Book promotional banner"
      pattern: "[NEW BOOK: **Code got you started. This gets you *paid*.** >>](/store/everything-but-the-code)"
      max_remove: -1

    # Remove sponsored content blocks
    - type: regex
      description: "Sponsored content blocks"
      pattern: '\*\*SPONSORED\*\*[^\n]*\n\n\[[^\]]+\]\([^\)]+\)\n'
      flags: [MULTILINE]

    # Remove footer sections
    - type: section_boundary
      description: "Footer content and social links"
      start_marker: "[Click here to visit the Hacking with Swift store >>](/store)"
      end_marker: "Link copied to your pasteboard."
      inclusive: true

    # ... (all other cleaning rules inline)

# Chunking Configuration
chunking:
  chunk_size: 1200
  chunk_overlap: 150
  strategy: "smart"         # "smart" or "legacy"
  max_header_level: 3       # For smart strategy (1-6)
  headers: "#,##,###,####,#####,######"  # For legacy strategy
  flush: true               # Delete output directory before chunking

# Merging Configuration
merging:
  pretty: true              # Pretty-print JSON output
  indent: 2                 # JSON indentation level
```

### Path Resolution Rules

**Priority order** (highest to lowest):
1. **Command-line arguments**: `--out`, `--input-dir`, etc.
2. **config.yaml paths section**: Paths specified in config set
3. **Global config files**: Legacy scrape.yaml, clean.yaml, chunk.yaml (deprecated)
4. **Default values**: `data/{config_set_name}/`

**Path interpretation:**
- **Relative paths** in `config.yaml` are resolved relative to the **project root** (site2chunks/)
- **Absolute paths** are used as-is
- **Special variables**:
  - `{config_set_name}`: Replaced with the config set name
  - `{data_dir}`: Replaced with the data_dir path

**Examples:**
```yaml
# Default: data stored in data/{config_set_name}/
paths:
  data_dir: data/hackingwithswift
  scrapes_dir: data/hackingwithswift/scrapes
  cleaned_dir: data/hackingwithswift/cleaned
  chunks_dir: data/hackingwithswift/chunks

# Using variable substitution
paths:
  data_dir: data/{config_set_name}
  scrapes_dir: {data_dir}/scrapes
  cleaned_dir: {data_dir}/cleaned
  chunks_dir: {data_dir}/chunks

# Absolute paths for external storage
paths:
  data_dir: /mnt/storage/scraping/hackingwithswift
  scrapes_dir: /mnt/storage/scraping/hackingwithswift/scrapes
```

### URLs File: `urls.txt`

Same format as current implementation:
```
https://www.hackingwithswift.com/100/swiftui/1
https://www.hackingwithswift.com/100/swiftui/2
https://www.hackingwithswift.com/100/swiftui/3
```

Stored in: `config/{config_set_name}/urls.txt`

---

## Command-Line Interface

### New Usage Pattern

Each script accepts a **config set name** as the first positional argument:

```bash
# Use configuration set
python3 scrape.py hackingwithswift
python3 clean.py hackingwithswift
python3 chunk.py hackingwithswift
python3 merge.py hackingwithswift

# Override config settings with flags
python3 scrape.py hackingwithswift --max-hops 3
python3 clean.py hackingwithswift --dry-run
python3 chunk.py hackingwithswift --chunk-size 1500
python3 merge.py hackingwithswift -o custom_output.json
```

### Backward Compatibility

Scripts still work without config set name (use global configs):

```bash
# Legacy usage (uses root-level scrape.yaml, clean.yaml, etc.)
python3 scrape.py
python3 clean.py
python3 chunk.py
```

### Config Set Discovery

When a config set name is provided:
1. Look for `config/{config_set_name}/config.yaml`
2. If not found, print error and exit:
   ```
   Error: Configuration set 'hackingwithswift' not found.
   Expected: config/hackingwithswift/config.yaml

   Available config sets:
     - hackingwithswift
     - swiftui-docs
   ```

### Full Command Syntax

#### scrape.py
```bash
python3 scrape.py [CONFIG_SET] [OPTIONS]

Arguments:
  CONFIG_SET            Optional: Name of configuration set in config/ directory

Options:
  --recursive           Enable recursive crawling (overrides config)
  --max-hops N          Maximum hops from seed URLs (overrides config)
  --ignore-scraping-state  Ignore state files and start fresh
  --out DIR             Output directory for scraped files (overrides config)
```

#### clean.py
```bash
python3 clean.py [CONFIG_SET] [OPTIONS]

Arguments:
  CONFIG_SET            Optional: Name of configuration set in config/ directory

Options:
  --input-dir DIR       Input directory (overrides config)
  --out DIR             Output directory (overrides config)
  --dry-run             Preview changes without writing
  --flush / --no-flush  Delete output directory before cleaning
```

#### chunk.py
```bash
python3 chunk.py [CONFIG_SET] [OPTIONS]

Arguments:
  CONFIG_SET            Optional: Name of configuration set in config/ directory

Options:
  --input-dir DIR       Input directory (overrides config)
  --out DIR             Output directory (overrides config)
  --chunk-size N        Target chunk size in characters
  --chunk-overlap N     Overlap between chunks
  --strategy STRATEGY   Chunking strategy: "smart" or "legacy"
  --max-header-level N  Max header level for smart strategy (1-6)
  --flush / --no-flush  Delete output directory before chunking
```

#### merge.py
```bash
python3 merge.py [CONFIG_SET] [OPTIONS]

Arguments:
  CONFIG_SET            Optional: Name of configuration set in config/ directory

Options:
  --input-dir DIR       Input directory (overrides config)
  -o, --output FILE     Output JSON file (overrides config)
  --pretty              Pretty-print JSON
  --indent N            JSON indentation level
```

---

## Implementation Plan

### Phase 1: Core Infrastructure

**1.1 Create configuration loader module** (`config_loader.py`)

**File:** `config_loader.py`

```python
"""
Configuration set loader and validator.
Handles loading config.yaml files and resolving paths.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml

class ConfigSetNotFoundError(Exception):
    """Raised when a configuration set cannot be found."""
    pass

class ConfigSet:
    """Represents a loaded configuration set."""

    def __init__(self, name: str, config_dir: Path, project_root: Path):
        self.name = name
        self.config_dir = config_dir
        self.project_root = project_root
        self.config_file = config_dir / "config.yaml"
        self.data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load and validate config.yaml."""
        if not self.config_file.exists():
            raise ConfigSetNotFoundError(
                f"Configuration file not found: {self.config_file}"
            )

        with open(self.config_file) as f:
            config = yaml.safe_load(f)

        # Validate required sections
        self._validate_config(config)
        return config

    def _validate_config(self, config: Dict[str, Any]):
        """Validate configuration structure."""
        required_sections = ["config_set", "scraping", "cleaning", "chunking"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section '{section}' in {self.config_file}")

    def _substitute_variables(self, path: str) -> str:
        """Substitute variables in path strings."""
        # Replace {config_set_name}
        path = path.replace("{config_set_name}", self.name)

        # Replace {data_dir} if it appears
        if "{data_dir}" in path:
            data_dir = self.data.get("paths", {}).get("data_dir", f"data/{self.name}")
            data_dir = data_dir.replace("{config_set_name}", self.name)
            path = path.replace("{data_dir}", data_dir)

        return path

    def resolve_path(self, path: str, relative_to_config: bool = False) -> Path:
        """
        Resolve a path from config.yaml.

        - Absolute paths are returned as-is
        - Relative paths are resolved relative to project root (unless relative_to_config=True)
        - Paths can use {config_set_name} and {data_dir} variables

        Args:
            path: Path string from config
            relative_to_config: If True, resolve relative paths from config dir (for urls.txt)
        """
        # Substitute variables
        path = self._substitute_variables(path)

        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj
        else:
            base_dir = self.config_dir if relative_to_config else self.project_root
            return (base_dir / path_obj).resolve()

    def get_data_dir(self) -> Path:
        """Get the data directory for this config set."""
        data_dir = self.data.get("paths", {}).get("data_dir", f"data/{self.name}")
        return self.resolve_path(data_dir)

    def get_state_dir(self) -> Path:
        """Get the state directory for this config set."""
        state_dir = self.data.get("paths", {}).get("state_dir")
        if state_dir:
            return self.resolve_path(state_dir)
        # Default to data_dir
        return self.get_data_dir()

    def get_urls_file(self) -> Path:
        """Get the URLs file path."""
        urls_file = self.data.get("paths", {}).get("urls_file", "urls.txt")
        # urls.txt is relative to config directory
        return self.resolve_path(urls_file, relative_to_config=True)

    def get_scrapes_dir(self) -> Path:
        """Get the scrapes directory path."""
        scrapes = self.data.get("paths", {}).get("scrapes_dir", "{data_dir}/scrapes")
        return self.resolve_path(scrapes)

    def get_cleaned_dir(self) -> Path:
        """Get the cleaned directory path."""
        cleaned = self.data.get("paths", {}).get("cleaned_dir", "{data_dir}/cleaned")
        return self.resolve_path(cleaned)

    def get_chunks_dir(self) -> Path:
        """Get the chunks directory path."""
        chunks = self.data.get("paths", {}).get("chunks_dir", "{data_dir}/chunks")
        return self.resolve_path(chunks)

    def get_merged_file(self) -> Path:
        """Get the merged JSON file path."""
        merged = self.data.get("paths", {}).get("merged_file", "{data_dir}/merged.json")
        return self.resolve_path(merged)

    def get_scraping_config(self) -> Dict[str, Any]:
        """Get scraping configuration section."""
        return self.data.get("scraping", {})

    def get_cleaning_config(self) -> Dict[str, Any]:
        """Get cleaning configuration section (includes rules)."""
        return self.data.get("cleaning", {})

    def get_chunking_config(self) -> Dict[str, Any]:
        """Get chunking configuration section."""
        return self.data.get("chunking", {})

    def get_merging_config(self) -> Dict[str, Any]:
        """Get merging configuration section."""
        return self.data.get("merging", {})


def load_config_set(name: str, project_root: Path = Path.cwd(),
                    config_base_dir: str = "config") -> ConfigSet:
    """
    Load a configuration set by name.

    Args:
        name: Name of the config set (e.g., "hackingwithswift")
        project_root: Project root directory (default: current working directory)
        config_base_dir: Base directory containing config sets (default: "config")

    Returns:
        ConfigSet object

    Raises:
        ConfigSetNotFoundError: If config set doesn't exist
    """
    config_dir = project_root / config_base_dir / name

    if not config_dir.exists():
        # List available config sets for helpful error message
        available = list_config_sets(project_root, config_base_dir)
        available_str = "\n  - ".join(available) if available else "  (none)"

        raise ConfigSetNotFoundError(
            f"Configuration set '{name}' not found.\n"
            f"Expected: {config_dir / 'config.yaml'}\n\n"
            f"Available config sets:\n  - {available_str}"
        )

    return ConfigSet(name, config_dir, project_root)


def list_config_sets(project_root: Path = Path.cwd(),
                     config_base_dir: str = "config") -> list[str]:
    """
    List all available configuration sets.

    Args:
        project_root: Project root directory
        config_base_dir: Base directory containing config sets

    Returns:
        List of config set names
    """
    base_dir = project_root / config_base_dir

    if not base_dir.exists():
        return []

    config_sets = []
    for item in base_dir.iterdir():
        if item.is_dir() and (item / "config.yaml").exists():
            config_sets.append(item.name)

    return sorted(config_sets)
```

**1.2 Update argument parsing** in all scripts

Add optional positional argument for config set name:
- If provided: Load config set and use its values as defaults
- If not provided: Use legacy global config files (backward compatible)
- Command-line flags always override config values

**1.3 Create directory structure**

```bash
mkdir -p config data
```

### Phase 2: Update Content Cleaner Module

**2.1 Update content_cleaner/config.py**

Modify the config loader to accept cleaning configuration directly from a dict (from config.yaml) instead of loading from a separate file:

```python
def load_cleaning_config_from_dict(config_dict: Dict[str, Any]) -> CleaningConfig:
    """
    Load cleaning configuration from a dictionary (from config.yaml).

    Args:
        config_dict: Dictionary containing cleaning configuration

    Returns:
        CleaningConfig object
    """
    # Extract cleaning rules
    rules = []
    for rule_dict in config_dict.get("rules", []):
        rule = create_rule_from_dict(rule_dict)
        rules.append(rule)

    return CleaningConfig(
        site=config_dict.get("site", "unknown"),
        delete_files=config_dict.get("delete_files", []),
        rules=rules
    )
```

### Phase 3: Script Integration

**3.1 Update scrape.py**

Changes:
1. Add optional `config_set` positional argument
2. If provided, load `ConfigSet` and use its values
3. Command-line flags override config values
4. State files stored in data directory (not config directory)
5. Maintain backward compatibility (works without config set)

**Key changes:**
```python
# At top of file
from config_loader import load_config_set, list_config_sets, ConfigSetNotFoundError
from pathlib import Path

# In argument parser
parser.add_argument(
    "config_set",
    nargs="?",
    default=None,
    help="Name of configuration set in config/ directory"
)

# After parsing arguments
config_set = None
if args.config_set:
    try:
        config_set = load_config_set(args.config_set)
        print(f"Loaded configuration set: {args.config_set}")
    except ConfigSetNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

# Use config set values as defaults
if config_set:
    urls_file = args.urls_file or config_set.get_urls_file()
    output_dir = args.output_dir or config_set.get_scrapes_dir()
    scraping_config = config_set.get_scraping_config()
    state_dir = config_set.get_state_dir()

    # Apply scraping_config values...
    recursive = args.recursive if args.recursive is not None else scraping_config.get("recursive", False)
    max_hops = args.max_hops if args.max_hops is not None else scraping_config.get("max_hops", 0)
    # ... etc
else:
    # Legacy: load from scrape.yaml or use defaults
    ...
```

**3.2 Update clean.py**

Similar changes to scrape.py:
1. Load config set if provided
2. Extract cleaning rules from config.yaml (not separate file)
3. Use config set's directories
4. Maintain backward compatibility

**Key changes:**
```python
from config_loader import load_config_set, ConfigSetNotFoundError
from content_cleaner.config import load_cleaning_config_from_dict

# Load config set
config_set = load_config_set(args.config_set)

# Get cleaning configuration (includes rules)
cleaning_config_dict = config_set.get_cleaning_config()

# Load cleaning rules from dict
cleaning_config = load_cleaning_config_from_dict(cleaning_config_dict)

# Get directories
input_dir = args.input_dir or config_set.get_scrapes_dir()
output_dir = args.output_dir or config_set.get_cleaned_dir()
```

**3.3 Update chunk.py**

Similar changes:
1. Load config set if provided
2. Use config set's chunking settings and directories
3. Maintain backward compatibility

**3.4 Update merge.py**

Similar changes:
1. Load config set if provided
2. Use config set's merging settings
3. Maintain backward compatibility

### Phase 4: Create hackingwithswift Config Set

**4.1 Create directory structure**

```bash
mkdir -p config/hackingwithswift
mkdir -p data/hackingwithswift/{scrapes,cleaned,chunks}
```

**4.2 Create config.yaml**

Consolidate all existing configs into `config/hackingwithswift/config.yaml`:
- Copy values from `scrape.yaml`
- Copy values from `clean.yaml`
- Copy values from `chunk.yaml`
- Copy all cleaning rules from `clean_rules/hackingwithswift.yaml` into `cleaning.rules` section

**4.3 Move URLs file**

```bash
cp urls.txt config/hackingwithswift/urls.txt
```

**4.4 Update .gitignore**

Ensure data directory is ignored:
```
# Data directories (generated content)
data/
scrapes/
cleaned/
chunks/
*.json

# State files
urls_to_scrape.txt
urls_scraped.txt
```

Ensure config directory is tracked:
```
# Keep config files
!config/
!config/**/*.yaml
!config/**/urls.txt
```

**4.5 Test the migration**

```bash
# Test scraping
python3 scrape.py hackingwithswift

# Test cleaning
python3 clean.py hackingwithswift --dry-run

# Test chunking
python3 chunk.py hackingwithswift

# Test merging
python3 merge.py hackingwithswift
```

### Phase 5: Documentation & Tooling

**5.1 Update CLAUDE.md**

- Document configuration sets feature
- Update command examples
- Add migration guide for existing setups
- Document new directory structure

**5.2 Create convenience scripts**

Create `run_pipeline.sh` for running full pipeline:

```bash
#!/bin/bash
# Run complete pipeline for a config set

if [ -z "$1" ]; then
    echo "Usage: ./run_pipeline.sh CONFIG_SET_NAME"
    echo ""
    echo "Example: ./run_pipeline.sh hackingwithswift"
    exit 1
fi

CONFIG_SET="$1"

echo "=== Running pipeline for: $CONFIG_SET ==="
echo ""

echo "Step 1: Scraping..."
python3 scrape.py "$CONFIG_SET" || exit 1
echo ""

echo "Step 2: Cleaning..."
python3 clean.py "$CONFIG_SET" || exit 1
echo ""

echo "Step 3: Chunking..."
python3 chunk.py "$CONFIG_SET" || exit 1
echo ""

echo "Step 4: Merging..."
python3 merge.py "$CONFIG_SET" || exit 1
echo ""

echo "=== Pipeline complete! ==="
echo "Output: data/$CONFIG_SET/"
```

**5.3 Create config set management tool**

Create `config_tool.py` for managing config sets:

```bash
# List all config sets
python3 config_tool.py list

# Create new config set from template
python3 config_tool.py create mysite

# Validate config set
python3 config_tool.py validate hackingwithswift

# Show config set details
python3 config_tool.py info hackingwithswift
```

### Phase 6: Testing & Validation

**6.1 Unit tests**

Create `tests/test_config_loader.py`:
- Test path resolution (relative, absolute, with variable substitution)
- Test config validation
- Test error handling (missing files, invalid YAML)
- Test config set discovery
- Test variable substitution ({config_set_name}, {data_dir})

**6.2 Integration tests**

Create `tests/test_integration.py`:
- Test full pipeline with config set
- Test backward compatibility (without config set)
- Test command-line overrides
- Test that data is properly separated from config

**6.3 Manual testing**

Test scenarios:
1. Run pipeline with config set
2. Run pipeline without config set (legacy mode)
3. Override config values with CLI flags
4. Test with non-existent config set (error handling)
5. Test with multiple config sets
6. Verify data directories are created correctly
7. Verify state files end up in data directory

---

## Migration Guide

### For Existing Projects

**Option A: Keep using global configs (no migration needed)**

Continue using root-level `scrape.yaml`, `clean.yaml`, `chunk.yaml`:
```bash
python3 scrape.py
python3 clean.py
python3 chunk.py
```

**Option B: Migrate to config sets**

**Step 1: Create config set directory**
```bash
mkdir -p config/mysite
mkdir -p data/mysite/{scrapes,cleaned,chunks}
```

**Step 2: Create config.yaml**

Create `config/mysite/config.yaml` with all configuration:

```yaml
config_set:
  name: mysite
  description: "My Website"
  version: 1.0

paths:
  data_dir: data/mysite
  scrapes_dir: data/mysite/scrapes
  cleaned_dir: data/mysite/cleaned
  chunks_dir: data/mysite/chunks
  merged_file: data/mysite/merged.json
  urls_file: urls.txt
  state_dir: data/mysite

scraping:
  # Copy from scrape.yaml
  recursive: true
  max_hops: 2
  skip_patterns: [...]
  state_files:
    urls_to_scrape: urls_to_scrape.txt
    urls_scraped: urls_scraped.txt

cleaning:
  pattern: "*.md"
  flush: true
  site: mysite.com
  delete_files: []
  rules:
    # Copy all rules from clean_rules/mysite.yaml here
    - type: section_boundary
      description: "..."
      start_marker: "..."
      end_marker: "..."

chunking:
  # Copy from chunk.yaml
  chunk_size: 1200
  chunk_overlap: 150
  strategy: "smart"
  max_header_level: 3
  flush: true

merging:
  pretty: true
  indent: 2
```

**Step 3: Move URLs file**
```bash
cp urls.txt config/mysite/urls.txt
```

**Step 4: Update .gitignore**
```bash
# Add to .gitignore
data/
```

**Step 5: Use config set**
```bash
python3 scrape.py mysite
python3 clean.py mysite
python3 chunk.py mysite
python3 merge.py mysite
```

### For New Projects

**Step 1: Create config set**
```bash
mkdir -p config/newsite
mkdir -p data/newsite/{scrapes,cleaned,chunks}
```

**Step 2: Create config.yaml**

Use template from Appendix A or copy from existing config set.

**Step 3: Add URLs**
```bash
echo "https://example.com" > config/newsite/urls.txt
```

**Step 4: Run pipeline**
```bash
./run_pipeline.sh newsite
```

---

## Examples

### Example 1: hackingwithswift Config Set

**Directory structure:**
```
config/hackingwithswift/
├── config.yaml
└── urls.txt

data/hackingwithswift/
├── scrapes/
├── cleaned/
├── chunks/
├── merged.json
├── urls_to_scrape.txt
└── urls_scraped.txt
```

**config.yaml (abbreviated):**
```yaml
config_set:
  name: hackingwithswift
  description: "Hacking with Swift - Swift and SwiftUI tutorials"
  version: 1.0

paths:
  data_dir: data/hackingwithswift
  scrapes_dir: data/hackingwithswift/scrapes
  cleaned_dir: data/hackingwithswift/cleaned
  chunks_dir: data/hackingwithswift/chunks
  merged_file: data/hackingwithswift/merged.json
  urls_file: urls.txt
  state_dir: data/hackingwithswift

scraping:
  recursive: true
  max_hops: 2
  skip_patterns:
    - "https://www.hackingwithswift.com/users/*"
    - "*/login"
    - "*.pdf"
  state_files:
    urls_to_scrape: urls_to_scrape.txt
    urls_scraped: urls_scraped.txt

cleaning:
  pattern: "*.md"
  flush: true
  site: hackingwithswift.com
  delete_files:
    - hackingwithswift.com_unwrap.md
    - hackingwithswift.com_videos.md
  rules:
    - type: section_boundary
      description: "Navigation menu"
      start_marker: "- [Forums](/forums)"
      end_marker: "- [SUBSCRIBE](/plus)"
      inclusive: true
    # ... (all other rules inline)

chunking:
  chunk_size: 1200
  chunk_overlap: 150
  strategy: "smart"
  max_header_level: 3
  flush: true

merging:
  pretty: true
  indent: 2
```

**Usage:**
```bash
# Run complete pipeline
./run_pipeline.sh hackingwithswift

# Or run steps individually
python3 scrape.py hackingwithswift
python3 clean.py hackingwithswift
python3 chunk.py hackingwithswift
python3 merge.py hackingwithswift
```

### Example 2: Using Variable Substitution

**config.yaml:**
```yaml
config_set:
  name: swiftui-docs

paths:
  data_dir: data/{config_set_name}          # → data/swiftui-docs
  scrapes_dir: {data_dir}/scrapes           # → data/swiftui-docs/scrapes
  cleaned_dir: {data_dir}/cleaned           # → data/swiftui-docs/cleaned
  chunks_dir: {data_dir}/chunks             # → data/swiftui-docs/chunks
  merged_file: {data_dir}/merged.json       # → data/swiftui-docs/merged.json
  state_dir: {data_dir}                     # → data/swiftui-docs

# ... rest of config
```

### Example 3: Using Absolute Paths

For projects that need data stored elsewhere:

**config.yaml:**
```yaml
config_set:
  name: enterprise-docs

paths:
  data_dir: /mnt/storage/scraping/enterprise-docs
  scrapes_dir: /mnt/storage/scraping/enterprise-docs/scrapes
  cleaned_dir: /mnt/storage/scraping/enterprise-docs/cleaned
  chunks_dir: /mnt/storage/scraping/enterprise-docs/chunks
  merged_file: /mnt/storage/scraping/enterprise-docs/output/merged.json
  state_dir: /mnt/storage/scraping/enterprise-docs

# ... rest of config
```

---

## Design Decisions

### Configuration vs Data Separation

**Decision:** Configuration and data must be strictly separated.

**Rationale:**
- **Version Control**: Configurations should be committed to git, data should not
- **Portability**: Config sets can be shared/distributed without including large data files
- **Git-friendly**: Clean separation makes .gitignore rules simple and predictable
- **Security**: Prevents accidentally committing scraped content

**Implementation:**
- Config stored in: `config/{config_set_name}/`
- Data stored in: `data/{config_set_name}/`
- State files stored with data (not config)

### All Configuration in One File

**Decision:** All pipeline configuration (including cleaning rules) goes in `config.yaml`.

**Rationale:**
- **Single source of truth**: One file contains everything for a config set
- **Easier to understand**: No need to hunt across multiple files
- **Simpler management**: Copy/edit one file instead of multiple
- **Atomic changes**: Configuration changes happen in one file
- **Better diffs**: Git diffs show all related changes together

**Trade-off:** Larger config file, but YAML structure keeps it organized.

### State Files Location

**Decision:** State files (`urls_to_scrape.txt`, `urls_scraped.txt`) stored in data directory.

**Rationale:**
- **They are generated data**, not configuration
- **Should not be version controlled**
- **Should be cleaned with data**, not preserved with config
- **Consistent with config/data separation principle**

### Path Resolution Relative to Project Root

**Decision:** Relative paths in config.yaml are resolved relative to project root (not config directory).

**Rationale:**
- **Predictable**: Paths work the same from any working directory
- **Consistent with data directory location** (data/ at root)
- **Simpler mental model**: All paths start from project root
- **Exception**: `urls_file` is relative to config directory (it's part of config)

### Variable Substitution

**Decision:** Support `{config_set_name}` and `{data_dir}` variable substitution in paths.

**Rationale:**
- **DRY principle**: Don't repeat config set name everywhere
- **Template-friendly**: Easy to create config template
- **Flexible**: Change data_dir location without updating all paths

**Not implemented (for now):**
- Environment variable substitution (`${ENV_VAR}`) - not needed initially
- Config inheritance - adds complexity, defer until requested

---

## Implementation Checklist

### Core Infrastructure
- [ ] Create `config_loader.py` module
  - [ ] `ConfigSet` class with path resolution
  - [ ] `load_config_set()` function
  - [ ] `list_config_sets()` function
  - [ ] Variable substitution support
  - [ ] Error handling and validation
- [ ] Create `config/` directory
- [ ] Create `data/` directory
- [ ] Update `.gitignore` for config/data separation

### Content Cleaner Module Updates
- [ ] Add `load_cleaning_config_from_dict()` to `content_cleaner/config.py`
- [ ] Test loading cleaning rules from config.yaml dict
- [ ] Maintain backward compatibility with separate clean_rules files

### Script Updates
- [ ] Update `scrape.py`
  - [ ] Add config_set positional argument
  - [ ] Integrate config loader
  - [ ] Use state_dir for state files
  - [ ] Test backward compatibility
- [ ] Update `clean.py`
  - [ ] Add config_set positional argument
  - [ ] Load cleaning rules from config.yaml
  - [ ] Integrate config loader
  - [ ] Test backward compatibility
- [ ] Update `chunk.py`
  - [ ] Add config_set positional argument
  - [ ] Integrate config loader
  - [ ] Test backward compatibility
- [ ] Update `merge.py`
  - [ ] Add config_set positional argument
  - [ ] Integrate config loader
  - [ ] Test backward compatibility

### hackingwithswift Migration
- [ ] Create `config/hackingwithswift/` directory
- [ ] Create `config/hackingwithswift/config.yaml`
  - [ ] Copy scraping config from scrape.yaml
  - [ ] Copy cleaning config from clean.yaml
  - [ ] Copy chunking config from chunk.yaml
  - [ ] Copy all cleaning rules from clean_rules/hackingwithswift.yaml
- [ ] Copy `urls.txt` to config set
- [ ] Create `data/hackingwithswift/` directories
- [ ] Update `.gitignore`
- [ ] Test full pipeline with config set

### Tooling & Documentation
- [ ] Create `run_pipeline.sh` script
- [ ] Create `config_tool.py` utility
  - [ ] list command
  - [ ] create command
  - [ ] validate command
  - [ ] info command
- [ ] Update `CLAUDE.md`
- [ ] Update `README.md` (if exists)
- [ ] Create migration guide

### Testing
- [ ] Write unit tests for `config_loader.py`
  - [ ] Test path resolution
  - [ ] Test variable substitution
  - [ ] Test config validation
  - [ ] Test error handling
- [ ] Write unit tests for `content_cleaner/config.py`
  - [ ] Test loading rules from dict
- [ ] Write integration tests
  - [ ] Test full pipeline with config set
  - [ ] Test backward compatibility
  - [ ] Test command-line overrides
  - [ ] Test config/data separation
- [ ] Manual testing with hackingwithswift

### Optional Enhancements
- [ ] Add config validation command
- [ ] Add config set initialization wizard
- [ ] Add support for config set templates
- [ ] Add --list-config-sets flag to all scripts
- [ ] Add dry-run mode for config set operations

---

## Success Criteria

The Configuration Sets feature is successful when:

1. ✅ **Users can run complete pipelines with a single command**
   - `python3 scrape.py hackingwithswift` works end-to-end

2. ✅ **Config sets are self-contained**
   - All configs for a site in one directory
   - Easy to version control, share, or duplicate

3. ✅ **Config and data are clearly separated**
   - Config in `config/`, data in `data/`
   - Only config is version controlled
   - No confusion about what goes where

4. ✅ **Single config file contains everything**
   - No need to maintain separate clean_rules.yaml
   - All pipeline settings in one place

5. ✅ **Backward compatibility maintained**
   - Existing scripts work without modifications
   - Global config files still functional

6. ✅ **Easy to add new sites**
   - Create new config set directory
   - Copy/customize config.yaml
   - Run pipeline

7. ✅ **Data isolation works correctly**
   - Each config set has isolated data directories
   - No cross-contamination between sites

8. ✅ **Documentation is clear**
   - Migration guide helps existing users
   - Examples show common patterns
   - Error messages are helpful

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Core Infrastructure | config_loader.py, directory structure | 4-6 hours |
| Phase 2: Content Cleaner Updates | Update config.py for dict loading | 2-3 hours |
| Phase 3: Script Integration | Update 4 scripts with config set support | 6-8 hours |
| Phase 4: hackingwithswift Migration | Create config set, consolidate configs | 3-4 hours |
| Phase 5: Documentation & Tooling | Update docs, create helper scripts | 3-4 hours |
| Phase 6: Testing & Validation | Unit tests, integration tests, manual testing | 4-6 hours |
| **Total** | | **22-31 hours** |

---

## Appendix A: Config Set Template

**Template for new config sets** (`config/template/config.yaml`):

```yaml
# Configuration Set Metadata
config_set:
  name: template
  description: "Configuration set template"
  version: 1.0
  created: 2025-01-15
  updated: 2025-01-15

# Data directory paths
# Relative paths are resolved relative to project root
# Use {config_set_name} and {data_dir} for variable substitution
paths:
  data_dir: data/{config_set_name}
  scrapes_dir: {data_dir}/scrapes
  cleaned_dir: {data_dir}/cleaned
  chunks_dir: {data_dir}/chunks
  merged_file: {data_dir}/merged.json
  urls_file: urls.txt               # Relative to config directory
  state_dir: {data_dir}

# Scraping Configuration
scraping:
  recursive: true
  max_hops: 2
  skip_patterns:
    - "*/login"
    - "*/register"
    - "*/auth/*"
    - "*.zip"
    - "*.pdf"
    - "*.jpg"
    - "*.png"
    - "*.gif"
  state_files:
    urls_to_scrape: urls_to_scrape.txt
    urls_scraped: urls_scraped.txt
  ignore_scraping_state: false

# Cleaning Configuration
cleaning:
  pattern: "*.md"
  dry_run: false
  flush: true
  site: example.com

  # Files to delete entirely
  delete_files: []

  # Cleaning rules
  rules:
    - type: section_boundary
      description: "Example: Remove footer"
      start_marker: "## Footer"
      end_marker: null
      inclusive: true

# Chunking Configuration
chunking:
  chunk_size: 1200
  chunk_overlap: 150
  strategy: "smart"
  max_header_level: 3
  headers: "#,##,###,####,#####,######"
  flush: true

# Merging Configuration
merging:
  pretty: true
  indent: 2
```

---

## Appendix B: Error Messages

**Config set not found:**
```
Error: Configuration set 'mysite' not found.
Expected: config/mysite/config.yaml

Available config sets:
  - hackingwithswift
  - swiftui-docs

To create a new config set:
  mkdir -p config/mysite
  cp config/template/config.yaml config/mysite/config.yaml
  echo "https://example.com" > config/mysite/urls.txt
```

**Invalid config.yaml:**
```
Error: Invalid configuration in config/mysite/config.yaml
Missing required section: 'scraping'

Please check your config.yaml file against the template:
  config/template/config.yaml
```

**Missing required files:**
```
Error: Configuration set 'mysite' is incomplete.
Missing required file: config/mysite/urls.txt

Required files:
  ✓ config.yaml
  ✗ urls.txt (MISSING)
```

---

## Appendix C: Future Enhancements

### 1. Config Set Wizard

Interactive wizard for creating new config sets:
```bash
$ python3 config_tool.py init

Configuration Set Wizard
========================

Config set name: mysite
Description: My website documentation
Seed URLs (one per line, blank line to finish):
> https://example.com/docs
>
Enable recursive crawling? [Y/n]: Y
Max hops [2]: 3
Enable smart chunking? [Y/n]: Y

Creating config set 'mysite'...
✓ Created config/mysite/config.yaml
✓ Created config/mysite/urls.txt
✓ Created data/mysite/ directories

Next steps:
1. Edit config/mysite/config.yaml to add cleaning rules
2. Run: python3 scrape.py mysite
```

### 2. Config Set Export/Import

Export config set as shareable archive:
```bash
$ python3 config_tool.py export hackingwithswift

Creating archive: hackingwithswift-config-2025-01-15.tar.gz
✓ Including config.yaml
✓ Including urls.txt
✗ Excluding data/ (config only)

Archive created: hackingwithswift-config-2025-01-15.tar.gz
```

Import config set from archive:
```bash
$ python3 config_tool.py import hackingwithswift-config-2025-01-15.tar.gz

Extracting config set 'hackingwithswift'...
✓ Extracted to config/hackingwithswift/

Config set imported successfully!
Run: python3 scrape.py hackingwithswift
```

### 3. Config Set Linting

Validate and lint config sets:
```bash
$ python3 config_tool.py lint hackingwithswift

Linting config set 'hackingwithswift'...
✓ config.yaml is valid
✓ urls.txt exists and is readable
✓ All required sections present
✓ All paths are resolvable
✓ Cleaning rules syntax is valid
⚠ Warning: data/hackingwithswift/scrapes/ does not exist (will be created)
⚠ Warning: 3 skip_patterns may be redundant

Overall: PASS (2 warnings)
```

### 4. Pipeline Orchestration

Run full pipeline with progress reporting:
```bash
$ python3 run_pipeline.py hackingwithswift

Pipeline: hackingwithswift
==========================

[1/4] Scraping ⠋
  ✓ Loaded 100 seed URLs
  ⠦ Scraped 45/100 pages (45%)
  ⠦ Found 123 new URLs via recursive crawling
  ...
  ✓ Scraped 268 pages (12 MB)

[2/4] Cleaning ⠋
  ✓ Loaded clean rules: 48 rules
  ⠦ Cleaned 134/268 files (50%)
  ...
  ✓ Cleaned 268 files (8 MB, 34% reduction)

[3/4] Chunking ⠋
  ✓ Using smart chunking strategy
  ⠦ Chunked 134/268 files (50%)
  ...
  ✓ Created 1,234 chunks (avg 1,150 chars/chunk)

[4/4] Merging ⠋
  ✓ Merged 1,234 chunks → merged.json (5 MB)

Pipeline complete! ✨
  Total time: 8m 32s
  Output: data/hackingwithswift/
```

---

**Document Version:** 1.1
**Last Updated:** 2025-01-15
**Author:** site2chunks development team
