from rdflib import URIRef
from razu.config import Config


class SparqlEndpointManager:
    """Manages SPARQL endpoints for different vocabularies. """

    @staticmethod
    def get_endpoint_by_vocabulary(vocabulary: str) -> str:
        """Get the SPARQL endpoint URL for a given vocabulary. """
        config = Config.get_instance()
        return f"{config.sparql_endpoint_prefix}{vocabulary}{config.sparql_endpoint_suffix}"

    @staticmethod
    def get_endpoint_by_uri(uri: URIRef) -> str:
        """Get the SPARQL endpoint URL for a concept URI. """
        # Extract vocabulary from URI
        uri_str = str(uri)
        parts = uri_str.split('/')
        if len(parts) < 4:
            raise ValueError(f"URI does not contain a vocabulary segment: {uri}")
        vocabulary = parts[4]
        return SparqlEndpointManager.get_endpoint_by_vocabulary(vocabulary)
