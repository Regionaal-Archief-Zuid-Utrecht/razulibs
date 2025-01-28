from rdflib import Graph, Namespace, RDF, RDFS, XSD, SKOS, OWL

# Namespaces for RDF properties
MDTO = Namespace("http://www.nationaalarchief.nl/mdto#")
LDTO = Namespace("https://data.razu.nl/def/ldto/")
SCHEMA = Namespace("http://schema.org/")
DCT = Namespace("http://purl.org/dc/terms/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PREMIS = Namespace("http://www.loc.gov/premis/rdf/v3/")
PROV = Namespace("http://www.w3.org/ns/prov#")
EROR = Namespace("http://id.loc.gov/vocabulary/preservation/eventRelatedObjectRole/")
ERAR = Namespace("http://id.loc.gov/vocabulary/preservation/eventRelatedAgentRole/")
EO = Namespace("http://id.loc.gov/vocabulary/preservation/eventOutcome/")


class MetaGraph(Graph):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind("ldto", LDTO)
        self.bind("mdto", MDTO)
        self.bind("schema", SCHEMA)
        self.bind("dct", DCT)
        self.bind("geo", GEO)
        self.bind("premis", PREMIS)
        self.bind("prov", PROV)
        self.bind("eror", EROR)
        self.bind("erar", ERAR)
        self.bind("eo", EO)
        self.bind("owl", OWL)
        