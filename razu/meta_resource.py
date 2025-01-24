import os
from rdflib import URIRef, Literal, BNode
from typing import Callable, Any

from razu.incrementer import Incrementer
from razu.config import Config
from razu.identifiers import Identifiers
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, LDTO, DCT, PREMIS, XSD, SKOS
from razu.concept_resolver import ConceptResolver
import razu.util as util


class MetaResource(RDFResource):
    """
    An RDF Resource tailored in the context of an RAZU edepot SIP.
    Provides load(), save() and identifier logic.
    """
    _counter = Incrementer(0)
    _context = Config.get_instance()
    _id_factory = Identifiers(_context)

    def __init__(self, id: str | None = None):
        self.id = id if id else str(MetaResource._counter.next())
        uri = MetaResource._id_factory.make_uri_from_id(self.id)
        super().__init__(uri=uri)
        self.is_modified = True
        self.is_from_existing = False

    @property
    def uid(self) -> str:
        return MetaResource._id_factory.make_uid_from_id(self.id)

    @property
    def filename(self) -> str:
        return MetaResource._id_factory.make_filename_from_id(self.id)

    @property
    def file_path(self) -> str:
        return os.path.join(MetaResource._context.sip_directory, self.filename)
 
    def save(self) -> bool:
        if self.is_modified:
            try:
                with open(self.file_path, 'w', encoding='utf-8') as file:
                    file.write(self.graph.serialize(format='json-ld'))
                self.is_modified = False
                return True
            except IOError as e:
                print(f"Error saving file {self.file_path}: {e}")
        return False 

    def load(self) -> None:
        self.graph = MetaGraph()
        with open(self.file_path, 'r', encoding='utf-8') as file:
            self.graph.parse(data=file.read(), format="json-ld")
        self.is_modified = False
        self.is_from_existing = True


class StructuredMetaResource(MetaResource):
    """
    Provides RDF structure templates for filling MetaResource,
    and properties for easy access to key parts of the graph data.
    """

    _actoren = ConceptResolver("actor")
    _aggregatieniveaus = ConceptResolver("aggregatieniveau")
    _algoritmes = ConceptResolver("algoritme")
    _beperkingen_openbaarheid = ConceptResolver("openbaarheid")
    _bestandsformaten = ConceptResolver("bestandsformaat")
    _dekkingintijdtypen = ConceptResolver("dekkingintijdtype")
    _eventtypen = ConceptResolver("eventtype")
    _licenties = ConceptResolver("licentie")
    _waarderingen = ConceptResolver("waardering")

    def __init__(self, id: str | None = None, rdf_type=LDTO.Informatieobject):
        super().__init__(id)
        self._init_rdf_properties(rdf_type)
        self.based_on_sources = set()

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
    def description_uri(self) -> str:
        return f"{MetaResource._id_factory.cdn_base_uri}{self.uid}.{MetaResource._context.metadata_suffix}.{MetaResource._context.metadata_extension}"

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
        self.add_properties({LDTO.archiefvormer: MetaResource._context.archive_creator_uri})

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
                LDTO.dekkingInTijdBeginDatum: util.date_type(start_date),
                LDTO.dekkingInTijdEindDatum: util.date_type(end_date),
                LDTO.dekkingInTijdType: URIRef(StructuredMetaResource._dekkingintijdtypen.get_concept_uri("Van toepassing"))
            }
        })

    def set_event_with_actor(self, event_type: str, event_date: str, event_actor: str) -> None:
        self.add_properties({
            LDTO.event: {
                RDF.type: LDTO.EventGegevens,
                LDTO.eventType: URIRef(StructuredMetaResource._eventtypen.get_concept_uri(event_type)),
                LDTO.eventTijd: util.date_type(event_date),
                LDTO.eventVerantwoordelijkeActor: URIRef(StructuredMetaResource._actoren.get_concept_uri(event_actor))
            } 
        })

    def set_publication_date(self, publication_date: str) -> None:
        self.add_properties({
            LDTO.event: {
                RDF.type: LDTO.EventGegevens,
                LDTO.eventType: URIRef(StructuredMetaResource._eventtypen.get_concept_uri("Publicatie")),
                LDTO.eventTijd: util.date_type(publication_date)
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

    def set_fileproperties_by_puid(self, puid) -> None:
        ext_file_fileformat_uri = StructuredMetaResource._bestandsformaten.get_concept(puid).get_uri()
        file_extension = StructuredMetaResource._bestandsformaten.get_concept(puid).get_value(SKOS.notation)
        ext_filename = f"{self.uid}.{file_extension}"
        url = f"{MetaResource._id_factory.cdn_base_uri}{ext_filename}"
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
            LDTO.beperkingGebruik: {
                RDF.type: LDTO.BeperkingGebruikGegevens,  
                LDTO.beperkingGebruikType: StructuredMetaResource._beperkingen_openbaarheid.get_concept(beperking_term).get_uri()
            }
        })

    def set_license(self, license_term) -> None:
        self.add_properties({
            LDTO.beperkingGebruik: {
                RDF.type: LDTO.BeperkingGebruikGegevens,  
                LDTO.beperkingGebruikType: StructuredMetaResource._licenties.get_concept(license_term).get_uri()
            }
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
        return util.calculate_md5(os.path.join(MetaResource._context.sip_directory, self.referenced_file_filename)) == self.referenced_file_md5checksum

    def _init_rdf_properties(self, rdf_type) -> None:
        self.add_properties({
            RDF.type: rdf_type,
            LDTO.identificatie: {
                RDF.type: LDTO.IdentificatieGegevens,
                LDTO.identificatieBron: "e-Depot RAZU",
                LDTO.identificatieKenmerk: self.uri
            },
            DCT.hasFormat: URIRef(self.description_uri)
        })
        if rdf_type == LDTO.Informatieobject:
            self.add_properties({
                LDTO.waardering: StructuredMetaResource._waarderingen.get_concept('B').get_uri(),
                LDTO.archiefvormer: StructuredMetaResource._actoren.get_concept(MetaResource._context.archive_creator_id).get_uri()
            })
        self.add_triple(URIRef(self.description_uri), RDF.type, PREMIS.File)
