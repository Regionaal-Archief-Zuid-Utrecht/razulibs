import os
from rdflib import URIRef, Literal, BNode
from typing import Callable, Any

from razu.config import Config
# from razu.identifiers import Identifiers # change with integration of identifiers service also I deleted the Incrementer import
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, LDTO, DCT, RAZU, XSD, BAG, SCHEMA, GEO, RDFS, OWL, PICO, PNV, SKOS, PREMIS, PROV
from razu.concept_resolver import ConceptBuilder
import razu.utils as utils


class MetaResource(RDFResource):
    """
    An RDF Resource tailored in the context of an RAZU edepot SIP.
    Provides load(), save() and identifier logic.
    """
    # _counter = Incrementer(0)
    # _id_factory = Identifiers(_context) 

    def __init__(self, id: str | None = None, uri: str | None = None):
        # OLD CODE (before removing Identifiers dependency):
        # if uri:
        #     self.id = id
        #     super().__init__(uri=uri)
        # else:
        #     self.id = id if id else str(MetaResource._counter.next())
        #     uri = MetaResource._id_factory.make_uri_from_id(self.id)
        #     super().__init__(uri=uri)
        
        # NEW CODE: Requires both id and uri to be passed explicitly
        if not uri:
            raise ValueError("MetaResource requires both 'id' and 'uri' to be provided")
        self.id = id
        super().__init__(uri=uri)
        self.graph = MetaGraph()
        self.is_modified = True
        self.is_from_existing = False

    @property
    def filename(self) -> str:
        """Default filename implementation - should be overridden in subclasses."""
        # OLD CODE: return MetaResource._id_factory.make_filename_from_id(self.id)
        # NEW CODE: Use self.id directly with config suffixes
        cfg = Config.get_instance()
        return f"{self.id}.{cfg.metadata_suffix}.{cfg.metadata_extension}"

    @property
    def local_file_path(self) -> str:
        return os.path.join(Config.get_instance().sip_directory, self.filename)

    # OLD CODE (removed methods that used _id_factory):
    # @property
    # def uid(self) -> str:
    #     return MetaResource._id_factory.make_uid_from_id(self.id)
    #
    # def filestore_key(self) -> str:
    #     return self._id_factory.make_s3_key_from_id(self.id)
 
    def save(self) -> bool:
        if self.is_modified:
            try:
                with open(self.local_file_path, 'w', encoding='utf-8') as file:
                    file.write(self.graph.serialize(format='json-ld'))
                self.is_modified = False
                return True
            except IOError as e:
                print(f"Error saving file {self.local_file_path}: {e}")
        return False 

    def load(self) -> None:
        self.graph = MetaGraph()
        with open(self.local_file_path, 'r', encoding='utf-8') as file:
            self.graph.parse(data=file.read(), format="json-ld")
        self.is_modified = False
        self.is_from_existing = True


