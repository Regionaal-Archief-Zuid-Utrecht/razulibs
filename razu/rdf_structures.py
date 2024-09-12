from rdflib import Graph, URIRef, Literal, BNode, RDF

class RDFBase:
    """
    An abstract class for working with RDF graphs.

    Attributes:
    -----------
    graph : rdflib.Graph
        The RDF graph that stores triples.

    Methods:
    --------
    add_properties(subject: URIRef, properties: dict) -> RDFBase
        Adds properties to a given RDF subject. Supports nested blank nodes and recursive structures.
    """

    def __init__(self, graph=None):
        """ Initializes the RDFBase class with an optional RDF graph.  
        If no graph is provided, a new one is created.
        """
        self.graph = graph if graph else Graph()

    def add_properties(self, subject: URIRef, properties: dict) -> "RDFBase":
        """
        Adds properties to the given subject in the RDF graph.

        Supports:
        - Lists: Adds multiple values for a property.
        - Dictionaries: Recursively adds nested blank nodes for structured data.
        - URIRefs, Literals, BNodes: These are added directly as property values.

        Parameters:
        -----------
        subject : URIRef
            The RDF subject to which properties will be added.
        properties : dict
            A dictionary where the keys are predicates (URIRefs) and the values are objects (URIRefs, Literals, BNodes, lists, or dictionaries).
        
        Returns:
        --------
        RDFBase
            The instance itself for method chaining.
        
        Raises:
        -------
        ValueError
            If a list item is not a valid RDF type (URIRef, Literal, BNode, or dictionary).
        """
        for prop, value in properties.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        nested_blank_node = BNode()
                        self.graph.add((subject, prop, nested_blank_node))
                        RDFBase.add_properties(self, nested_blank_node, item)
                    elif isinstance(item, (URIRef, Literal, BNode)):
                        self.graph.add((subject, prop, item))
                    else:
                        raise ValueError("List items must be URIRefs, Literals, BNodes, or dictionaries for blank nodes.")
            elif isinstance(value, dict):
                nested_blank_node = BNode()
                self.graph.add((subject, prop, nested_blank_node))
                RDFBase.add_properties(self, nested_blank_node, value)
            else:
                if not isinstance(value, (URIRef, Literal, BNode)):
                    value = Literal(value)
                self.graph.add((subject, prop, value))
        return self


class BlankNode(RDFBase):
    """ A class representing an RDF blank node. """
    def __init__(self, graph, node):
        """ Initializes a BlankNode with a given RDF graph and blank node. """
        super().__init__(graph)
        self.node = node

    def add_node(self, relation: URIRef, properties: dict = None) -> "BlankNode":
        """ Adds a blank node related to the current node and optionally adds properties to it. 
        Returns the BlankNode object for optional chaining.
        """
        blank_node = BNode()
        self.graph.add((self.node, relation, blank_node))
        if properties:
            self.add_properties(blank_node, properties)
        return BlankNode(self.graph, blank_node)


class Entity(RDFBase):
    """
    A class representing an RDF entity with a URI and type.

    Attributes:
    -----------
    uri : URIRef
        The URI of the entity.
    type : URIRef
        The RDF type of the entity.

    Methods:
    --------
    add(predicate: URIRef, object: URIRef)
        Adds a triple to the graph with the entity's URI as the subject.
    add_properties(properties: dict) -> RDFBase
        Adds properties to the entity.
    add_node(relation: URIRef, node_type: URIRef, properties: dict) -> BlankNode
        Adds a related blank node of a given type and adds properties to it.
    add_properties_list(list: str, separator: str, property: URIRef, transform_function: callable)
        Splits a string into a list of items, transforms them, and adds them as properties.
    __iter__() -> iterator
        Allows iterating over the RDF graph.
    __iadd__(other_graph: Graph) -> Graph
        Adds another graph's triples to the current graph.
    """

    def __init__(self, uri: URIRef, type: URIRef):
        """ Initializes an Entity with a given URI and RDF type. """
        super().__init__()
        self.uri = uri   
        self.type = type
        self.graph.add((self.uri, RDF.type, self.type))

    def add(self, predicate: URIRef, object: URIRef):
        """ Adds a triple to the graph with the entity's URI as the subject. """
        self.graph.add((self.uri, predicate, object))

    def add_properties(self, properties: dict) -> "Entity":
        """ Adds properties to the entity's URI. 
        Returns the Entity object for optional chaining.
        """
        return super().add_properties(self.uri, properties)

    def add_node(self, relation: URIRef, node_type: URIRef, properties: dict) -> BlankNode:
        """
        Adds a related blank node of a specified type to the entity and assigns properties to it.

        Parameters:
        -----------
        relation : URIRef
            The relation (predicate) connecting the entity and the new blank node.
        node_type : URIRef
            The RDF type of the new blank node.
        properties : dict
            A dictionary of properties to add to the new blank node.

        Returns:
        --------
        BlankNode
            A new BlankNode instance for the created blank node.
        """
        blank_node = BNode()
        self.graph.add((self.uri, relation, blank_node))
        self.graph.add((blank_node, RDF.type, node_type))
        RDFBase.add_properties(self, blank_node, properties)
        return BlankNode(self.graph, blank_node)

    def add_properties_list(self, list: str, separator: str, property: URIRef, transform_function: callable):
        """
        Splits a string into a list of items, transforms them, and adds them as properties to the entity.

        Parameters:
        -----------
        list : str
            The string containing items to be split and transformed.
        separator : str
            The separator used to split the string into items.
        property : URIRef
            The predicate to use for the transformed items.
        transform_function : callable
            A function to transform each item from the split string.
        """
        if isinstance(list, str) and list:
            elements = list.split(separator)
            for part in elements:
                value = transform_function(part)
                self.add_properties({
                    property: value
                })

    def __iter__(self):
        """ Returns an iterator over the RDF graph. """
        return iter(self.graph)
    
    def __iadd__(self, other_graph: Graph) -> Graph:
        """ Adds another RDF graph's triples to this entity's graph. """
        other_graph += self.graph
        return other_graph
