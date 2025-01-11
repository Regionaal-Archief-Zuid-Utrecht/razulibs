from rdflib import Graph, URIRef, Literal, BNode


class RDFResource:
    """
    RDFResource represents an RDF node (either a URIRef or a BlankNode) along with its associated graph.
    It provides methods to add properties, handle nested data, and combine graphs.
    """

    def __init__(self, uri: str = None):
        """
        Initializes an RDFResource. If a URI is provided, it is used as the subject for the RDFResource;
        otherwise, a blank node is created.
        """
        if uri:
            self.uri = URIRef(uri)
        else:
            self.uri = BNode()
        self.graph = Graph()

    def __iter__(self):
        """ Returns an iterator over the RDF graph, allows iteration over all triples in the graph. """
        return iter(self.graph)

    def __iadd__(self, other_graph: Graph) -> Graph:
        """ In-place addition of another RDF graph's triples to this RDFResource's graph. """
        self.graph += other_graph
        return self.graph

    def add_triple(self, subject: URIRef, predicate: URIRef, object) -> None:
        self.graph.add((subject, predicate, object))

    def add_property(self, predicate: URIRef, object, object_transformer: callable = Literal):
        """
        Adds a triple to the graph where the subject is the current RDFResource,
        the object is transformed using the given transformer.
        """
        if isinstance(object, RDFResource):
            self.add_triple(self.uri, predicate, object.uri)
            self.graph += object.graph
        elif isinstance(object, URIRef):
            self.add_triple(self.uri, predicate, object)
        else:
            self.add_triple(self.uri, predicate, object_transformer(object))

    def add_properties(self, rdf_properties: dict):
        """
        Adds multiple properties to the RDFResource from a dictionary.
        This method handles nested dictionaries and lists to create complex structures.

        :param rdf_properties: A dictionary where keys are predicates (URIRefs) and values
                               are objects, which can be RDFResource instances, URIRefs, lists, or dictionaries.
        """
        for predicate, obj in rdf_properties.items():
            if isinstance(obj, dict):
                nested_entity = RDFResource()
                nested_entity.add_properties(obj)
                self.add_property(predicate, nested_entity)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        nested_entity = RDFResource()
                        nested_entity.add_properties(item)
                        self.add_property(predicate, nested_entity)
                    elif isinstance(item, URIRef):
                        self.add_triple(self.uri, predicate, item)
                    else:
                        self.add_triple(self.uri, predicate, Literal(item))
            else:
                self.add_property(predicate, obj)

    def add_properties_from_string(self, predicate: URIRef, objects: str, separator: str, object_transformer: callable = Literal):
        """Adds multiple triples to the graph based on a string of objects separated by a specified separator character."""
        if isinstance(objects, str) and objects:
            elements = objects.split(separator)
            for object_part in elements:
                self.add_property(predicate, object_part, object_transformer)