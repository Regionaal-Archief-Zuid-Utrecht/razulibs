import sys
from functools import lru_cache
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import URIRef
from .sparql_endpoint_manager import SparqlEndpointManager


class Concept:
    """
    Represents a concept identified by a specific URI, allowing SPARQL queries
    for specific values related to that concept.
    """

    def __init__(self, uri: URIRef):
        """ Initializes the Concept with its associated URI and determines the SPARQL endpoint. """
        self.uri = uri
        self.sparql_endpoint = SparqlEndpointManager.get_endpoint_by_uri(uri)

    @lru_cache(maxsize=128)
    def get_value(self, predicate: URIRef) -> str:
        """ Fetches the value for a given predicate for this concept. """
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
                return bindings[0]['value']['value']
            raise ValueError(f"No value found for {self.uri} and predicate: {predicate}")     
        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            sys.exit(1)
    
    def get_uri(self) -> URIRef:
        """ Returns the URI of the concept. """
        return self.uri


class ConceptResolver:
    """
    Resolves URIs for terms from a vocabulary and creates Concept objects.
    """

    PREFIXES = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>
    """

    def __init__(self, vocabulary: str):
        """ Initialize with vocabulary name. """
        self.vocabulary = vocabulary

    @lru_cache(maxsize=256)
    def get_concept(self, term: str) -> Concept:
        """ Retrieves a Concept object for the given term. """
        query = self._build_query(term)
        response = self._execute_query(query)

        if response:
            bindings = response.get('results', {}).get('bindings', [])
            if bindings:
                uri = URIRef(bindings[0]['uri']['value'])
                return Concept(uri)
        raise ValueError(f"No Concept found for term: {term}")

    def get_concept_value(self, term: str, predicate: URIRef) -> str:
        """ Get a concept's predicate value. """
        return self.get_concept(term).get_value(predicate)

    def get_concept_uri(self, term: str) -> URIRef:
        """ Get a concept's URI. """
        return self.get_concept(term).get_uri()

    def _build_query(self, term: str) -> str:
        """ Builds the SPARQL query for a term. """
        return f"""
        {self.PREFIXES}

        SELECT ?uri WHERE {{
            ?uri skos:prefLabel|schema:name|rdfs:label|skos:altLabel|schema:identifier|skos:notation "{term}".
        }} LIMIT 1
        """

    def _execute_query(self, query: str) -> dict:
        """ Executes a SPARQL query. """
        sparql_service = SPARQLWrapper(
            SparqlEndpointManager.get_endpoint_by_vocabulary(self.vocabulary)
        )
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)

        try:
            return sparql_service.query().convert()
        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            sys.exit(1)