class StructuredMetaResource(MetaResource):
    """
    Provides RDF structure templates for filling MetaResource,
    and properties for easy access to key parts of the graph data.
    """

    _actoren = ConceptBuilder("actor")
    _aggregatieniveaus = ConceptBuilder("aggregatieniveau")
    _algoritmes = ConceptBuilder("algoritme")
    _beperkingen_openbaarheid = ConceptBuilder("openbaarheid")
    _bestandsformaten = ConceptBuilder("bestandsformaat")
    _dekkingintijdtypen = ConceptBuilder("dekkingintijdtype")
    _eventtypen = ConceptBuilder("eventtype")
    _licenties = ConceptBuilder("licentie")
    _waarderingen = ConceptBuilder("waardering")

    def __init__(self, id: str | None = None, uri: str | None = None):
        super().__init__(id, uri=uri)
        # self._init_rdf_properties(rdf_type) changed
        self.based_on_sources = set()

    @property
    def filename(self) -> str:
        """Override parent's filename to use self.id directly without factory call chain."""
        # This override ensures we use self.id directly (same as parent now, but kept for clarity)
        cfg = Config.get_instance()
        return f"{self.id}.{cfg.metadata_suffix}.{cfg.metadata_extension}"

    def add(self, predicate: URIRef, obj, transformer: Callable = Literal) -> None:
        """Add a triple to the graph and mark as modified."""
        super().add_property(predicate, obj, transformer)
        self.is_modified = True
    
    def add_properties(self, rdf_properties: dict) -> None:
        """Add properties to the graph and mark as modified."""
        super().add_properties(rdf_properties)
        self.is_modified = True

    def add_list_from_string(self, predicate: URIRef, item_list: str, separator: str, transformer: Callable = Literal) -> None:
        """Add a list of values from a string and mark as modified."""
        super().add_properties_from_string(predicate, item_list, separator, transformer)
        self.is_modified = True

    @property
    def is_based_on_sources(self) -> bool:
        return bool(self.based_on_sources)

    @property
    def has_referenced_file(self) -> bool:
        return self._get_object_value(LDTO.URLBestand, self.uri) is not None


    @property
    def referenced_file_uri(self) -> str | None:
        value = self._get_object_value(LDTO.URLBestand, self.uri)
        return value if value is not None else None
    
    @property
    def referenced_file_filename(self) -> str:
        return os.path.basename(str(self.referenced_file_uri))

    @property
    def referenced_file_original_filename(self) -> str:
        return str(self._get_object_value(PREMIS.originalName, URIRef(self.referenced_file_uri)))

    @property
    def referenced_file_md5checksum(self) -> str:
        return str(self._get_object_value(LDTO.checksumWaarde))

    @property
    def referenced_file_checksum_datetime(self) -> str:
        return str(self._get_object_value(LDTO.checksumDatum))

    @property
    def reference_file_fileformat(self) -> str:
        return str(self._get_object_value(LDTO.bestandsformaat, self.uri))
    
    def set_type(self, rdf_type: URIRef) -> None:   
        self.add_properties({RDF.type: rdf_type})

    def set_archive_creator(self) -> None:
        self.add_properties({LDTO.archiefvormer: Config.get_instance().archive_creator_uri})

    def set_name(self, name: str) -> None:
        self.add_properties({LDTO.naam: name})

    def set_classification(self, classification_uri: URIRef) -> None:
        self.add_properties({LDTO.classificatie: classification_uri})

    def set_keywords(self, keywords: str, separator: str = ";") -> None:
        self.add_list_from_string(LDTO.trefwoord, keywords, separator)

    def set_applicable_period(self, start_date: str, end_date: str) -> None:
        self.add_properties({
            LDTO.dekkingInTijd: { 
                RDF.type: LDTO.DekkingInTijdGegevens,
                LDTO.dekkingInTijdBeginDatum: utils.date_type(start_date),
                LDTO.dekkingInTijdEindDatum: utils.date_type(end_date),
                LDTO.dekkingInTijdType: URIRef(StructuredMetaResource._dekkingintijdtypen.get_concept_uri("Van toepassing"))
            }
        })

    def set_event_with_actor(self, event_type: str, event_date: str, event_actor: str) -> None:
        self.add_properties({
            LDTO.event: {
                RDF.type: LDTO.EventGegevens,
                LDTO.eventType: URIRef(StructuredMetaResource._eventtypen.get_concept_uri(event_type)),
                LDTO.eventTijd: utils.date_type(event_date),
                LDTO.eventVerantwoordelijkeActor: URIRef(StructuredMetaResource._actoren.get_concept_uri(event_actor))
            } 
        })

    def set_publication_date(self, publication_date: str) -> None:
        self.add_properties({
            LDTO.event: {
                RDF.type: LDTO.EventGegevens,
                LDTO.eventType: URIRef(StructuredMetaResource._eventtypen.get_concept_uri("Publicatie")),
                LDTO.eventTijd: utils.date_type(publication_date)
            } 
        })

    def set_md5_properties(self, md5checksum, checksum_datetime) -> None:
        self.add_properties({
            LDTO.checksum: {
                RDF.type: LDTO.ChecksumGegevens,
                LDTO.checksumAlgoritme: StructuredMetaResource._algoritmes.get_concept("MD5").get_uri(),
                LDTO.checksumDatum: Literal(checksum_datetime, datatype=XSD.dateTime),
                LDTO.checksumWaarde: md5checksum
            }
        })

    def set_fileproperties_by_puid(self, puid, cdn_base_uri: str) -> None:
        """Set file properties by PUID. Requires cdn_base_uri to be passed in."""
        # OLD CODE: Used self.uid and MetaResource._id_factory.cdn_base_uri
        # ext_filename = f"{self.uid}.{file_extension}"
        # url = f"{MetaResource._id_factory.cdn_base_uri}{ext_filename}"
        # NEW CODE: Use self.id and accept cdn_base_uri as parameter
        ext_file_fileformat_uri = StructuredMetaResource._bestandsformaten.get_concept(puid).get_uri()
        file_extension = StructuredMetaResource._bestandsformaten.get_concept(puid).get_value(SKOS.notation)
        ext_filename = f"{self.id}.{file_extension}"
        url = f"{cdn_base_uri}{ext_filename}"
        self.add_properties({
            LDTO.bestandsformaat: ext_file_fileformat_uri,
            LDTO.URLBestand: Literal(url, datatype=XSD.anyURI),
        })
        self.add_triple(URIRef(url), RDF.type, PREMIS.File)

    def set_filesize(self, filesize: int) -> None:
        self.add_properties({LDTO.omvang: Literal(filesize, datatype=XSD.integer)})

    def set_original_filename(self, ext_file_original_filename: str) -> None:
        self.add_triple(URIRef(self.referenced_file_uri), PREMIS.originalName, Literal(ext_file_original_filename))

    def set_aggregation_level(self, aggregation_term) -> None:
        self.add_properties({LDTO.aggregatieniveau: StructuredMetaResource._aggregatieniveaus.get_concept(aggregation_term).get_uri()})

    def set_restrictions_public_availability(self, beperking_term) -> None:
        self.add_properties({
            LDTO.beperkingGebruik: StructuredMetaResource._beperkingen_openbaarheid.get_concept(beperking_term).get_uri()
        })

    def set_license(self, license_term) -> None:
        self.add_properties({
            LDTO.beperkingGebruik: StructuredMetaResource._licenties.get_concept(license_term).get_uri()
        })

    def add_based_on_source(self, source) -> None:
        self.based_on_sources.add(source)

    def _get_object_value(self, predicate, subject=None) -> Any:
        if subject is not None:
            for s, p, o in self.graph.triples((subject, predicate, None)):
                return o
        else:
            for s, p, o in self.graph.triples((None, predicate, None)):
                if isinstance(s, BNode):
                    return o
        return None

    def validate_referenced_file_md5checksum(self) -> bool:
        return utils.calculate_md5(os.path.join(Config.get_instance().sip_directory, self.referenced_file_filename)) == self.referenced_file_md5checksum

