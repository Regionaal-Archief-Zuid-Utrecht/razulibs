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
    """ Provides dict a filter fir meta_resources that link to a referenced file."""
    
    def with_referenced_files(self):
        return [resource for resource in self.values() if resource.has_ext_file]


class Sip:
    """ Represents a SIP (Submission Information Package) """

    def __init__(self, sip_dir, archive_creator_id=None, dataset_id=None) -> None:
        self.sip_dir = sip_dir

        if archive_creator_id is not None and dataset_id is not None:
            self._create_new_sip(archive_creator_id, dataset_id)
        else:
            self._open_existing_sip()

        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.cfg = RazuConfig(archive_creator_id=self.archive_creator_id, archive_id=self.dataset_id, save_dir=self.sip_dir)

        self.manifest = Manifest(self.sip_dir)
        self.log_event = RazuEvents(self.sip_dir)
        self.meta_resources = MetaResourcesDict()
        self._load_graph()
        self.is_locked = self.log_event.is_locked

    @property
    def all_uris(self) -> list:
        uris = []
        # all meta_resouce uris:
        for meta_resource in self.meta_resources.values():
            uris.append(meta_resource.this_file_uri)
            # a meta_resource might be accompanied by a file object with an uri:
            if meta_resource.ext_file_uri is not None:
                uris.append(meta_resource.ext_file_uri)
        return uris

    @property    
    def referenced_file_uris(self) -> list:
        uris = []
        for meta_resource in self.meta_resources.with_referenced_files():
            uris.append(meta_resource.ext_file_uri)
        return uris

    def export_rdf(self, format='turtle'):
        graph = MetaGraph()
        for resource in self.meta_resources.values():
            graph += resource.graph
        print(graph.serialize(format=format))

    def create_resource(self, id=None, rdf_type=None) -> StructuredMetaResource:
        if self.is_locked:
            raise AssertionError("Sip is locked. Cannot create resource.")
        resource = StructuredMetaResource(id, rdf_type)
        self.meta_resources[id] = resource
        return resource

    def get_resource_by_id(self, id) -> StructuredMetaResource:
        return self.meta_resources[id]

    def store_resource(self, resource: StructuredMetaResource):
        if self.is_locked:
            raise AssertionError("Sip is locked. Cannot store resource.")
        if resource.save():
            md5checksum = util.calculate_md5(resource.file_path)
            md5date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            self.manifest.add_entry(resource.filename, md5checksum, md5date)
            self.manifest.extend_entry(resource.filename, {
                "ObjectUID": resource.uid,
                "Source": self.archive_creator_uri,
                "Dataset": self.dataset_id
            })
            print(f"Stored {resource.this_file_uri}.")

    def store_referenced_file(self, resource: StructuredMetaResource, source_dir):
        if self.is_locked:
            raise AssertionError("Sip is locked. Cannot store referenced file.")
        # TODO zou vergelijkbaar met save moeten controleren of dit nog ndoig is (check file en hash?)
        origin_filepath = os.path.join(source_dir, resource.ext_file_original_filename)
        dest_filepath = os.path.join(self.sip_dir, resource.ext_filename)
        shutil.copy2(origin_filepath, dest_filepath)

        self.manifest.add_entry(resource.ext_filename, resource.ext_file_md5checksum,
                                resource.ext_file_checksum_datetime)
        self.manifest.extend_entry(resource.ext_filename, {
            "ObjectUID": resource.uid,
            "Source": self.archive_creator_uri,
            "Dataset": self.dataset_id,
            "FileFormat": resource.ext_file_fileformat_uri,
            "OriginalFilename": resource.ext_file_original_filename
        })
        print(f"Added referenced file {resource.ext_file_original_filename} as {resource.ext_file_uri}.")

    def validate(self):
        self.manifest.verify()

    def save(self):
        for meta_resource in self.meta_resources.values():
            self.store_resource(meta_resource)
        # TODO: ook store_referenced_file zou aangeroepen moeten worden (met controle niet al uitgevoerd)
        self.manifest.save()
        self.log_event.save()

    def _create_new_sip(self, archive_creator_id, dataset_id):
        if not os.path.exists(self.sip_dir):
            os.makedirs(self.sip_dir)
        elif os.listdir(self.sip_dir):
            raise ValueError(f"The SIP directory '{self.sip_dir}' is not empty.")
        self.archive_creator_id = archive_creator_id
        self.dataset_id = dataset_id
        print(f"Created empty SIP at {self.sip_dir}.")

    def _open_existing_sip(self):
        if not os.listdir(self.sip_dir):
            raise ValueError(f"The SIP directory '{self.sip_dir}' is empty.")
        self.archive_creator_id, self.dataset_id = self._determine_ids_from_files_in_sip_dir()
        print(f"Opened existing SIP at {self.sip_dir}.")

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

    def _determine_ids_from_files_in_sip_dir(self):
        filenames = [f for f in os.listdir(self.sip_dir) if os.path.isfile(os.path.join(self.sip_dir, f))]
        filename = filenames[0] if filenames else None
        return  util.extract_source_from_filename(filename), util.extract_archive_from_filename(filename)
    