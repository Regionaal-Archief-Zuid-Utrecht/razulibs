import os
from rdflib import URIRef, Literal

from incrementer import Incrementer
from razuconfig import RazuConfig
from rdf_resource import RDFResource
from meta_graph import MetaGraph, RDF, MDTO, PREMIS, XSD, SKOS
from concept_resolver import ConceptResolver
import util as util


class MetaResource(RDFResource):
    """
    An RDF Resource tailored for use in the RAZU edepot SIPs.

    Provides load(), save() and uri, uid & id logic.
    """
    _config = RazuConfig()
    _counter = Incrementer()

    def __init__(self, id=None, uid=None, uri=None):
        self.id, self.uid, uri = self._fill_identifiers(id, uid, uri)
        super().__init__(uri)
        self.is_changed = False

    def save(self) -> None:
        filename = f"{self._config.filename_prefix}-{self.id}.{self._config.metadata_suffix}.json"
        file_path = os.path.join(self._config.save_dir, filename)
        with open(file_path, 'w') as file:
            file.write(self.graph.serialize(format='json-ld'))
        self.is_changed = False

    def load(self, file_path=None) -> None:
        if file_path is None:
            filename = f"{self._config.filename_prefix}-{self.id}.{self._config.metadata_suffix}.json"
            file_path = os.path.join(self._config.save_dir, filename)
        rdf = MetaGraph()
        rdf.parse(file_path, format="json-ld")
        self.graph = rdf

        subject = next(
            (s for s in self.graph.subjects(RDF.type, None) if isinstance(s, URIRef)),
            None
        )
        self.id, self.uid, self.uri = self._fill_identifiers(self.id, self.uid, str(subject))
        self.is_changed = False

    def _fill_identifiers(self, id=None, uid=None, uri=None):
        # uri takes precedence!
        if uri is not None:
            id = util.extract_id_from_filename(uri)
            uid = f"{MetaResource._config.filename_prefix}-{id}"
        elif uid is not None:
            id = util.extract_id_from_filename(uid)
            uri = f"{MetaResource._config.URI_prefix}-{id}"
        elif id is not None:
            uid = f"{MetaResource._config.filename_prefix}-{id}"
            uri = f"{MetaResource._config.URI_prefix}-{id}"
        else:
            id = MetaResource._counter.next()
            uid = f"{MetaResource._config.filename_prefix}-{id}"
            uri = f"{MetaResource._config.URI_prefix}-{id}"
        return(id, uid, uri)

class StructuredMetaResource(MetaResource):
    """
    Provides RDF structure templates for filling MetaReource.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.algoritmes = ConceptResolver("algoritme")
        self.bestandsformaten = ConceptResolver("bestandsformaat")

        rdf_type = kwargs.get('rdf_type', MDTO.Informatieobject)
        self.add_properties({
            RDF.type: [PREMIS.Object, rdf_type],
            MDTO.identificatie: {
                RDF.type: MDTO.IdentificatieGegevens,
                MDTO.identificatieBron: "e-Depot RAZU",
                MDTO.identificatieKenmerk: f"{self._config.filename_prefix}-{self.id}"
            }
        })
        self.is_changed = True

    def set_type(self, rdf_type: URIRef):
        self.add_properties({RDF.type: rdf_type})
        self.is_changed = True

    def set_md5_properties(self, md5checksum, checksum_datetime):
        self.add_properties({
            MDTO.checksum: {
                RDF.type: MDTO.ChecksumGegevens,
                MDTO.checksumAlgoritme: self.algoritmes.get_concept("MD5").get_uri(),
                MDTO.checksumDatum: Literal(checksum_datetime, datatype=XSD.dateTime),
                MDTO.checksumWaarde: md5checksum
            }
        })
        self.is_changed = True

    def set_fileproperties_by_puid(self, puid):
        fileformat_uri = self.bestandsformaten.get_concept(puid).get_uri()
        file_extension = self.bestandsformaten.get_concept(puid).get_value(SKOS.notation)
        filename = f"{puid}.{file_extension}"
        url = f"https://{MetaResource._config.archive_creator_id.lower()}.opslag.razu.nl/{filename}"
        self.add_properties({
            MDTO.bestandsformaat: fileformat_uri,
            MDTO.URLBestand: Literal(f"{url}", datatype=XSD.anyURI),
        })
        self.is_changed = True

    def set_filesize(self, filesize: int):
        self.add_properties({
            MDTO.omvang: Literal(filesize, datatype=XSD.integer)
        })
        self.is_changed = True

    def set_original_filename(self, original_filename: str):
        self.add_properties({
            PREMIS.originalName: original_filename
        })
        self.is_changed = True
