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
