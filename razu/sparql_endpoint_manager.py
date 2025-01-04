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
        config = Config.get_instance()
        uri_str = str(uri)
        if f"/{config.resource_identifier_segment}/" in uri_str:
            vocabulary = uri_str.split(f"/{config.resource_identifier_segment}/")[1].split("/")[0]
        else:
            raise ValueError(f"Invalid URI structure: No '/{config.resource_identifier_segment}/' segment found")
        return SparqlEndpointManager.get_endpoint_by_vocabulary(vocabulary)
