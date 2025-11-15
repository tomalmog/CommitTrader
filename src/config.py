"""Configuration management for CommitTrader."""

import os
from pathlib import Path
from typing import Any, Dict
import yaml


class Config:
    """Configuration manager for CommitTrader."""

    def __init__(self, config_path: str = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config file. If None, uses default config.yaml
        """
        if config_path is None:
            # Default to config.yaml in project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Set up project paths
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.raw_data_dir = self.data_dir / "raw"
        self.processed_data_dir = self.data_dir / "processed"
        self.mappings_dir = self.data_dir / "mappings"

        # Ensure directories exist
        for directory in [self.raw_data_dir, self.processed_data_dir, self.mappings_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key (e.g., 'github.max_retries')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_github_token(self) -> str:
        """
        Get GitHub token from environment variable.

        Returns:
            GitHub token or None if not set
        """
        return os.environ.get('GITHUB_TOKEN')

    @property
    def event_window_pre(self) -> int:
        """Days before event in event window."""
        return self.get('event_study.event_window.pre', 5)

    @property
    def event_window_post(self) -> int:
        """Days after event in event window."""
        return self.get('event_study.event_window.post', 5)

    @property
    def estimation_window_start(self) -> int:
        """Start of estimation window (days before event)."""
        return self.get('event_study.estimation_window.start', -130)

    @property
    def estimation_window_end(self) -> int:
        """End of estimation window (days before event)."""
        return self.get('event_study.estimation_window.end', -31)

    @property
    def market_index(self) -> str:
        """Market index ticker for market model."""
        return self.get('stocks.market_index', '^GSPC')

    @property
    def risk_free_rate(self) -> float:
        """Annual risk-free rate."""
        return self.get('stocks.risk_free_rate', 0.04)


# Global config instance
_config = None


def get_config(config_path: str = None) -> Config:
    """
    Get global configuration instance.

    Args:
        config_path: Path to config file (only used on first call)

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
