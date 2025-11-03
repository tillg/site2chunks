#!/bin/bash
# Run complete pipeline for a config set

set -e  # Exit on any error

if [ -z "$1" ]; then
    echo "Usage: ./run_pipeline.sh CONFIG_SET_NAME"
    echo ""
    echo "Example: ./run_pipeline.sh hackingwithswift"
    echo ""
    echo "Available config sets:"
    if [ -d "config" ]; then
        for dir in config/*/; do
            if [ -f "${dir}config.yaml" ]; then
                basename "$dir"
            fi
        done
    else
        echo "  (none - config/ directory does not exist)"
    fi
    exit 1
fi

CONFIG_SET="$1"

# Check if config set exists
if [ ! -f "config/$CONFIG_SET/config.yaml" ]; then
    echo "Error: Configuration set '$CONFIG_SET' not found."
    echo "Expected: config/$CONFIG_SET/config.yaml"
    echo ""
    echo "Available config sets:"
    if [ -d "config" ]; then
        for dir in config/*/; do
            if [ -f "${dir}config.yaml" ]; then
                basename "$dir"
            fi
        done
    fi
    exit 1
fi

echo "=== Running pipeline for: $CONFIG_SET ==="
echo ""

echo "Step 1/4: Scraping..."
python3 scrape.py "$CONFIG_SET" || {
    echo "Error: Scraping failed"
    exit 1
}
echo ""

echo "Step 2/4: Cleaning..."
python3 clean.py "$CONFIG_SET" || {
    echo "Error: Cleaning failed"
    exit 1
}
echo ""

echo "Step 3/4: Chunking..."
python3 chunk.py "$CONFIG_SET" || {
    echo "Error: Chunking failed"
    exit 1
}
echo ""

echo "Step 4/4: Merging..."
python3 merge.py "$CONFIG_SET" || {
    echo "Error: Merging failed"
    exit 1
}
echo ""

echo "=== Pipeline complete! ==="
echo "Output: data/$CONFIG_SET/"
echo ""
echo "Files generated:"
echo "  - Scraped files: data/$CONFIG_SET/scrapes/"
echo "  - Cleaned files: data/$CONFIG_SET/cleaned/"
echo "  - Chunked files: data/$CONFIG_SET/chunks/"
echo "  - Merged JSON: data/$CONFIG_SET/merged.json"
