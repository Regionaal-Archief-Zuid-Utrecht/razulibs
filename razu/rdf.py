
import os
from rdflib import Graph, Namespace, URIRef, Literal, BNode, RDF, RDFS, XSD

from .incrementer import Incrementer
from .config import Config

## ACHTERHAALD, zie libs in  /mnt/f/python/razulibs/razu/
##              script /mnt/f/python/luchtfotos_houten/csv2rdf.py 

MDTO = Namespace("http://www.nationaalarchief.nl/mdto#")


class RDFBase:
    def __init__(self, graph=None):
        self.graph = graph if graph else Graph()

    def add_properties(self, subject: URIRef, properties: dict):
        for prop, value in properties.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        nested_blank_node = BNode()
                        self.graph.add((subject, prop, nested_blank_node))
                        # Ensure recursive call refers directly to RDFBase method:
                        RDFBase.add_properties(self, nested_blank_node, item)
                    else:
                        raise ValueError("List items must be dictionaries to represent blank nodes.")
            elif isinstance(value, dict):
                nested_blank_node = BNode()
                self.graph.add((subject, prop, nested_blank_node))
                # Ensure recursive call refers directly to RDFBase method:
                RDFBase.add_properties(self, nested_blank_node, value)
            else:
                if not isinstance(value, (URIRef, Literal, BNode)):
                    value = Literal(value)
                self.graph.add((subject, prop, value))
        return self


class Entity(RDFBase):
    def __init__(self, uri: URIRef, type: URIRef):
        super().__init__()
        self.uri = uri   
        self.type = type
        self.graph.add((self.uri, RDF.type, self.type))

    def add(self, predicate, object):
        self.graph.add((self.uri, predicate, object))

    def add_properties(self, properties: dict):
        return super().add_properties(self.uri, properties)

    def add_node(self, relation: URIRef, node_type: URIRef, properties: dict):
        blank_node = BNode()
        self.graph.add((self.uri, relation, blank_node))
        self.graph.add((blank_node, RDF.type, node_type))
        RDFBase.add_properties(self, blank_node, properties)
        return BlankNode(self.graph, blank_node)
    
    def __iter__(self):
        return iter(self.graph)
    
    def __iadd__(self, other_graph: Graph):
        other_graph += self.graph
        return other_graph


class MDTO_Object(Entity):
    _counter = Incrementer(1)
    _config = Config()

    def __init__(self, type: URIRef = MDTO.Informatieobject, id = None):
        if id is None:
            self.id = MDTO_Object._counter.next()
        else:
            self.id = id
        uri = URIRef(f"{MDTO_Object._config.URI_prefix}-{self.id}")
        super().__init__(uri, type)

    def MDTO_identificatieKenmerk(self):
        return f"{self._config.filename_prefix}-{self.id}"

    def save(self):
        if self._config.save == True:
            output_file = os.path.join(self._config.save_dir, f"{self._config.filename_prefix}-{self.id}.mdto.json")
            with open(output_file, 'w') as file:
                file.write(self.graph.serialize(format='json-ld'))
