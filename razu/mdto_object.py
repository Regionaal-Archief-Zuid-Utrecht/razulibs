import os
from rdflib import Namespace, URIRef
from .incrementer import Incrementer
from .razuconfig import RazuConfig
from .rdf_structures import Entity

# Namespaces for RDF properties
SCHEMA = Namespace("http://schema.org/")
MDTO = Namespace("http://www.nationaalarchief.nl/mdto#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")


class MDTOObject(Entity):
    """
    A class representing an MDTO (Metadata Transport Object) within an RDF graph.

    Inherits from the `Entity` class and represents a specific RDF entity based on the
    Nationaal Archief's MDTO schema.

    Attributes:
    -----------
    _counter : Incrementer
        A class-level counter used to generate unique IDs for MDTOObjects.
    _config : RazuConfig
        Configuration for saving and identifying MDTOObjects, such as URIs and file prefixes.
    id : int or str
        A unique identifier for the MDTOObject, either provided or auto-incremented.
    uri : URIRef
        The URI of the MDTOObject in the RDF graph.
    type : URIRef
        The RDF type of the MDTOObject (default is MDTO.Informatieobject).

    Methods:
    --------
    mdto_identificatiekenmerk() -> str
        Returns a string identifier for the MDTOObject based on the configuration settings.
    
    save() -> None
        Serializes and saves the MDTOObject's RDF graph as a JSON-LD file.
    """
    
    _counter = Incrementer(0)
    _config = RazuConfig()

    def __init__(self, rdf_type: URIRef = MDTO.Informatieobject, entity_id: int = None):
        """
        Initializes the MDTOObject with a given RDF type and optional ID.

        If no ID is provided, a new ID is auto-incremented using the `_counter` attribute.
        The URI of the MDTOObject is constructed based on the configuration settings.

        Parameters:
        -----------
        type : URIRef, optional
            The RDF type of the MDTOObject (default is MDTO.Informatieobject).
        entity_id : int, optional
            An optional unique identifier for the MDTOObject. If not provided, an ID is generated.
        """
        if entity_id is None:
            self.id = MDTOObject._counter.next()
        else:
            self.id = entity_id
        uri = URIRef(f"{MDTOObject._config.URI_prefix}{self.id}")
        super().__init__(uri, rdf_type)

    def mdto_identificatiekenmerk(self) -> str:
        """
        Returns the unique identifier for the MDTOObject based on the configuration.
        The identifier combines the filename prefix from the configuration with the object's ID.
        """
        return f"{self._config.filename_prefix}{self.id}"

    def save(self) -> None:
        """
        Serializes the RDF graph of the MDTOObject and saves it as a JSON-LD file.
        If saving is disabled in the configuration, this method does nothing.
        
        The file is saved in the directory specified by the configuration, and the filename
        is constructed from the filename prefix and the object's ID.

        """
        if self._config.save:
            output_file = os.path.join(self._config.save_dir, f"{self._config.filename_prefix}{self.id}.meta.json")
            with open(output_file, 'w') as file:
                file.write(self.graph.serialize(format='json-ld'))
