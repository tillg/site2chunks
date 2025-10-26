#!/usr/bin/env python3
"""
Content Cleaning CLI

Clean scraped markdown files by removing non-valuable content like navigation menus,
footers, sponsored content, and other boilerplate.

Usage:
    python3 clean.py [input] [output] [options]

Examples:
    # Using config file (recommended): reads settings from clean.yaml
    python3 clean.py

    # Clean a single file
    python3 clean.py scrapes/file.md cleaned/file.md --config clean_rules/hackingwithswift.yaml

    # Clean entire directory
    python3 clean.py scrapes/ cleaned/ --config clean_rules/hackingwithswift.yaml

    # Dry run to preview changes
    python3 clean.py scrapes/ --dry-run --config clean_rules/hackingwithswift.yaml

    # Auto-detect config from file's domain
    python3 clean.py scrapes/ cleaned/ --auto-detect
"""

import argparse
import sys
import yaml
from pathlib import Path
from content_cleaner import ContentCleaner, CleaningConfig


def load_config_file(config_path='clean.yaml'):
    """Load cleaning configuration from YAML file."""
    if not Path(config_path).exists():
        return {}

    with open(config_path, 'r') as f:
        return yaml.safe_load(f) or {}


def main():
    parser = argparse.ArgumentParser(
        description='Clean scraped markdown files by removing non-valuable content.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'input',
        nargs='?',
        help='Input file or directory containing markdown files'
    )

    parser.add_argument(
        'output',
        nargs='?',
        help='Output file or directory (optional for dry-run, required otherwise)'
    )

    parser.add_argument(
        '-c', '--config',
        help='Path to YAML configuration file with cleaning rules'
    )

    parser.add_argument(
        '-a', '--auto-detect',
        action='store_true',
        help='Auto-detect configuration from file frontmatter domain'
    )

    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )

    parser.add_argument(
        '-p', '--pattern',
        default='*.md',
        help='File pattern to match (default: *.md)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )

    parser.add_argument(
        '--preview',
        action='store_true',
        help='Show detailed diff preview for first file'
    )

    parser.add_argument(
        '--flush',
        action='store_true',
        help='Delete output directory before cleaning (flush-and-fill)'
    )

    parser.add_argument(
        '--no-flush',
        action='store_true',
        help='Do not delete output directory (overrides config file)'
    )

    args = parser.parse_args()

    # Load config file if it exists
    file_config = load_config_file('clean.yaml')

    # Get input/output from args or config
    input_arg = args.input or file_config.get('input_dir')
    output_arg = args.output or file_config.get('output_dir')
    pattern = args.pattern or file_config.get('pattern', '*.md')
    dry_run = args.dry_run or file_config.get('dry_run', False)
    auto_detect = args.auto_detect or file_config.get('auto_detect', False)
    config_file = args.config or file_config.get('config_file')
    rules_dir = file_config.get('rules_dir', 'clean_rules')

    # Determine flush behavior (CLI args override config)
    if args.no_flush:
        flush = False
    elif args.flush:
        flush = True
    else:
        flush = file_config.get('flush', False)

    # Validate arguments
    if not input_arg:
        print("Error: Input path must be specified (via argument or clean.yaml)")
        sys.exit(1)

    input_path = Path(input_arg)
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_arg}")
        sys.exit(1)

    if not dry_run and not args.preview and not output_arg:
        print("Error: Output path is required unless using --dry-run or --preview")
        sys.exit(1)

    # Load configuration
    config = None

    if auto_detect:
        print("Auto-detecting configuration from file...")
        try:
            # Get first file to detect domain
            if input_path.is_file():
                sample_file = str(input_path)
            else:
                files = list(input_path.glob(pattern))
                if not files:
                    print(f"Error: No files matching '{pattern}' found in {input_arg}")
                    sys.exit(1)
                sample_file = str(files[0])

            domain = CleaningConfig.extract_domain_from_file(sample_file)
            if not domain:
                print("Error: Could not extract domain from file frontmatter")
                sys.exit(1)

            print(f"Detected domain: {domain}")
            config_path = CleaningConfig.find_config_for_domain(domain, rules_dir)
            print(f"Using configuration: {config_path}")
            config = CleaningConfig(config_path)

        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif config_file:
        try:
            config = CleaningConfig(config_file)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)

    else:
        print("Error: Either --config, --auto-detect, or clean.yaml with auto_detect:true must be specified")
        sys.exit(1)

    # Validate configuration
    warnings = config.validate()
    if warnings:
        print("Configuration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        print()

    # Create cleaner
    cleaner = ContentCleaner(config)

    # Flush output directory if requested
    if flush and output_arg:
        output_path = Path(output_arg)
        if output_path.exists():
            if not dry_run:
                import shutil
                shutil.rmtree(output_path)
                print(f"Flushed output directory: {output_arg}")
            else:
                print(f"Would flush output directory: {output_arg}")
            print()

    # Delete files listed in config (before cleaning)
    if config.delete_files and output_arg:
        output_path = Path(output_arg)
        if output_path.exists():
            deleted_count = 0
            for filename in config.delete_files:
                file_to_delete = output_path / filename
                if file_to_delete.exists():
                    if not dry_run:
                        file_to_delete.unlink()
                    deleted_count += 1
                    if args.verbose:
                        print(f"Deleted: {filename}")

            if deleted_count > 0:
                action = "Would delete" if dry_run else "Deleted"
                print(f"{action} {deleted_count} file(s) from delete_files list\n")

    # Preview mode
    if args.preview:
        if input_path.is_file():
            preview_file = str(input_path)
        else:
            files = list(input_path.glob(pattern))
            if not files:
                print(f"No files matching '{pattern}' found")
                sys.exit(0)
            preview_file = str(files[0])

        print("=" * 70)
        print("PREVIEW MODE - First file:")
        print("=" * 70)
        print(cleaner.preview_changes(preview_file))
        sys.exit(0)

    # Process files
    print("=" * 70)
    print("CONTENT CLEANING")
    print("=" * 70)
    print(f"Input: {input_arg}")
    if output_arg:
        print(f"Output: {output_arg}")
    print(f"Config: {config.config_path}")
    print(f"Rules: {len(config.get_rules())}")
    print(f"Flush: {'Yes' if flush else 'No'}")

    if dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***\n")

    # Clean files
    try:
        if input_path.is_file():
            # Single file
            result = cleaner.clean_file(str(input_path), output_arg, dry_run)

            print(f"\nResults:")
            print(f"  Original size: {result['original_size']:,} bytes")
            print(f"  Cleaned size: {result['cleaned_size']:,} bytes")
            print(f"  Reduction: {result['reduction_percent']:.1f}%")

            if result.get('warnings'):
                print("\n  Warnings:")
                for warning in result['warnings']:
                    print(f"    - {warning}")

        else:
            # Directory
            results = cleaner.clean_directory(str(input_path), output_arg, pattern, dry_run)

            # Print summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)

            stats = cleaner.get_statistics()
            total_original = sum(r['original_size'] for r in results)
            total_cleaned = sum(r['cleaned_size'] for r in results)
            total_reduction = ((total_original - total_cleaned) / total_original * 100) if total_original > 0 else 0

            print(f"Files processed: {stats['files_processed']}")
            print(f"Files cleaned: {stats['files_cleaned']}")
            print(f"Total bytes removed: {stats['bytes_removed']:,}")
            print(f"Overall reduction: {total_reduction:.1f}%")

            if stats['errors']:
                print(f"\nErrors: {len(stats['errors'])}")
                for error in stats['errors']:
                    print(f"  - {error}")

            # Show files with warnings
            warned_files = [r for r in results if r.get('warnings')]
            if warned_files:
                print(f"\nFiles with warnings: {len(warned_files)}")
                for result in warned_files:
                    print(f"  {Path(result['file']).name}:")
                    for warning in result['warnings']:
                        print(f"    - {warning}")

    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    print("\n✓ Done!")


if __name__ == '__main__':
    main()
