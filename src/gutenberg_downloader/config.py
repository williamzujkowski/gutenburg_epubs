"""Configuration management for Gutenberg downloader."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Try to import tomllib (Python 3.11+) or fall back to toml
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import toml as tomllib  # fallback to external toml package
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Application configuration."""
    
    # Database settings
    db_path: str = "gutenberg_books.db"
    
    # API settings
    api_base_url: str = "https://gutendex.com"
    api_timeout: int = 30
    api_retry_count: int = 3
    api_delay: float = 1.0
    
    # Download settings
    download_dir: str = "downloads"
    max_concurrent_downloads: int = 3
    skip_existing: bool = True
    smart_download: bool = True
    
    # Cache settings
    cache_dir: str = ".cache"
    cache_expiry: int = 86400  # 24 hours
    memory_cache_expiry: int = 300  # 5 minutes
    
    # Queue settings
    queue_workers: int = 3
    queue_state_file: str = "queue_state.json"
    
    # Export settings
    export_dir: str = "exports"
    export_limit: int = 10000
    
    # TUI settings
    tui_page_size: int = 100
    tui_theme: str = "dark"
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # User agent
    user_agent: str = "Gutenberg-Downloader/3.0 (+https://github.com/williamzujkowski/gutenburg_epubs)"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "db_path": self.db_path,
            "api": {
                "base_url": self.api_base_url,
                "timeout": self.api_timeout,
                "retry_count": self.api_retry_count,
                "delay": self.api_delay,
            },
            "download": {
                "dir": self.download_dir,
                "max_concurrent": self.max_concurrent_downloads,
                "skip_existing": self.skip_existing,
                "smart_download": self.smart_download,
            },
            "cache": {
                "dir": self.cache_dir,
                "expiry": self.cache_expiry,
                "memory_expiry": self.memory_cache_expiry,
            },
            "queue": {
                "workers": self.queue_workers,
                "state_file": self.queue_state_file,
            },
            "export": {
                "dir": self.export_dir,
                "limit": self.export_limit,
            },
            "tui": {
                "page_size": self.tui_page_size,
                "theme": self.tui_theme,
            },
            "logging": {
                "level": self.log_level,
                "file": self.log_file,
            },
            "user_agent": self.user_agent,
        }


