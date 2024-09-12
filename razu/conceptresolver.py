from SPARQLWrapper import SPARQLWrapper, JSON

from .razuconfig import RazuConfig

class ConceptResolver:
    """
    A class that resolves a concept's URI by querying a SPARQL endpoint based on a provided term.

    This class is designed to query a specific vocabulary or list of concepts.

    Attributes:
    -----------
    config : RazuConfig
        Configuration object containing SPARQL endpoint details.
    vocabulary: str
        The specific vocabulary or category (e.g., 'actor', 'algoritme') to be used in the SPARQL query.
    cache : dict
        A dictionary used to cache previous queries for faster lookups.

    Methods:
    --------
    get_uri(term: str) -> str
        Fetches the URI of the concept matching the provided term, using the cache if available.
    """

    def __init__(self, vocabulary:str, endpoint_suffix: str = "/sparql"):
        """
        Initializes the ConceptResolver with a given vocabulary type.

        Parameters:
        -----------
        vocabulary : str
            The category or vocabulary list to query (e.g., 'person', 'category').
        """
        self.config = RazuConfig()
        self.vocabulary = vocabulary
        self.endpoint_suffix = endpoint_suffix
        self.cache = {}

    def _build_query(self, term: str) -> str:
        """ Builds the SPARQL query to resolve a URI for the given term."""
        return f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>
        
        SELECT ?uri WHERE {{
            ?uri skos:prefLabel|schema:name|rdfs:label|skos:altLabel|skos:notation "{term}".
        }} LIMIT 1
        """

    def _fetch_uri(self, term: str) -> str:
        """ Fetches the URI for the given term by querying the SPARQL endpoint.
        Utilizes caching to avoid duplicate requests for the same term.
        """
        if term in self.cache:
            return self.cache[term]

        sparql_service= SPARQLWrapper(f"{self.config.sparql_endpoint_prefix}{self.vocabulary}{self.endpoint_suffix}")
        query = self._build_query(term)
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)

        try:
            response = sparql_service.query().convert()
            bindings = response.get('results', {}).get('bindings', [])

            if bindings:
                uri = bindings[0]['uri']['value']
            else:
                uri = None

            self.cache[term] = uri
            return uri

        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            return None

    def get_uri(self, term: str) -> str:
        """ Public method to get the URI of a concept based on the provided term. """
        return self._fetch_uri(term)
