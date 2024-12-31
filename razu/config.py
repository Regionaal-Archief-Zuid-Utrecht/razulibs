import yaml
import inspect
from typing import Optional, Any, ClassVar
from pathlib import Path
from appdirs import user_config_dir
from abc import ABC, abstractmethod


class ConfigBase(ABC):
    """Abstract base class for configuration.
    
    This class defines the required configuration properties that must be
    implemented by any configuration class used with IdentifierFactory.
    """
    
    @property
    @abstractmethod
    def razu_base_uri(self) -> str:
        """Base URI for razu identifiers."""
        pass
    
    @property
    @abstractmethod
    def resource_identifier_segment(self) -> str:
        """Segment used in resource identifiers."""
        pass
    
    @property
    @abstractmethod
    def razu_file_id(self) -> str:
        """File ID for razu."""
        pass
    
    @property
    @abstractmethod
    def storage_base_domain(self) -> str:
        """Base domain for storage."""
        pass
    
    @property
    @abstractmethod
    def metadata_suffix(self) -> str:
        """Suffix for metadata files."""
        pass
    
    @property
    @abstractmethod
    def manifest_suffix(self) -> str:
        """Suffix for manifest files."""
        pass
    
    @property
    @abstractmethod
    def eventlog_suffix(self) -> str:
        """Suffix for eventlog files."""
        pass
    
    @property
    @abstractmethod
    def metadata_extension(self) -> str:
        """Extension for metadata files."""
        pass
    
    @abstractmethod
    def get_sparql_endpoint(self, vocabulary: str) -> str:
        """Get the SPARQL endpoint URL for a vocabulary (e.g., 'actor')
        """
        pass


class ConfigFileLocator:
    """Responsible for finding configuration files in the filesystem."""

    def __init__(self, config_filename: str, package_name: str):
        self.config_filename = config_filename
        self.package_name = package_name
        self._searched_locations: list[Path] = []

    def find_config_file(self) -> Optional[str]:
        r"""Find the configuration file in various locations.
        
        The file will be searched in the following locations, in order:
        1. The directory of the script that uses the library
        2. The current working directory
        3. The user's config directory:
           - Windows: %LOCALAPPDATA%\{package_name}\{filename}
           - macOS: ~/Library/Application Support/{package_name}/{filename}
           - Linux: ~/.config/{package_name}/{filename}
           
        Returns:
            Optional[str]: Path to the first found configuration file, or None if not found.
        """
        self._searched_locations = []
        config_file = Path(self.config_filename)

        # 1. Check script directory
        calling_frame = inspect.stack()[2]
        script_dir = Path(calling_frame.filename).parent
        script_config = script_dir / config_file
        self._searched_locations.append(script_dir)
        if script_config.is_file():
            return str(script_config)

        # 2. Check current working directory
        cwd = Path.cwd()
        cwd_config = cwd / config_file
        self._searched_locations.append(cwd)
        if cwd_config.is_file():
            return str(cwd_config)

        # 3. Check user config directory (platform specific)
        user_dir = Path(user_config_dir(self.package_name))
        home_config = user_dir / config_file
        self._searched_locations.append(user_dir)
        if home_config.is_file():
            return str(home_config)

        return None

    def get_search_locations(self) -> str:
        """Get a description of all locations that were searched for the config file."""
        if not self._searched_locations:
            return "No locations have been searched yet"
        
        return "\n".join(
            f"- {path}" + (" (script directory)" if i == 0 else
                         " (working directory)" if i == 1 else
                         " (user config directory)")
            for i, path in enumerate(self._searched_locations)
        )


class Config(ConfigBase):
    """Configuration class for managing application settings.
    
    This class reads configuration settings from a YAML file and implements
    the required config properties defined in ConfigBase.
    """
    _instance: ClassVar[Optional['Config']] = None
    _config_filename: ClassVar[str] = 'config.yaml'
    _package_name: ClassVar[str] = 'razu'

    def __init__(self, config_file: Optional[str] = None) -> None:
        """Private constructor, use initialize() or get_instance() instead."""
        if self._instance is not None:
            raise RuntimeError("Use Config.initialize() or Config.get_instance()")
        
        self._settings: dict[str, Any] = {}
        
        if config_file is None:
            locator = ConfigFileLocator(self._config_filename, self._package_name)
            config_file = locator.find_config_file()
            if config_file is None:
                raise FileNotFoundError(
                    f"Configuration file '{self._config_filename}' not found in any of these locations:\n"
                    f"{locator.get_search_locations()}"
                )
        
        self._load_settings_from_file(config_file)

    def _load_settings_from_file(self, config_file: str) -> None:
        """Load configuration settings from the YAML file."""
        try:
            with open(config_file, 'r') as f:
                self._settings = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Error loading config file: {e}")

    @classmethod
    def initialize(cls, config_file: Optional[str] = None) -> 'Config':
        """Initialize the global config instance.
        
        Args:
            config_file: Optional path to config file. If not provided,
                        will search in default locations.
        
        Returns:
            The initialized config instance.
            
        Raises:
            RuntimeError: If already initialized
            FileNotFoundError: If config file not found
            ValueError: If config file is invalid
        """
        if cls._instance is not None:
            raise RuntimeError("Config already initialized")
        cls._instance = cls(config_file)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'Config':
        """Get the global config instance.
        
        Returns:
            The global config instance.
            
        Raises:
            RuntimeError: If not yet initialized
        """
        if cls._instance is None:
            raise RuntimeError(
                "Config not initialized. Call Config.initialize() first"
            )
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None

    def __getattr__(self, name: str) -> Any:
        """Get a configuration setting."""
        if name in self._settings:
            return self._settings[name]
        raise AttributeError(f"Config has no setting '{name}'")

    # Required properties from ConfigBase
    @property
    def razu_base_uri(self) -> str:
        return self._settings['razu_base_uri']
    
    @property
    def resource_identifier_segment(self) -> str:
        return self._settings['resource_identifier_segment']
    
    @property
    def razu_file_id(self) -> str:
        return self._settings['razu_file_id']
    
    @property
    def storage_base_domain(self) -> str:
        return self._settings['storage_base_domain']
    
    @property
    def metadata_suffix(self) -> str:
        return self._settings['metadata_suffix']
    
    @property
    def manifest_suffix(self) -> str:
        return self._settings['manifest_suffix']
    
    @property
    def eventlog_suffix(self) -> str:
        return self._settings['eventlog_suffix']
    
    @property
    def metadata_extension(self) -> str:
        return self._settings['metadata_extension']
    
    def get_sparql_endpoint(self, vocabulary: str) -> str:
        """Get the SPARQL endpoint URL for a vocabulary.
        
        Args:
            vocabulary: The vocabulary to get the endpoint for (e.g., 'actor')
            
        Returns:
            The endpoint URL
            
        Raises:
            KeyError: If no endpoint is configured for this vocabulary
        """
        key = f'sparql_endpoint_{vocabulary}'
        if key not in self._settings:
            raise KeyError(f"No endpoint configured for vocabulary '{vocabulary}'")
        return self._settings[key]
