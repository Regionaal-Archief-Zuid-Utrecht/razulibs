import os
from rdflib import URIRef, Literal, BNode

from razu.incrementer import Incrementer
from razu.razuconfig import RazuConfig
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, MDTO, DCT, PREMIS, XSD, SKOS, OWL
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
        self.file_path = os.path.join(self._config.save_dir, self.filename)
        self.is_modified = False

    def save(self) -> bool:
        if self.is_modified:
            try:
                with open(self.file_path, 'w') as file:
                    file.write(self.graph.serialize(format='json-ld'))
                self.is_modified = False
                return True
            except IOError as e:
                print(f"Error saving file {self.file_path}: {e}")
        return False 

    def load(self) -> None:
        self.graph = MetaGraph()
        self.graph.parse(self.file_path, format="json-ld")
        self.is_modified = False

    def _construct_identifiers(self, id=None, uid=None, uri=None):
        # uri takes precedence!
        if uri is not None:
            id = util.extract_id_from_filepath(uri)
            uid = self._construct_uid(id)
        elif uid is not None:
            id = util.extract_id_from_filepath(uid)
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

    _algoritmes = ConceptResolver("algoritme")
    _bestandsformaten = ConceptResolver("bestandsformaat")

    def __init__(self, id=None, rdf_type=None, sources=None):
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
            DCT.hasFormat: URIRef(self.this_file_uri)
        })
        self.graph.add((URIRef(self.this_file_uri), RDF.type, PREMIS.File))
        self.metadata_sources = sources
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

    def validate_md5(self):
        return util.calculate_md5(os.path.join(self._config.save_dir, self.ext_filename)) == self.ext_file_md5checksum

    def set_type(self, rdf_type: URIRef):
        self.add_properties({RDF.type: rdf_type})
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
            # OWL.sameAs: URIRef(url)
        })
        self.graph.add((URIRef(url), RDF.type, PREMIS.File))
        # self.graph.add((URIRef(self.this_file_uri), OWL.sameAs, self.uri))
        self.is_modified = True

    def set_filesize(self, filesize: int):
        self.add_properties({
            MDTO.omvang: Literal(filesize, datatype=XSD.integer)
        })
        self.is_modified = True

    def set_original_filename(self, ext_file_original_filename: str):
        self.graph.add((URIRef(self.ext_file_uri), PREMIS.originalName, Literal(ext_file_original_filename)))
        self.is_modified = True

    def set_metadata_sources(self, sources: list):
        self.metadata_sources = sources

    def _get_object_value(self, predicate, subject=None):
        if subject is not None:
            for s, p, o in self.graph.triples((subject, predicate, None)):
                return o
        else:
            for s, p, o in self.graph.triples((None, predicate, None)):
                if isinstance(s, BNode):
                    return o
        return None
