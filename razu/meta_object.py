import os
from rdflib import Namespace, URIRef, Literal, RDF, XSD, SKOS
from .incrementer import Incrementer
from .razuconfig import RazuConfig
from .rdf_structures import Entity
from .concept_resolver import ConceptResolver

# Namespaces for RDF properties
SCHEMA = Namespace("http://schema.org/")
MDTO = Namespace("http://www.nationaalarchief.nl/mdto#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PREMIS = Namespace("http://www.loc.gov/premis/rdf/v3/")


class MetaObject(Entity):
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
            self.id = MetaObject._counter.next()
        else:
            self.id = entity_id
        uri = URIRef(f"{MetaObject._config.URI_prefix}-{self.id}")
        super().__init__(uri, rdf_type)
        
        self.algoritmes = ConceptResolver("algoritme")
        self.bestandsformaten = ConceptResolver("bestandsformaat")

        self.object_identifier = f"{self._config.filename_prefix}-{self.id}"
        self.add_properties({
            RDF.type: PREMIS.Object,
            MDTO.identificatie: {
                RDF.type: MDTO.IdentificatieGegevens,
                MDTO.identificatieBron: "e-Depot RAZU",
                MDTO.identificatieKenmerk: f"{self._config.filename_prefix}-{self.id}" 
            }
        })
    
    def set_md5_properties(self, md5checksum, checksum_datetime):
        self.md5checksum = md5checksum
        self.checksum_datetime = checksum_datetime
        self.add_properties({
            MDTO.checksum: { 
                RDF.type: MDTO.ChecksumGegevens, 
                MDTO.checksumAlgoritme: self.algoritmes.get_concept("MD5").get_uri(),
                MDTO.checksumDatum: Literal(self.checksum_datetime, datatype=XSD.dateTime),
                MDTO.checksumWaarde: self.md5checksum  
            }
        })

    def set_fileproperties_by_puid(self, puid):
        self.puid = puid
        self.fileformat_uri = self.bestandsformaten.get_concept(self.puid).get_uri()
        self.file_extension = self.bestandsformaten.get_concept(self.puid).get_value(SKOS.notation)
        self.filename = f"{self.object_identifier}.{self.file_extension}"


        self.url = f"https://{MetaObject._config.archive_creator_id.lower()}.opslag.razu.nl/{self.filename}"
        self.add_properties({
            MDTO.bestandsformaat: self.fileformat_uri,
            MDTO.URLBestand: Literal(f"{self.url}", datatype=XSD.anyURI),
        })

    def set_filesize(self, size: int):
        self.filesize = size
        self.add_properties({
            MDTO.omvang: Literal(self.filesize, datatype=XSD.integer)
        })

    def set_original_filename(self, filename:str):
        self.original_filename = filename
        self.add_properties({
            PREMIS.originalName: self.original_filename
        })


    def save(self) -> None:
        """
        Serializes the RDF graph of the MDTOObject and saves it as a JSON-LD file.
        If saving is disabled in the configuration, this method does nothing.
        
        The file is saved in the directory specified by the configuration, and the filename
        is constructed from the filename prefix and the object's ID.

        """
        if self._config.save:
            try:
                save_dir = self._config.save_dir
            except:
                save_dir = "sip"
            self.meta_filename = f"{self._config.filename_prefix}-{self.id}.{self._config.metadata_suffix}.json"
            self.meta_file_path = os.path.join(save_dir, self.meta_filename)
            with open(self.meta_file_path, 'w') as file:
                file.write(self.graph.serialize(format='json-ld'))