class ConfigManager:
    """Manages application configuration."""
    
    DEFAULT_CONFIG_PATHS = [
        Path.home() / ".config" / "gutenberg-downloader" / "config.yaml",
        Path.home() / ".gutenberg-downloader.yaml",
        Path("gutenberg-downloader.yaml"),
        Path("config.yaml"),
    ]
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager.
        
        Args:
            config_path: Optional path to config file
        """
        self.config_path = config_path
        self.config = Config()
    
    def load(self) -> Config:
        """Load configuration from file."""
        config_file = self._find_config_file()
        
        if config_file:
            logger.info(f"Loading config from {config_file}")
            
            if config_file.suffix == ".yaml" or config_file.suffix == ".yml":
                data = self._load_yaml(config_file)
            elif config_file.suffix == ".toml":
                data = self._load_toml(config_file)
            else:
                logger.warning(f"Unknown config file format: {config_file}")
                return self.config
            
            if data:
                self.config = self._parse_config(data)
                logger.info("Configuration loaded successfully")
        else:
            logger.info("No config file found, using defaults")
        
        # Override with environment variables
        self._load_env_vars()
        
        return self.config
    
    def save(self, config_path: Optional[Path] = None) -> bool:
        """Save configuration to file.
        
        Args:
            config_path: Optional path to save config
            
        Returns:
            True if successful
        """
        save_path = config_path or self.config_path
        
        if not save_path:
            save_path = self.DEFAULT_CONFIG_PATHS[0]
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = self.config.to_dict()
            
            if save_path.suffix == ".yaml" or save_path.suffix == ".yml":
                with open(save_path, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False)
            elif save_path.suffix == ".toml":
                if tomllib and hasattr(tomllib, 'dump'):
                    with open(save_path, 'w') as f:
                        tomllib.dump(data, f)
                else:
                    # Try using toml instead
                    try:
                        import toml
                        with open(save_path, 'w') as f:
                            toml.dump(data, f)
                    except ImportError:
                        logger.error("Cannot save TOML file: no TOML writer available")
                        return False
            else:
                # Default to YAML
                save_path = save_path.with_suffix('.yaml')
                with open(save_path, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False)
            
            logger.info(f"Configuration saved to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file."""
        if self.config_path and self.config_path.exists():
            return self.config_path
        
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return path
        
        return None
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading YAML config: {e}")
            return {}
    
    def _load_toml(self, path: Path) -> Dict[str, Any]:
        """Load TOML configuration."""
        if not tomllib:
            logger.error("TOML support not available. Please install 'toml' package.")
            return {}
        
        try:
            with open(path, 'rb') as f:
                return tomllib.load(f)
        except Exception as e:
            logger.error(f"Error loading TOML config: {e}")
            return {}
    
    def _parse_config(self, data: Dict[str, Any]) -> Config:
        """Parse configuration data."""
        config = Config()
        
        # Direct attributes
        for key in ['db_path', 'user_agent']:
            if key in data:
                setattr(config, key, data[key])
        
        # API settings
        if 'api' in data:
            api = data['api']
            config.api_base_url = api.get('base_url', config.api_base_url)
            config.api_timeout = api.get('timeout', config.api_timeout)
            config.api_retry_count = api.get('retry_count', config.api_retry_count)
            config.api_delay = api.get('delay', config.api_delay)
        
        # Download settings
        if 'download' in data:
            dl = data['download']
            config.download_dir = dl.get('dir', config.download_dir)
            config.max_concurrent_downloads = dl.get('max_concurrent', config.max_concurrent_downloads)
            config.skip_existing = dl.get('skip_existing', config.skip_existing)
            config.smart_download = dl.get('smart_download', config.smart_download)
        
        # Cache settings
        if 'cache' in data:
            cache = data['cache']
            config.cache_dir = cache.get('dir', config.cache_dir)
            config.cache_expiry = cache.get('expiry', config.cache_expiry)
            config.memory_cache_expiry = cache.get('memory_expiry', config.memory_cache_expiry)
        
        # Queue settings
        if 'queue' in data:
            queue = data['queue']
            config.queue_workers = queue.get('workers', config.queue_workers)
            config.queue_state_file = queue.get('state_file', config.queue_state_file)
        
        # Export settings
        if 'export' in data:
            export = data['export']
            config.export_dir = export.get('dir', config.export_dir)
            config.export_limit = export.get('limit', config.export_limit)
        
        # TUI settings
        if 'tui' in data:
            tui = data['tui']
            config.tui_page_size = tui.get('page_size', config.tui_page_size)
            config.tui_theme = tui.get('theme', config.tui_theme)
        
        # Logging settings
        if 'logging' in data:
            log = data['logging']
            config.log_level = log.get('level', config.log_level)
            config.log_file = log.get('file', config.log_file)
        
        return config
    
    def _load_env_vars(self):
        """Load configuration from environment variables."""
        env_map = {
            'GUTENBERG_DB_PATH': 'db_path',
            'GUTENBERG_DOWNLOAD_DIR': 'download_dir',
            'GUTENBERG_CACHE_DIR': 'cache_dir',
            'GUTENBERG_LOG_LEVEL': 'log_level',
            'GUTENBERG_USER_AGENT': 'user_agent',
        }
        
        for env_var, config_attr in env_map.items():
            value = os.environ.get(env_var)
            if value:
                setattr(self.config, config_attr, value)
                logger.info(f"Overriding {config_attr} from environment: {value}")
    
    def generate_example_config(self, path: Path):
        """Generate example configuration file.
        
        Args:
            path: Path to save example config
        """
        example_config = {
            "db_path": "gutenberg_books.db",
            "api": {
                "base_url": "https://gutendex.com",
                "timeout": 30,
                "retry_count": 3,
                "delay": 1.0,
            },
            "download": {
                "dir": "downloads",
                "max_concurrent": 3,
                "skip_existing": True,
                "smart_download": True,
            },
            "cache": {
                "dir": ".cache",
                "expiry": 86400,
                "memory_expiry": 300,
            },
            "queue": {
                "workers": 3,
                "state_file": "queue_state.json",
            },
            "export": {
                "dir": "exports",
                "limit": 10000,
            },
            "tui": {
                "page_size": 100,
                "theme": "dark",
            },
            "logging": {
                "level": "INFO",
                "file": None,
            },
            "user_agent": "Gutenberg-Downloader/3.0",
        }
        
        if path.suffix == ".toml":
            try:
                import toml
                with open(path, 'w') as f:
                    toml.dump(example_config, f)
            except ImportError:
                logger.error("Cannot save TOML file: toml package not installed")
                return
        else:
            with open(path, 'w') as f:
                yaml.dump(example_config, f, default_flow_style=False)
        
        logger.info(f"Example config saved to {path}")