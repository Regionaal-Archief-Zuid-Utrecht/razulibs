from rdflib import URIRef
from razu.razuconfig import RazuConfig

class SparqlEndpointManager:
    """
    Static class responsible for determining the correct SPARQL endpoint
    based on either a concept URI or a vocabulary name (part of URI).
    """

    @staticmethod
    def get_endpoint_by_vocabulary(vocabulary: str) -> str:
        """
        Determines the SPARQL endpoint based on the vocabulary.

        Parameters:
        -----------
        vocabulary : str
            The category or vocabulary list to query (e.g., 'actor', 'category').

        Returns:
        --------
        str:
            The full SPARQL endpoint URL.
        """
        config = RazuConfig()
        return f"{config.sparql_endpoint_prefix}{vocabulary}{config.sparql_endpoint_suffix}"

    @staticmethod
    def get_endpoint_by_uri(uri: URIRef) -> str:
        """
        Determines the SPARQL endpoint based on the concept's URI by extracting the part
        after '/id/' (actually config.resource_identifier) and using it to form the SPARQL endpoint.

        Parameters:
        -----------
        uri : URIRef
            The URI of the concept.

        Returns:
        --------
        str:
            The full SPARQL endpoint URL for the given URI.
        """
        config = RazuConfig()
        
        uri_str = str(uri)
        if f"/{config.resource_identifier}/" in uri_str:
            vocabulary = uri_str.split(f"/{config.resource_identifier}/")[1].split("/")[0]
        else:
            raise ValueError(f"Invalid URI structure: No '/{config.resource_identifier}/' segment found")

        return f"{config.sparql_endpoint_prefix}{vocabulary}{config.sparql_endpoint_suffix}"
