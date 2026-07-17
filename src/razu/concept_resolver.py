import sys
from functools import lru_cache
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import URIRef
from razu.sparql_endpoint_manager import SparqlEndpointManager

# class Concept:
# represent a subject node of a thesaurus (URI)
# --> Attributes:
# - uri (ex: https://data.razu.nl/id/actor/124f62d77ae9d7beadab9dc57bced177) (Gemeente Rhenen)
# - sparql_endpoint (ex: https://data.razu.nl/id/actor/sparql)
# - graph URI (ex: https://data.razu.nl/id/actor/bd4867122112bf6248d97334ea20479e)
# ---> Methods:
# - get_value(predicate: URIRef) -> str: Fetches the value for a given predicate for this concept.
# - get_all_values() -> dict: Fetches all values for this concept.

# class ConceptResolver:
# --> Attributes:
# - thesaurus: a name or a URI of a RAZU thesaurus
# --> Methods:
# - get_concept_from_term(term: str) -> Concept: Resolves a term to a Concept object.

# USE
# Either initialize a Concept class independently if URI is known, or initialize it from a ConceptResolver if you only know some values of the concept.
# Both classes call methods from SparqlEndpointManager to determine the SPARQL endpoint.

class Concept:
    '''Represents a skos:Concept identified by a specific URI from a thesaurus, allowing SPARQL queries
    for specific values related to that concept.'''

    def __init__(self, concept_uri):
        self.uri = concept_uri
        self.sparql_endpoint = SparqlEndpointManager.get_endpoint_by_uri(concept_uri)
        self.graph_uri = self.get_value(URIRef("http://www.w3.org/2004/02/skos/core#inScheme")) 
    
    @lru_cache(maxsize=128)
    def get_value(self, predicate: URIRef) -> str:
        """ Takes a predicate in input and fetches the value for a given predicate for this concept."""
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
    
    def get_values(self, predicate: URIRef) -> list[str]:
        """Returns all values for a given predicate as a list."""
        query = f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>

        SELECT ?value WHERE {{
            <{self.uri}> <{predicate}> ?value .
        }}
        """
        sparql_service = SPARQLWrapper(self.sparql_endpoint)
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)

        try:
            response = sparql_service.query().convert()
            bindings = response.get('results', {}).get('bindings', [])
            return [b['value']['value'] for b in bindings if 'value' in b]
        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            return []

    # !! MG: to cache? and also exectuing query could be a reusable bit
    def get_all_values(self) -> dict:
        """ Returns all values for this concept. """
        query = f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>

        SELECT ?p ?o WHERE {{
            <{self.uri}> ?p ?o .
       }}
        """
        sparql_service = SPARQLWrapper(self.sparql_endpoint)
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)

        try:
            response = sparql_service.query().convert()
            bindings = response.get('results', {}).get('bindings', [])
            if bindings:
                return {binding['p']['value']: binding['o']['value'] for binding in bindings}
            raise ValueError(f"No values found for {self.uri}")     
        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")


class ConceptResolver:
    """
    Resolves URIs for terms from a vocabulary and creates Concept objects.
    """
    # !! in the other class they are within the query here abstracted, to harmonize
    PREFIXES = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>
    """

    def __init__(self, thesaurus: str | URIRef):
        if isinstance(thesaurus, URIRef):
            self.endpoint = SparqlEndpointManager.get_endpoint_by_uri(thesaurus)   
        elif isinstance(thesaurus, str):
            self.endpoint = SparqlEndpointManager.get_endpoint_by_vocabulary(thesaurus)
        else:
            raise ValueError(f"Invalid thesaurus type: {type(thesaurus)}")

    @lru_cache(maxsize=256)
    def get_concept_obj_from_term(self, term: str) -> Concept:
        """ Retrieves a Concept object for the given Literal value term. """
        query = f"""
        {self.PREFIXES}

        SELECT ?uri WHERE {{
            {{ 
                ?uri skos:prefLabel|schema:name|rdfs:label|skos:altLabel|schema:identifier|skos:notation "{term}".
            }} UNION {{
                ?uri skos:prefLabel|schema:name|rdfs:label|skos:altLabel|schema:identifier|skos:notation "{term}"@nl.
            }} UNION {{
                ?uri skos:prefLabel|schema:name|rdfs:label|skos:altLabel|schema:identifier|skos:notation "{term}"@en.
            }}
        }} LIMIT 1
        """
        sparql_service = SPARQLWrapper(self.endpoint)
        sparql_service.setQuery(query)
        sparql_service.setReturnFormat(JSON)
        
        try:
            response = sparql_service.query().convert()
        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            return None

        if response:
            bindings = response.get('results', {}).get('bindings', [])
            if bindings:
                uri = URIRef(bindings[0]['uri']['value'])
                return Concept(uri)
        return None # changed for integration in rdf_generator

        

# test
# c = Concept(URIRef("https://data.razu.nl/id/actor/54c9a2e607988deae23c920dae4f43e4"))
# print(c.get_value(URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")))
# print("\n##############################\n")
# print(c.get_all_values())
# print("\n##############################\n")
# print(c.uri, c.graph_uri, c.sparql_endpoint)

# c_builder = ConceptResolver(URIRef("https://data.razu.nl/id/actor/bd4867122112bf6248d97334ea20479e"))
# print(c_builder.get_concept_obj_from_term("Joris van Bennekom").get_value(URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")))
# print("\n##############################\n")
# c_build_term = ConceptResolver("locatie")
# print(c_build_term.get_concept_obj_from_term("Zeist (plaats)").get_value(URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")))