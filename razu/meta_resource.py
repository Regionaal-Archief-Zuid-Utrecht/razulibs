import os
from rdflib import URIRef, Literal, BNode

from typing import Callable

from razu.incrementer import Incrementer
from razu.razuconfig import RazuConfig
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, MDTO, DCT, PREMIS, XSD, SKOS
from razu.concept_resolver import ConceptResolver
import razu.util as util


class MetaResource(RDFResource):
    """
    An RDF Resource tailored for use in the RAZU edepot SIPs.

    Provides load(), save() and identifier (uri, uid & id)-logic.
    """
    _config = RazuConfig()
    _counter = Incrementer(0)

    def __init__(self, id=None, uid=None, uri=None):
        self.id, self.uid, uri = self._construct_identifiers(id, uid, uri)
        super().__init__(uri)
        self.filename = self._construct_filename()
        self.file_path = os.path.join(self._config.save_directory, self.filename)
        self.is_modified = False

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

    def _construct_identifiers(self, id=None, uid=None, uri=None):
        # uri takes precedence!
        if uri is not None:
            id = util.extract_id_from_file_path(uri)
            uid = self._construct_uid(id)
        elif uid is not None:
            id = util.extract_id_from_file_path(uid)
            uri = self._construct_uri(id)
        else:
            id = MetaResource._counter.next() if id is None else id
            uid = self._construct_uid(id)
            uri = self._construct_uri(id)
        return id, uid, URIRef(uri)

    def _construct_filename(self):
        return f"{self._config.filename_prefix}-{self.id}.{self._config.metadata_suffix}.json"

    def _construct_uri(self, id) -> str:
        return f"{MetaResource._config.object_uri_prefix}-{id}"

    def _construct_uid(self, id) -> str:
        return f"{MetaResource._config.filename_prefix}-{id}"


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

    def __init__(self, id=None, rdf_type=None):
        super().__init__(id)

        if rdf_type is None:
            rdf_type = MDTO.Informatieobject
        self.add_properties({
            RDF.type: rdf_type,
            MDTO.identificatie: {
                RDF.type: MDTO.IdentificatieGegevens,
                MDTO.identificatieBron: "e-Depot RAZU",
                MDTO.identificatieKenmerk: self.uid
            },
            MDTO.waardering: StructuredMetaResource._waarderingen.get_concept('B').get_uri(),
            MDTO.archiefvormer: StructuredMetaResource._actoren.get_concept(MetaResource._config.archive_creator_id).get_uri(),
            DCT.hasFormat: URIRef(self.this_file_uri)
        })
        self.graph.add((URIRef(self.this_file_uri), RDF.type, PREMIS.File))
        self.metadata_sources = set()
        self.is_modified = True

    @property
    def has_ext_file(self):
        return self._get_object_value(MDTO.URLBestand, self.uri) is not None

    @property
    def this_file_uri(self):
        return f"{MetaResource._config.cdn_base_uri}{self.uid}.{MetaResource._config.metadata_suffix}.{MetaResource._config.metadata_extension}"

    @property
    def ext_file_uri(self):
        value = self._get_object_value(MDTO.URLBestand, self.uri)
        return value if value is not None else None
    
    @property
    def ext_filename(self):
        return os.path.basename(str(self.ext_file_uri))

    @property
    def ext_file_original_filename(self):
        return str(self._get_object_value(PREMIS.originalName, URIRef(self.ext_file_uri)))

    @property
    def ext_file_md5checksum(self):
        return str(self._get_object_value(MDTO.checksumWaarde))

    @property
    def ext_file_checksum_datetime(self):
        return str(self._get_object_value(MDTO.checksumDatum))

    @property
    def ext_file_fileformat_uri(self):
        return str(self._get_object_value(MDTO.bestandsformaat, self.uri))
    
    def add(self, predicate: URIRef, obj, transformer: Callable = Literal):
        super().add(predicate, obj, transformer)
        self.is_modified = True
    
    def add_properties(self, rdf_properties: dict):
        super().add_properties(rdf_properties)
        self.is_modified = True

    def add_list_from_string(self, predicate: URIRef, item_list: str, separator: str, transformer: Callable = Literal):
        super().add_list_from_string(predicate, item_list, separator, transformer)
        self.is_modified = True

    def validate_md5(self):
        return util.calculate_md5(os.path.join(self._config.save_directory, self.ext_filename)) == self.ext_file_md5checksum

    def set_type(self, rdf_type: URIRef):
        self.add_properties({RDF.type: rdf_type})
        self.is_modified = True
        
    def set_name(self, name: str):
        self.add_properties( {
            MDTO.naam: name
        })
        self.is_modified = True

    def set_classification(self, classification_uri: URIRef):
        self.add_properties({MDTO.classificatie: classification_uri})
        self.is_modified = True

    def set_keywords(self, keywords: str, separator: str = ";"):
        self.add_list_from_string(MDTO.trefwoord, keywords, separator)
        self.is_modified = True

    def set_applicable_period(self, start_date: str, end_date: str):
        self.add_properties({
            MDTO.dekkingInTijd: { 
                RDF.type: MDTO.DekkingInTijdGegevens,
                MDTO.dekkingInTijdBeginDatum: util.date_type(start_date),
                MDTO.dekkingInTijdEindDatum: util.date_type(end_date),
                MDTO.dekkingInTijdType: URIRef(StructuredMetaResource._dekkingintijdtypen.get_concept_uri("Van toepassing"))
            }
        })
        self.is_modified = True

    def set_event_with_actor(self, event_type: str, event_date: str, event_actor: str):
        self.add_properties({
            MDTO.event: {
                RDF.type: MDTO.EventGegevens,
                MDTO.eventType: URIRef(StructuredMetaResource._eventtypen.get_concept_uri(event_type)),
                MDTO.eventTijd: util.date_type(event_date),
                MDTO.eventActor: URIRef(StructuredMetaResource._actoren.get_concept_uri(event_actor))
            } 
        })
        self.is_modified = True

    def set_publication_date(self, publication_date: str):
        self.add_properties({
            MDTO.event: {
                RDF.type: MDTO.EventGegevens,
                MDTO.eventType: URIRef(StructuredMetaResource._eventtypen.get_concept_uri("Publicatie")),
                MDTO.eventTijd: util.date_type(publication_date)
            } 
        })
        self.is_modified = True

    def set_md5_properties(self, md5checksum, checksum_datetime):
        self.add_properties({
            MDTO.checksum: {
                RDF.type: MDTO.ChecksumGegevens,
                MDTO.checksumAlgoritme: StructuredMetaResource._algoritmes.get_concept("MD5").get_uri(),
                MDTO.checksumDatum: Literal(checksum_datetime, datatype=XSD.dateTime),
                MDTO.checksumWaarde: md5checksum
            }
        })
        self.is_modified = True

    def set_fileproperties_by_puid(self, puid):
        ext_file_fileformat_uri = StructuredMetaResource._bestandsformaten.get_concept(puid).get_uri()
        file_extension = StructuredMetaResource._bestandsformaten.get_concept(puid).get_value(SKOS.notation)
        ext_filename = f"{self.uid}.{file_extension}"
        url = f"{MetaResource._config.cdn_base_uri}{ext_filename}"
        self.add_properties({
            MDTO.bestandsformaat: ext_file_fileformat_uri,
            MDTO.URLBestand: Literal(url, datatype=XSD.anyURI),
        })
        self.graph.add((URIRef(url), RDF.type, PREMIS.File))
        self.is_modified = True

    def set_filesize(self, filesize: int):
        self.add_properties({
            MDTO.omvang: Literal(filesize, datatype=XSD.integer)
        })
        self.is_modified = True

    def set_original_filename(self, ext_file_original_filename: str):
        self.graph.add((URIRef(self.ext_file_uri), PREMIS.originalName, Literal(ext_file_original_filename)))
        self.is_modified = True

    def set_aggregation_level(self, aggregation_term):
        self.add_properties({
            MDTO.aggregatieniveau: StructuredMetaResource._aggregatieniveaus.get_concept(aggregation_term).get_uri()
        })
        self.is_modified = True 

    def set_restrictions_public_availability(self, beperking_term):
        self.add_properties({
            MDTO.beperkingGebruik: {
                RDF.type: MDTO.BeperkingGebruikGegevens,  
                MDTO.beperkingGebruikType: StructuredMetaResource._beperkingen_openbaarheid.get_concept(beperking_term).get_uri()
            }
        })
        self.is_modified = True

    def set_license(self, license_term):
        self.add_properties({
            MDTO.beperkingGebruik: {
                RDF.type: MDTO.BeperkingGebruikGegevens,  
                MDTO.beperkingGebruikType: StructuredMetaResource._licenties.get_concept(license_term).get_uri()
            }
        })
        self.is_modified = True

    def set_metadata_source(self, source):
        self.metadata_sources.add(source)

    def _get_object_value(self, predicate, subject=None):
        if subject is not None:
            for s, p, o in self.graph.triples((subject, predicate, None)):
                return o
        else:
            for s, p, o in self.graph.triples((None, predicate, None)):
                if isinstance(s, BNode):
                    return o
        return None
