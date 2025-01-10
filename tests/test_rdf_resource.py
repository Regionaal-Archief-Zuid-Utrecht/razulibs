import pytest
from rdflib import URIRef, Literal, Graph
from razu.rdf_resource import RDFResource

# Test URIs and predicates we'll use
EXAMPLE_URI = "http://example.org/resource/1"
TITLE_PRED = URIRef("http://purl.org/dc/terms/title")
CREATOR_PRED = URIRef("http://purl.org/dc/terms/creator")
SUBJECT_PRED = URIRef("http://purl.org/dc/terms/subject")
TYPE_PRED = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
PERSON_TYPE = URIRef("http://xmlns.com/foaf/0.1/Person")
NAME_PRED = URIRef("http://xmlns.com/foaf/0.1/name")

def test_add_single_property():
    """Test het toevoegen van een enkele property via add_property."""
    resource = RDFResource(EXAMPLE_URI)
    resource.add_property(TITLE_PRED, "Test Title")

    # Controleer of de triple correct is toegevoegd
    assert (URIRef(EXAMPLE_URI), TITLE_PRED, Literal("Test Title")) in resource.graph

def test_add_nested_property():
    """Test het toevoegen van een geneste RDFResource als property."""
    resource = RDFResource(EXAMPLE_URI)
    creator = RDFResource()
    creator.add_property(TYPE_PRED, PERSON_TYPE)
    creator.add_property(NAME_PRED, "John Doe")
    
    resource.add_property(CREATOR_PRED, creator)

    # Controleer of alle triples correct zijn toegevoegd
    assert (URIRef(EXAMPLE_URI), CREATOR_PRED, creator.uri) in resource.graph
    assert (creator.uri, TYPE_PRED, PERSON_TYPE) in resource.graph
    assert (creator.uri, NAME_PRED, Literal("John Doe")) in resource.graph

def test_add_properties_from_dict():
    """Test het toevoegen van properties via een dictionary."""
    resource = RDFResource(EXAMPLE_URI)
    
    properties = {
        TITLE_PRED: "Test Title",
        CREATOR_PRED: {
            TYPE_PRED: PERSON_TYPE,
            NAME_PRED: "John Doe"
        }
    }
    
    resource.add_properties(properties)

    # Zoek de creator URI in de graph
    creator_uri = None
    for s, p, o in resource.graph:
        if p == CREATOR_PRED:
            creator_uri = o
            break

    # Controleer of alle triples correct zijn toegevoegd
    assert (URIRef(EXAMPLE_URI), TITLE_PRED, Literal("Test Title")) in resource.graph
    assert creator_uri is not None
    assert (creator_uri, TYPE_PRED, PERSON_TYPE) in resource.graph
    assert (creator_uri, NAME_PRED, Literal("John Doe")) in resource.graph

def test_add_properties_from_string():
    """Test het toevoegen van properties via een string met separator."""
    resource = RDFResource(EXAMPLE_URI)
    subjects = "History;Science;Mathematics"
    
    resource.add_properties_from_string(SUBJECT_PRED, subjects, ";")

    # Controleer of alle subjects correct zijn toegevoegd
    assert (URIRef(EXAMPLE_URI), SUBJECT_PRED, Literal("History")) in resource.graph
    assert (URIRef(EXAMPLE_URI), SUBJECT_PRED, Literal("Science")) in resource.graph
    assert (URIRef(EXAMPLE_URI), SUBJECT_PRED, Literal("Mathematics")) in resource.graph

def test_add_properties_list_in_dict():
    """Test het toevoegen van een lijst van waarden via de dictionary interface."""
    resource = RDFResource(EXAMPLE_URI)
    
    properties = {
        SUBJECT_PRED: ["History", "Science", "Mathematics"]
    }
    
    resource.add_properties(properties)

    # Controleer of alle subjects correct zijn toegevoegd
    assert (URIRef(EXAMPLE_URI), SUBJECT_PRED, Literal("History")) in resource.graph
    assert (URIRef(EXAMPLE_URI), SUBJECT_PRED, Literal("Science")) in resource.graph
    assert (URIRef(EXAMPLE_URI), SUBJECT_PRED, Literal("Mathematics")) in resource.graph
