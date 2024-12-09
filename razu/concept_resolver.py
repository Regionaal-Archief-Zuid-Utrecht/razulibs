import sys
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import URIRef
from .sparql_endpoint_manager import SparqlEndpointManager


class Concept:
    """
    Represents a concept identified by a specific URI, allowing SPARQL queries
    for specific values related to that concept.
    
    Attributes:
    -----------
    uri : URIRef
        The URI of the concept being queried.
    sparql_endpoint : str
        The SPARQL endpoint URL where queries will be sent.
    cache : dict
        A dictionary cache to store query results for predicates to avoid duplicate queries.
    
    Methods:
    --------
    get_value(predicate: URIRef) -> str
        Retrieves the value for a given predicate associated with this concept.
        Uses caching to avoid unnecessary queries for the same predicate.
    
    get_uri() -> URIRef
        Returns the URI of the concept.
    """

    def __init__(self, uri: URIRef):
        """
        Initializes the Concept with its associated URI and determines the SPARQL endpoint.

        Parameters:
        -----------
        uri : URIRef
            The URI representing the concept.
        """
        self.uri = uri
        self.sparql_endpoint = SparqlEndpointManager.get_endpoint_by_uri(uri)
        self.cache = {}

    def get_value(self, predicate: URIRef) -> str:
        """
        Fetches the value for a given predicate for this concept.

        Executes a SPARQL query to retrieve the value associated with the given predicate for this concept's URI. 
        Uses caching to avoid unnecessary queries for the same predicate.
        """
        predicate_str = str(predicate)
        
        # Check cache
        if predicate_str in self.cache:
            return self.cache[predicate_str]

        # Build SPARQL query
        query = f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>

        SELECT ?value WHERE {{
            <{self.uri}> <{predicate}> ?value .
        }} LIMIT 1
        """
        
        sparql_service = SPARQLWrapper(self.sparql_endpoint)
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)

        try:
            response = sparql_service.query().convert()
            bindings = response.get('results', {}).get('bindings', [])
            if bindings and 'value' in bindings[0]:
                value = bindings[0]['value']['value']
                self.cache[predicate_str] = value
                return value
            else:
                raise ValueError(f"No value found for {self.uri} and predicate: {predicate}")     
        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            sys.exit(1)
    
    def get_uri(self) -> URIRef:
        """
        Returns the URI of the concept.
        
        Returns:
        --------
        URIRef:
            The URI of this concept.
        """
        return self.uri


class ConceptResolver:
    """
    Resolves URIs for terms from a vocabulary and creates Concept objects,
    using caching to avoid repeated SPARQL queries for the same term.
    
    Singleton implementation ensures only one instance of ConceptResolver exists per vocabulary.
    """

    _instances = {}

    PREFIXES = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>
    """

    def __new__(cls, vocabulary: str):
        """
        Ensures only one instance of ConceptResolver exists per vocabulary.
        If an instance with the same vocabulary already exists, it returns the existing instance.
        """
        if vocabulary not in cls._instances:
            instance = super(ConceptResolver, cls).__new__(cls)
            cls._instances[vocabulary] = instance
        return cls._instances[vocabulary]

    def __init__(self, vocabulary: str):
        """
        Initializes the ConceptResolver for a specific vocabulary, if it hasn't been initialized yet.
        """
        if not hasattr(self, "is_initialized"):
            self.vocabulary = vocabulary
            self.cache = {}
            self.is_initialized = True  # Mark as initialized to avoid re-initialization

    def get_concept(self, term: str) -> Concept:
        """
        Retrieves a Concept object for the given term. Uses caching to avoid
        repeated queries for the same term.
        """
        if term in self.cache:
            return self.cache[term]

        query = self._build_query(term)
        response = self._execute_query(query)

        if response:
            bindings = response.get('results', {}).get('bindings', [])
            if bindings:
                uri = URIRef(bindings[0]['uri']['value'])
                concept = Concept(uri)
                self.cache[term] = concept  # Cache the concept
                return concept
        # If no concept is found, raise an error
        raise ValueError(f"No Concept found for term: {term}")
        exit(1)

    # shortcut
    def get_concept_value(self, term: str, predicate: URIRef) -> str:
        concept = self.get_concept(term)
        return concept.get_value(predicate) if concept else None

    # shortcut
    def get_concept_uri(self, term: str) -> URIRef:
        concept = self.get_concept(term)
        return concept.get_uri() if concept else None

    def _build_query(self, term: str) -> str:
        """
        Builds the SPARQL query to fetch the URI for a given term.

        Parameters:
        -----------
        term : str
            The term for which the URI is being queried.

        Returns:
        --------
        str:
            The SPARQL query string.
        """
        return f"""
        {self.PREFIXES}

        SELECT ?uri WHERE {{
            ?uri skos:prefLabel|schema:name|rdfs:label|skos:altLabel|schema:identifier|skos:notation "{term}".
        }} LIMIT 1
        """

    def _execute_query(self, query: str) -> dict:
        """
        Executes the given SPARQL query and returns the response as a JSON object.

        Parameters:
        -----------
        query : str
            The SPARQL query to be executed.

        Returns:
        --------
        dict:
            The JSON response from the SPARQL query.
        """
        sparql_service = SPARQLWrapper(SparqlEndpointManager.get_endpoint_by_vocabulary(self.vocabulary))
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)

        try:
            response = sparql_service.query().convert()
            return response
        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            sys.exit(1)
