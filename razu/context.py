from typing import Optional, Any, ClassVar
from razu.config import Config
from razu.identifiers import IdentifierFactory, ConfigBase


class RunContext:
    """Context for a specific run, containing run-specific configuration.
    
    This class holds configuration that is specific to one run/project,
    such as archive IDs and creator IDs. It also provides access to
    application-wide settings from Config and identifier generation
    through IdentifierFactory.
    """
    _instance: ClassVar[Optional['RunContext']] = None
    
    def __init__(
        self, 
        archive_id: str, 
        archive_creator_id: str,
        config: Optional[ConfigBase] = None
    ) -> None:
        """Private constructor, use initialize() or get_instance() instead."""
        if self._instance is not None:
            raise RuntimeError("Use RunContext.initialize() or RunContext.get_instance()")
            
        self.archive_id = archive_id
        self.archive_creator_id = archive_creator_id
        self._config = config or Config.get_instance()
        self._identifiers = IdentifierFactory(
            archive_id=self.archive_id,
            archive_creator_id=self.archive_creator_id,
            config=self._config
        )
    
    @classmethod
    def initialize(
        cls, 
        archive_id: str, 
        archive_creator_id: str,
        config: Optional[ConfigBase] = None
    ) -> 'RunContext':
        """Create and initialize the run context.
        
        Args:
            archive_id: ID of the archive ('toegang')
            archive_creator_id: ID of the archive creator
            config: Optional config instance. If not provided, will use
                   the global Config instance.
        
        Returns:
            The initialized run context.
        """
        if cls._instance is not None:
            raise RuntimeError("RunContext already initialized")
            
        cls._instance = cls(
            archive_id=archive_id,
            archive_creator_id=archive_creator_id,
            config=config
        )
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'RunContext':
        """Get the current run context.
        
        Returns:
            The global run context instance.
            
        Raises:
            RuntimeError: If not yet initialized
        """
        if cls._instance is None:
            raise RuntimeError(
                "RunContext not initialized. Call RunContext.initialize() first"
            )
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None
    
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to Config instance."""
        return getattr(self._config, name)
    
    @property
    def identifiers(self) -> IdentifierFactory:
        """Get the identifier factory."""
        return self._identifiers
