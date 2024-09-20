from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import URIRef
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
    
    get_value(term: str, predicate: URIRef) -> str
        Fetches the value of the provided predicate for the resolved URI of the concept matching the term.
    """

    def __init__(self, vocabulary: str, endpoint_suffix: str = "/sparql"):
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
        """ Builds the SPARQL query to resolve a URI for the given term. """
        return f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>
        
        SELECT ?uri WHERE {{
            ?uri skos:prefLabel|schema:name|rdfs:label|skos:altLabel|schema:identifier "{term}".
        }} LIMIT 1
        """

    def _fetch_uri(self, term: str) -> URIRef:
        """ Fetches the URI for the given term by querying the SPARQL endpoint.
        Utilizes caching to avoid duplicate requests for the same term.
        Returns a URIRef object.
        """
        if term in self.cache and "uri" in self.cache[term]:
            return self.cache[term]["uri"]

        sparql_service = SPARQLWrapper(f"{self.config.sparql_endpoint_prefix}{self.vocabulary}{self.endpoint_suffix}")
        query = self._build_query(term)
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)

        try:
            response = sparql_service.query().convert()
            bindings = response.get('results', {}).get('bindings', [])

            if bindings:
                uri = URIRef(bindings[0]['uri']['value'])  # URIRef wordt nu gemaakt
            else:
                uri = None

            # Update cache
            if term not in self.cache:
                self.cache[term] = {}
            self.cache[term]["uri"] = uri
            return uri

        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            return None

    def get_uri(self, term: str) -> URIRef:
        """ Public method to get the URI of a concept based on the provided term as a URIRef. """
        return self._fetch_uri(term)

    def get_value(self, term: str, predicate: URIRef) -> str:
        """ 
        Public method to get the value of a predicate for a concept.
        
        Fetches the value for the given predicate for the URI of the concept that matches the provided term.
        Utilizes caching to avoid duplicate requests for the same term and predicate combination.
        """
        # Convert the predicate to a string if it's an rdflib URIRef
        predicate_str = str(predicate)

        # Check if the result is already cached
        if term in self.cache and predicate_str in self.cache[term]:
            return self.cache[term][predicate_str]

        uri = self.get_uri(term)
        if not uri:
            return None

        query = f"""
        SELECT ?value WHERE {{
            <{uri}> <{predicate_str}> ?value .
        }} LIMIT 1
        """

        sparql_service = SPARQLWrapper(f"{self.config.sparql_endpoint_prefix}{self.vocabulary}{self.endpoint_suffix}")
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)

        try:
            response = sparql_service.query().convert()
            bindings = response.get('results', {}).get('bindings', [])

            if bindings:
                value = bindings[0]['value']['value']
            else:
                value = None

            # Cache the result
            if term not in self.cache:
                self.cache[term] = {}
            self.cache[term][predicate_str] = value

            return value

        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            return None
