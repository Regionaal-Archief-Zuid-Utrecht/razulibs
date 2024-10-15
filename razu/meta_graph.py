from rdflib import Graph, RDF, RDFS
from razu.meta_object import MDTO, SCHEMA, GEO, PREMIS

class MetaGraph(Graph):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind("rdf", RDF)
        self.bind("rdfs", RDFS)
        self.bind("mdto", MDTO)
        self.bind("schema", SCHEMA)
        self.bind("geo", GEO)
        self.bind("premis", PREMIS)