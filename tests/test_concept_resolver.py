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
        uri = URIRef(f"http://example.org/{cfg.resource_identifier_segment}/concept")
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
        uri = URIRef(f"http://example.org/{cfg.resource_identifier_segment}/concept")
        predicate = URIRef("http://example.org/predicate")
        concept = Concept(uri)
        
        # Mock het SPARQL antwoord
        mock_query = MagicMock()
        mock_query.query().convert.return_value = {
            'results': {
                'bindings': [{
                    'value': {
                        'type': 'literal',
                        'value': 'queried_value'
                    }
                }]
            }
        }
        mock_sparql_wrapper.return_value = mock_query
        
        result = concept.get_value(predicate)
        
        assert result == "queried_value"
        assert concept.cache[str(predicate)] == "queried_value"  # Controleer dat de waarde wordt gecachet

    def test_get_uri(self):
        """Test of de URI correct wordt teruggegeven."""
        cfg = RazuConfig()
        uri = URIRef(f"http://example.org/{cfg.resource_identifier_segment}/concept")
        concept = Concept(uri)
        assert concept.get_uri() == uri


# Test voor de ConceptResolver class
class TestConceptResolver:

    @patch('razu.concept_resolver.SparqlEndpointManager.get_endpoint_by_vocabulary')
    @patch('razu.concept_resolver.SparqlEndpointManager.get_endpoint_by_uri')
    @patch('razu.concept_resolver.SPARQLWrapper')  # Mock de SPARQLWrapper om netwerkverzoeken te simuleren
    def test_get_concept_cached(self, mock_sparql_wrapper, mock_get_endpoint_by_uri, mock_get_endpoint_by_vocabulary):
        """Test of de cache correct werkt voor termen."""
        # Mock de endpoint URLs
        mock_get_endpoint_by_vocabulary.return_value = "http://mock.endpoint/vocabulary"
        mock_get_endpoint_by_uri.return_value = "http://mock.endpoint/uri"
        
        cfg = RazuConfig()
        resolver = ConceptResolver("vocabulary")
        term = "example_term"
        cached_concept = Concept(URIRef(f"http://example.org/{cfg.resource_identifier_segment}/concept"))
        resolver.cache[term] = cached_concept
        
        # Test dat de cache wordt gebruikt
        concept = resolver.get_concept(term)
        assert concept == cached_concept
        mock_sparql_wrapper.assert_not_called()

    @patch('razu.concept_resolver.SparqlEndpointManager.get_endpoint_by_vocabulary')
    @patch('razu.concept_resolver.SparqlEndpointManager.get_endpoint_by_uri')
    @patch('razu.concept_resolver.SPARQLWrapper')  # Mock de SPARQLWrapper om netwerkverzoeken te simuleren
    def test_get_concept_from_sparql(self, mock_sparql_wrapper, mock_get_endpoint_by_uri, mock_get_endpoint_by_vocabulary):
        """Test het ophalen van een concept via SPARQL."""
        # Mock de endpoint URLs
        mock_get_endpoint_by_vocabulary.return_value = "http://mock.endpoint/vocabulary"
        mock_get_endpoint_by_uri.return_value = "http://mock.endpoint/uri"
        
        cfg = RazuConfig()
        resolver = ConceptResolver("vocabulary")
        term = "example_term"
        
        # Mock het SPARQL antwoord
        mock_query = MagicMock()
        mock_query.query().convert.return_value = {
            'results': {
                'bindings': [{
                    'concept': {
                        'type': 'uri',
                        'value': f'http://example.org/{cfg.resource_identifier_segment}/concept'
                    }
                }]
            }
        }
        mock_sparql_wrapper.return_value = mock_query
        
        concept = resolver.get_concept(term)
        
        assert concept.get_uri() == URIRef(f"http://example.org/{cfg.resource_identifier_segment}/concept")
        assert resolver.cache[term].get_uri() == URIRef(f"http://example.org/{cfg.resource_identifier_segment}/concept")

    @patch('razu.concept_resolver.SparqlEndpointManager.get_endpoint_by_vocabulary')
    @patch('razu.concept_resolver.SparqlEndpointManager.get_endpoint_by_uri')
    @patch('razu.concept_resolver.SPARQLWrapper')  # Mock de SPARQLWrapper om netwerkverzoeken te simuleren
    def test_get_concept_value(self, mock_sparql_wrapper, mock_get_endpoint_by_uri, mock_get_endpoint_by_vocabulary):
        """Test het ophalen van een waarde voor een concept en predicate."""
        # Mock de endpoint URLs
        mock_get_endpoint_by_vocabulary.return_value = "http://mock.endpoint/vocabulary"
        mock_get_endpoint_by_uri.return_value = "http://mock.endpoint/uri"
        
        cfg = RazuConfig()
        resolver = ConceptResolver("vocabulary")
        term = "example_term"
        predicate = URIRef("http://example.org/predicate")
        
        # Mock het SPARQL antwoord voor get_concept
        mock_instance = MagicMock()
        mock_instance.query().convert.return_value = {
            'results': {
                'bindings': [{
                    'uri': {
                        'type': 'uri',
                        'value': f'http://example.org/{cfg.resource_identifier_segment}/concept'
                    }
                }]
            }
        }
        
        # Mock het SPARQL antwoord voor get_value
        mock_instance2 = MagicMock()
        mock_instance2.query().convert.return_value = {
            'results': {
                'bindings': [{
                    'value': {
                        'type': 'literal',
                        'value': 'queried_value'
                    }
                }]
            }
        }
        
        # Return verschillende mock instances voor elke SPARQLWrapper instantiatie
        mock_sparql_wrapper.side_effect = [mock_instance, mock_instance2]
        
        # Debug prints
        print("Testing get_concept_value...")
        concept = resolver.get_concept(term)
        print(f"Concept: {concept}")
        if concept:
            print(f"Concept URI: {concept.get_uri()}")
            value = concept.get_value(predicate)
            print(f"Value: {value}")
        else:
            print("No concept found!")
            
        value = resolver.get_concept_value(term, predicate)
        assert value == "queried_value"
