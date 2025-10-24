"""Configuration loader for cleaning rules."""

import yaml
from pathlib import Path
from typing import List, Dict, Any
from .rules import (
    CleaningRule,
    ExactMatchRule,
    RegexRule,
    SectionBoundaryRule,
    LinePatternRule,
    RepeatingPatternRule
)


class CleaningConfig:
    """Load and manage cleaning rule configurations from YAML files."""

    RULE_TYPE_MAP = {
        'exact_match': ExactMatchRule,
        'regex': RegexRule,
        'section_boundary': SectionBoundaryRule,
        'line_pattern': LinePatternRule,
        'repeating_pattern': RepeatingPatternRule
    }

    def __init__(self, config_path: str = None):
        self.site = ""
        self.rules: List[CleaningRule] = []
        self.config_path = config_path

        if config_path:
            self.load_config(config_path)

    def load_config(self, path: str) -> None:
        """Load and parse YAML configuration file."""
        config_file = Path(path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        self.site = config_data.get('site', '')
        rules_data = config_data.get('rules', [])

        # Instantiate rule objects from configuration
        for rule_config in rules_data:
            rule_type = rule_config.get('type')

            if rule_type not in self.RULE_TYPE_MAP:
                print(f"Warning: Unknown rule type '{rule_type}', skipping")
                continue

            rule_class = self.RULE_TYPE_MAP[rule_type]
            rule = rule_class(rule_config)
            self.rules.append(rule)

        print(f"Loaded {len(self.rules)} cleaning rules for {self.site}")

    def get_rules(self) -> List[CleaningRule]:
        """Return all loaded rules."""
        return self.rules

    @staticmethod
    def find_config_for_domain(domain: str, config_dir: str = "cleaning_rules") -> str:
        """Find configuration file for a given domain."""
        config_dir_path = Path(config_dir)

        if not config_dir_path.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")

        # Try exact match first (e.g., hackingwithswift.com.yaml)
        exact_match = config_dir_path / f"{domain}.yaml"
        if exact_match.exists():
            return str(exact_match)

        # Try without TLD (e.g., hackingwithswift.yaml)
        domain_without_tld = domain.rsplit('.', 1)[0]
        no_tld_match = config_dir_path / f"{domain_without_tld}.yaml"
        if no_tld_match.exists():
            return str(no_tld_match)

        raise FileNotFoundError(f"No configuration found for domain: {domain}")

    @staticmethod
    def extract_domain_from_file(file_path: str) -> str:
        """Extract domain from frontmatter in markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for YAML frontmatter
        if not content.startswith('---\n'):
            return ""

        parts = content.split('---\n', 2)
        if len(parts) < 3:
            return ""

        frontmatter = yaml.safe_load(parts[1])
        original_url = frontmatter.get('original_url', '')

        # Extract domain from URL
        if original_url:
            # Remove protocol
            domain = original_url.replace('https://', '').replace('http://', '')
            # Remove path
            domain = domain.split('/')[0]
            # Remove www.
            domain = domain.replace('www.', '')
            return domain

        return ""

    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings/errors."""
        warnings = []

        if not self.site:
            warnings.append("No site specified in configuration")

        if not self.rules:
            warnings.append("No rules defined in configuration")

        for i, rule in enumerate(self.rules):
            if not rule.description:
                warnings.append(f"Rule {i} has no description")

        return warnings
