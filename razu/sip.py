import os
import shutil

from datetime import datetime

from .razuconfig import RazuConfig
from .concept_resolver import ConceptResolver
from .meta_resource import StructuredMetaResource
from .meta_graph import MetaGraph
from .manifest import Manifest
from .events import RazuEvents

import razu.util as util


class MetaResourcesDict(dict):
    def with_external_files(self):
        return [resource for resource in self.values() if resource.has_ext_file]


class Sip:
    """
    A class representing a SIP (Submission Information Package)
    """

    def __init__(self, sip_dir, archive_creator_id=None, dataset_id=None) -> None:
        self.sip_dir = sip_dir
        self.meta_resources = MetaResourcesDict()

        if not os.path.exists(self.sip_dir):
            if archive_creator_id is None or dataset_id is None:
                raise ValueError("Both archive_creator_id and dataset_id must be provided when creating a new SIP.")
            self.archive_creator_id = archive_creator_id
            self.dataset_id = dataset_id
            os.makedirs(self.sip_dir)
            print(f"Created empty SIP at {self.sip_dir}.")
        else:
            if os.listdir(self.sip_dir):
                raise ValueError(f"The SIP directory '{self.sip_dir}' is not empty.")
            if archive_creator_id is None or dataset_id is None:
                self.archive_creator_id, self.dataset_id = self._determine_ids_from_files_in_sip_dir()
            else:
                self.archive_creator_id = archive_creator_id
                self.dataset_id = dataset_id

        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.cfg = RazuConfig(archive_creator_id=self.archive_creator_id, archive_id=self.dataset_id, save_dir=self.sip_dir)

        self.manifest = Manifest(self.sip_dir)
        self.log_event = RazuEvents(self.sip_dir)
        self._load_graph()

    @property
    def all_uris(self):
        uris = []
        # all meta_resouce uris:
        for meta_resource in self.meta_resources.values():
            uris.append(meta_resource.this_file_uri)
            # a meta_resource might be accompanied by a file object with an uri:
            if meta_resource.ext_file_uri is not None:
                uris.append(meta_resource.ext_file_uri)
        return uris
    
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

    def store_resource(self, resource: StructuredMetaResource, source_dir=None):  # TODO  name something like "persist_resource"  ?
        resource.save()
        md5checksum = util.calculate_md5(resource.file_path)
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
        self.log_event.save()

    def _load_graph(self):
        for filename in os.listdir(self.sip_dir):
            if os.path.isfile(os.path.join(self.sip_dir, filename)) and filename.endswith(f"{self.cfg.metadata_suffix}.{self.cfg.metadata_extension}"):
                if self.archive_creator_id is None:
                    self.archive_creator_id = util.extract_source_from_filename(filename)
                    self.dataset_id = util.extract_archive_from_filename(filename)
                id = util.extract_id_from_filepath(filename)
                meta_resource = StructuredMetaResource(id=id)
                meta_resource.load()
                self.meta_resources[id] = meta_resource
        # for filename in self.manifest.get_filenames():
        #     if filename.endswith(f"{self.cfg.metadata_suffix}.{self.cfg.metadata_extension}"):
        #         id = util.extract_id_from_filepath(filename)
        #         meta_resource = StructuredMetaResource(id=id)
        #         meta_resource.load()
        #         self.meta_resources[id] = meta_resource

    def _determine_ids_from_files_in_sip_dir(self):
        filenames = [f for f in os.listdir(self.sip_dir) if os.path.isfile(os.path.join(self.sip_dir, f))]
        filename = filenames[0] if filenames else None
        return  util.extract_source_from_filename(filename), util.extract_archive_from_filename(filename)