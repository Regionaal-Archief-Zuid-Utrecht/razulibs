from rdflib import Graph, Namespace, RDF, RDFS, XSD, SKOS

# Namespaces for RDF properties
SCHEMA = Namespace("http://schema.org/")
MDTO = Namespace("http://www.nationaalarchief.nl/mdto#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PREMIS = Namespace("http://www.loc.gov/premis/rdf/v3/")


class MetaGraph(Graph):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind("mdto", MDTO)
        self.bind("schema", SCHEMA)
        self.bind("geo", GEO)
        self.bind("premis", PREMIS)
        