from typing import Dict, Optional, ClassVar
from rdflib import URIRef

from razu.config import Config


class SparqlEndpointManager:
    """Manages SPARQL endpoints for different vocabularies."""

    _instance: ClassVar[Optional['SparqlEndpointManager']] = None
    _config: ClassVar[Optional[Config]] = None

    def __init__(self) -> None:
        """Private constructor, use get_instance() instead."""
        if self._instance is not None:
            raise RuntimeError("Use SparqlEndpointManager.get_instance()")
        
        self._config = Config.get_instance()

    @classmethod
    def get_instance(cls) -> 'SparqlEndpointManager':
        """Get the global instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None
        cls._config = None

    @classmethod
    def get_endpoint_by_vocabulary(cls, vocabulary: str) -> str:
        """Get the SPARQL endpoint URL for a given vocabulary. """
        config = Config.get_instance()
        return f"{config.sparql_endpoint_prefix}{vocabulary}{config.sparql_endpoint_suffix}"

    @classmethod
    def get_endpoint_by_uri(cls, uri: URIRef) -> str:
        """Get the SPARQL endpoint URL for a concept URI.
        
        Args:
            uri: The URI of the concept
            
        Returns:
            The endpoint URL
            
        Raises:
            ValueError: If the URI doesn't contain a vocabulary segment
            KeyError: If no endpoint is found for the vocabulary
        """
        instance = cls.get_instance()
        uri_str = str(uri)
        segment = f"/{instance._config.resource_identifier_segment}/"
        
        if segment not in uri_str:
            raise ValueError(f"Invalid URI structure: No '{segment}' segment found")
        
        vocabulary = uri_str.split(segment)[1].split("/")[0]
        return cls.get_endpoint_by_vocabulary(vocabulary)
