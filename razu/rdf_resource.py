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

        :param uri: A URI string for the resource. If None, a blank node is created.
        """
        if uri:
            self.uri = URIRef(uri)
        else:
            self.uri = BNode()
        self.graph = Graph()

    def add(self, predicate: URIRef, obj, transformer: callable = Literal):
        """
        Adds a triple to the graph where the subject is the current RDFResource,
        the predicate is provided, and the object is transformed using the given transformer.

        :param predicate: The URIRef representing the predicate of the triple.
        :param obj: The object of the triple, which can be another RDFResource, a URIRef, or any value
                    to be converted into a Literal.
        :param transformer: A callable that transforms the object into a suitable type for RDF (default: Literal).
        """
        if isinstance(obj, RDFResource):
            self.graph.add((self.uri, predicate, obj.uri))
            self.graph += obj.graph  # Merges the graph of the nested RDFResource
        elif isinstance(obj, URIRef):
            self.graph.add((self.uri, predicate, obj))
        else:
            self.graph.add((self.uri, predicate, transformer(obj)))

    def add_list_from_string(self, predicate: URIRef, item_list: str, separator: str, transformer: callable = Literal):
        """
        Adds multiple triples to the graph based on a string of items separated by a specified separator.

        :param predicate: The URIRef representing the predicate of each triple.
        :param item_list: A string containing multiple items separated by the given separator.
        :param separator: The separator used to split the string into individual items.
        :param transformer: A callable that transforms each item into a suitable type for RDF (default: Literal).
        """
        if isinstance(item_list, str) and item_list:
            elements = item_list.split(separator)
            for part in elements:
                self.add(predicate, transformer(part))

    def add_properties(self, rdf_properties: dict):
        """
        Adds multiple properties to the RDFResource from a dictionary.
        This method handles nested dictionaries and lists to create complex structures.

        :param rdf_properties: A dictionary where keys are predicates (URIRefs) and values
                               are objects, which can be RDFResource instances, URIRefs, lists, or dictionaries.
        """
        for predicate, obj in rdf_properties.items():
            if isinstance(obj, dict):
                nested_entity = RDFResource()  # Create a new RDFResource for the nested structure
                nested_entity.add_properties(obj)  # Recursively add the properties
                self.add(predicate, nested_entity)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        nested_entity = RDFResource()
                        nested_entity.add_properties(item)
                        self.add(predicate, nested_entity)
                    elif isinstance(item, URIRef):
                        self.graph.add((self.uri, predicate, item))
                    else:
                        self.graph.add((self.uri, predicate, Literal(item)))
            else:
                self.add(predicate, obj)

    def __iter__(self):
        """ Returns an iterator over the RDF graph. This allows iteration over all triples in the graph. """
        return iter(self.graph)

    def __iadd__(self, other_graph: Graph) -> Graph:
        """ In-place addition of another RDF graph's triples to this RDFResource's graph. """
        self.graph += other_graph
        return self.graph
