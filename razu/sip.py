import os
import shutil

from datetime import datetime

from .razuconfig import RazuConfig
from .concept_resolver import ConceptResolver
from .meta_resource import StructuredMetaResource
from .meta_graph import MetaGraph
from .manifest import Manifest
import razu.util as util


class Sip:
    """
    A class representing a SIP (Submission Information Package)
    """

    def __init__(self, sip_dir, archive_creator_id, dataset_id: str) -> None:
        self.sip_dir = sip_dir
        self.archive_creator_id = archive_creator_id
        self.dataset_id = dataset_id
        self.meta_resources = {}

        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.cfg = RazuConfig(archive_creator_id=archive_creator_id, archive_id=dataset_id, save_dir=sip_dir, save=True)

        if not os.path.exists(self.sip_dir):
            os.makedirs(self.sip_dir)
            print(f"Created empty SIP at {self.sip_dir}.")

        self.manifest = Manifest(self.sip_dir, self.cfg.manifest_filename)
        if len(self.manifest.get_filenames()) > 0:
            self._load_graph()

    def export_rdf(self, format='turtle'):
        graph = MetaGraph()
        for resource in self.meta_resources.values():
            graph += resource.graph
        print(graph.serialize(format=format))

    def create_resource(self, id=None, rdf_type=None) -> StructuredMetaResource:
        resource = StructuredMetaResource(id, rdf_type)
        self.meta_resources[id] = resource
        return resource

    def get_resource_by_id(self, id) -> StructuredMetaResource:
        return self.meta_resources[id]

    def store_resource(self, resource: StructuredMetaResource,
                       source_dir=None):  # TODO  name something like "persist_resource"  ?
        resource.save()
        md5checksum = self.manifest.calculate_md5(resource.file_path)
        md5date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.manifest.add_entry(resource.filename, md5checksum, md5date)
        self.manifest.update_entry(resource.filename, {
            "ObjectUID": resource.uid,
            "Source": self.archive_creator_uri,
            "Dataset": self.dataset_id
        })

        # process the (optional) referenced file:
        if source_dir is not None:
            origin_filepath = os.path.join(source_dir, resource.ext_file_original_filename)
            dest_filepath = os.path.join(self.sip_dir, resource.ext_filename)
            shutil.copy2(origin_filepath, dest_filepath)

            self.manifest.add_entry(resource.ext_filename, resource.ext_file_md5checksum,
                                    resource.ext_file_checksum_datetime)
            self.manifest.update_entry(resource.filename, {
                "ObjectUID": resource.uid,
                "Source": self.archive_creator_uri,
                "Dataset": self.dataset_id,
                "FileFormat": resource.ext_file_fileformat_uri,
                "OriginalFilename": resource.ext_file_original_filename
            })
        self.manifest.save()

    def validate(self):
        self.manifest.verify()

    def save(self):  # TODO: naam?
        for meta_resource in self.meta_resources.values():
            self.store_resource(meta_resource)

    def _load_graph(self):
        for filename in self.manifest.get_filenames():
            if filename.endswith(f"{self.cfg.metadata_suffix}.json"):
                id = util.extract_id_from_filename(filename)
                meta_resource = StructuredMetaResource(id=id)
                meta_resource.load()
                self.meta_resources[id] = meta_resource
