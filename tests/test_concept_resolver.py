import pytest
from unittest.mock import patch, MagicMock
from rdflib import URIRef
from razu.concept_resolver import Concept, ConceptResolver
from razu.sparql_endpoint_manager import SparqlEndpointManager
from razu.razuconfig import RazuConfig 

# Test voor de Concept class
class TestConcept:
    
    @patch('razu.concept_resolver.SPARQLWrapper')  # Mock de SPARQLWrapper om netwerkverzoeken te simuleren
    def test_get_value_cached(self, mock_sparql_wrapper):
        """Test of de cache correct wordt gebruikt."""
        cfg = RazuConfig()
        uri = URIRef(f"http://example.org/{cfg.resource_identifier}/concept")
        predicate = URIRef("http://example.org/predicate")
        concept = Concept(uri)

        # Vul de cache handmatig
        concept.cache[str(predicate)] = "cached_value"
        
        # Test dat de cache wordt geraadpleegd en geen nieuw SPARQL-verzoek wordt gedaan
        result = concept.get_value(predicate)
        assert result == "cached_value"
        mock_sparql_wrapper.assert_not_called()

    @patch('razu.concept_resolver.SPARQLWrapper')  # Mock de SPARQLWrapper om netwerkverzoeken te simuleren
    def test_get_value_from_sparql(self, mock_sparql_wrapper):
        """Test het ophalen van waarde via SPARQL wanneer niet in cache."""
        cfg = RazuConfig()
        uri = URIRef(f"http://example.org/{cfg.resource_identifier}/concept")
        predicate = URIRef("http://example.org/predicate")
        concept = Concept(uri)
        
        # Mock het SPARQL antwoord
        mock_query = MagicMock()
        mock_query.query().convert.return_value = {
            'results': {'bindings': [{'value': {'value': 'queried_value'}}]}
        }
        mock_sparql_wrapper.return_value = mock_query
        
        result = concept.get_value(predicate)
        
        assert result == "queried_value"
        assert concept.cache[str(predicate)] == "queried_value"  # Controleer dat de waarde wordt gecachet

    def test_get_uri(self):
        """Test of de URI correct wordt teruggegeven."""
        cfg = RazuConfig()
        uri = URIRef(f"http://example.org/{cfg.resource_identifier}/concept")
        concept = Concept(uri)
        assert concept.get_uri() == uri


# Test voor de ConceptResolver class
class TestConceptResolver:

    @patch('razu.concept_resolver.SPARQLWrapper')  # Mock de SPARQLWrapper om netwerkverzoeken te simuleren
    def test_get_concept_cached(self, mock_sparql_wrapper):
        """Test of de cache correct werkt voor termen."""
        cfg = RazuConfig()
        resolver = ConceptResolver("vocabulary")
        term = "example_term"
        cached_concept = Concept(URIRef(f"http://example.org/{cfg.resource_identifier}/concept"))
        resolver.cache[term] = cached_concept
        
        # Test dat de cache wordt gebruikt
        concept = resolver.get_concept(term)
        assert concept == cached_concept
        mock_sparql_wrapper.assert_not_called()

    @patch('razu.concept_resolver.SPARQLWrapper')  # Mock de SPARQLWrapper om netwerkverzoeken te simuleren
    def test_get_concept_from_sparql(self, mock_sparql_wrapper):
        """Test het ophalen van een concept via SPARQL."""
        cfg = RazuConfig()
        resolver = ConceptResolver("vocabulary")
        term = "example_term"
        
        # Mock het SPARQL antwoord
        mock_query = MagicMock()
        mock_query.query().convert.return_value = {
            'results': {'bindings': [{'uri': {'value': f'http://example.org/{cfg.resource_identifier}/concept'}}]}
        }
        mock_sparql_wrapper.return_value = mock_query
        
        concept = resolver.get_concept(term)
        
        assert concept.get_uri() == URIRef(f"http://example.org/{cfg.resource_identifier}/concept")
        assert resolver.cache[term].get_uri() == URIRef(f"http://example.org/{cfg.resource_identifier}/concept")

    @patch('razu.concept_resolver.SPARQLWrapper')  # Mock de SPARQLWrapper om netwerkverzoeken te simuleren
    def test_get_concept_value(self, mock_sparql_wrapper):
        """Test het ophalen van een waarde voor een concept en predicate."""
        cfg = RazuConfig()
        resolver = ConceptResolver("vocabulary")
        term = "example_term"
        predicate = URIRef("http://example.org/predicate")
        
        # Mock het SPARQL antwoord voor zowel term als predicate
        mock_query = MagicMock()
        mock_query.query().convert.side_effect = [
            # Eerste mock is voor get_concept
            {
                'results': {'bindings': [{'uri': {'value': f'http://example.org/{cfg.resource_identifier}/concept'}}]}
            },
            # Tweede mock is voor get_value
            {
                'results': {'bindings': [{'value': {'value': 'queried_value'}}]}
            }
        ]
        mock_sparql_wrapper.return_value = mock_query
        
        value = resolver.get_concept_value(term, predicate)
        assert value == "queried_value"
