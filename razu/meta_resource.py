import os
from rdflib import URIRef, Literal, BNode

from razu.incrementer import Incrementer
from razu.razuconfig import RazuConfig
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, MDTO, PREMIS, XSD, SKOS
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
        self.id, self.uid, uri = self._setup_identifiers(id, uid, uri)
        super().__init__(uri)
        self.filename = f"{self._config.filename_prefix}-{self.id}.{self._config.metadata_suffix}.json"
        self.file_path = os.path.join(self._config.save_dir, self.filename)
        self.is_changed = False

    def save(self) -> None:
        try:
            with open(self.file_path, 'w') as file:
                file.write(self.graph.serialize(format='json-ld'))
            self.is_changed = False
        except IOError as e:
            print(f"Error saving file {self.file_path}: {e}")

    def load(self, file_path=None) -> None:
        if file_path is None:
            filename = f"{self._config.filename_prefix}-{self.id}.{self._config.metadata_suffix}.json"
            file_path = os.path.join(self._config.save_dir, filename)
        self.graph = MetaGraph()
        self.graph.parse(file_path, format="json-ld")

        subject = next(
            (s for s in self.graph.subjects(RDF.type, None) if isinstance(s, URIRef)),
            None
        )
        self.id, self.uid, self.uri = self._setup_identifiers(self.id, self.uid, str(subject))
        self.is_changed = False

    def _setup_identifiers(self, id=None, uid=None, uri=None):
        # uri takes precedence!
        if uri is not None:
            id = util.extract_id_from_filename(uri)
            uid = f"{MetaResource._config.filename_prefix}-{id}"
        elif uid is not None:
            id = util.extract_id_from_filename(uid)
            uri = f"{MetaResource._config.URI_prefix}-{id}"
        else:
            id = MetaResource._counter.next() if id is None else id
            uid = f"{MetaResource._config.filename_prefix}-{id}"
            uri = f"{MetaResource._config.URI_prefix}-{id}"
        return(id, uid, URIRef(uri))

class StructuredMetaResource(MetaResource):
    """
    Provides RDF structure templates for filling MetaResource,
    and properties for easy access to (parts of) the graph data.
    """

    _algoritmes = ConceptResolver("algoritme")
    _bestandsformaten = ConceptResolver("bestandsformaat")

    def __init__(self, id=None, rdf_type=None):
        super().__init__(id)

        if rdf_type is None:
            rdf_type = MDTO.Informatieobject
        self.add_properties({
            RDF.type: [PREMIS.Object, rdf_type],
            MDTO.identificatie: {
                RDF.type: MDTO.IdentificatieGegevens,
                MDTO.identificatieBron: "e-Depot RAZU",
                MDTO.identificatieKenmerk: f"{self._config.filename_prefix}-{self.id}"
            }
        })
        self.is_changed = True

    @property
    def ext_filename(self):
        return os.path.basename(self._get_object_value(MDTO.URLBestand, self.uri))

    @property
    def ext_file_original_filename(self):
        return str(self._get_object_value(PREMIS.originalName, self.uri))

    @property
    def ext_file_md5checksum(self):
        return str(self._get_object_value(MDTO.checksumWaarde))
    
    @property
    def ext_file_checksum_datetime(self):
        return str(self._get_object_value(MDTO.checksumDatum))

    @property
    def ext_file_fileformat_uri(self):
        return str(self._get_object_value(MDTO.bestandsformaat, self.uri))

    def set_type(self, rdf_type: URIRef):
        self.add_properties({RDF.type: rdf_type})
        self.is_changed = True

    def set_md5_properties(self, md5checksum, checksum_datetime):
        self.add_properties({
            MDTO.checksum: {
                RDF.type: MDTO.ChecksumGegevens,
                MDTO.checksumAlgoritme: StructuredMetaResource._algoritmes.get_concept("MD5").get_uri(),
                MDTO.checksumDatum: Literal(checksum_datetime, datatype=XSD.dateTime),
                MDTO.checksumWaarde: md5checksum
            }
        })
        self.is_changed = True

    def set_fileproperties_by_puid(self, puid):
        ext_file_fileformat_uri = StructuredMetaResource._bestandsformaten.get_concept(puid).get_uri()
        file_extension = StructuredMetaResource._bestandsformaten.get_concept(puid).get_value(SKOS.notation)
        ext_filename = f"{self.uid}.{file_extension}"
        url = f"https://{MetaResource._config.archive_creator_id.lower()}.opslag.razu.nl/{ext_filename}"
        self.add_properties({
            MDTO.bestandsformaat: ext_file_fileformat_uri,
            MDTO.URLBestand: Literal(f"{url}", datatype=XSD.anyURI),
        })
        self.is_changed = True

    def set_filesize(self, filesize: int):
        self.add_properties({
            MDTO.omvang: Literal(filesize, datatype=XSD.integer)
        })
        self.is_changed = True

    def set_original_filename(self, ext_file_original_filename: str):
        self.add_properties({
            PREMIS.originalName: ext_file_original_filename
        })
        self.is_changed = True

    def _get_object_value(self, predicate, subject=None):
        if subject is not None:
            for s, p, o in self.graph.triples((subject, predicate, None)):
                return o
        else:
            for s, p, o in self.graph.triples((None, predicate, None)):
                if isinstance(s, BNode):
                    return o
        return None
