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

    def __init__(self, sip_directory, archive_creator_id=None, dataset_id=None, file_source_directory=None, ingestion_start_date=None) -> None:
        self.sip_directory = sip_directory
        self.file_source_directory = file_source_directory

        if archive_creator_id is not None and dataset_id is not None:
            self._create_new_sip(archive_creator_id, dataset_id)
        else:
            self._open_existing_sip()

        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.cfg = RazuConfig(archive_creator_id=self.archive_creator_id, archive_id=self.dataset_id, save_directory=self.sip_directory)

        self.manifest = Manifest(self.sip_directory)
        self.log_event = RazuEvents(self.sip_directory)
        self.meta_resources = MetaResourcesDict()

        if ingestion_start_date is not None:
            self.log_event.to_queue('ingestion_start', lambda: self.referenced_file_uris, timestamp=ingestion_start_date)

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
                "Dataset": self.dataset_id,
                "URI": resource.this_file_uri
            })

            if resource.metadata_sources is None:
                self.log_event.metadata_modification(resource.this_file_uri, resource.this_file_uri)
            else:
                self.log_event.metadata_modification(resource.metadata_sources, resource.this_file_uri)

            print(f"Stored {resource.this_file_uri}.")

    def store_referenced_file(self, resource: StructuredMetaResource):
        if self.is_locked:
            raise AssertionError("Sip is locked. Cannot store referenced file.")
        
        if self.file_source_directory is not None:
            origin_filepath = os.path.join(self.file_source_directory, resource.ext_file_original_filename)
            dest_filepath = os.path.join(self.sip_directory, resource.ext_filename)

            if not os.path.exists(dest_filepath):
                shutil.copy2(origin_filepath, dest_filepath)

                self.manifest.add_entry(resource.ext_filename, resource.ext_file_md5checksum,
                                        resource.ext_file_checksum_datetime)
                self.manifest.extend_entry(resource.ext_filename, {
                    "ObjectUID": resource.uid,
                    "Source": self.archive_creator_uri,
                    "Dataset": self.dataset_id,
                    "FileFormat": resource.ext_file_fileformat_uri,
                    "OriginalFilename": resource.ext_file_original_filename,
                    "URI": resource.ext_file_uri
                })
                self.log_event.filename_change(resource.ext_file_uri, resource.ext_file_original_filename, resource.ext_filename)

                print(f"Stored referenced file {resource.ext_file_original_filename} as {resource.ext_file_uri}.")

    def lock(self):
        self.log_event.ingestion_end(self.all_uris)

    def validate_referenced_files(self):
        for meta_resource in self.meta_resources.with_referenced_files():
            self.log_event.fixity_check(meta_resource.ext_file_uri, meta_resource.validate_md5())

    def validate(self):
        self.manifest.verify() # TODO: deze validate logt niet, de andere wel , deze sip.validate method verwijderen?

    def save(self):
        for meta_resource in self.meta_resources.values():
            self.store_resource(meta_resource)
        for meta_resource in self.meta_resources.with_referenced_files():
            self.store_referenced_file(meta_resource)
        self.log_event.process_queue()
        self.log_event.save()
        self.manifest.save()

    def _create_new_sip(self, archive_creator_id, dataset_id):
        if not os.path.exists(self.sip_directory):
            os.makedirs(self.sip_directory)
        elif os.listdir(self.sip_directory):
            raise ValueError(f"The SIP directory '{self.sip_directory}' is not empty.")
        self.archive_creator_id = archive_creator_id
        self.dataset_id = dataset_id
        print(f"Created empty SIP at {self.sip_directory}.")

    def _open_existing_sip(self):
        if not os.listdir(self.sip_directory):
            raise ValueError(f"The SIP directory '{self.sip_directory}' is empty.")
        self.archive_creator_id, self.dataset_id = self._determine_ids_from_files_in_sip_directory()
        print(f"Opened existing SIP at {self.sip_directory}.")

    def _load_graph(self):
        for filename in os.listdir(self.sip_directory):
            if os.path.isfile(os.path.join(self.sip_directory, filename)) and filename.endswith(f"{self.cfg.metadata_suffix}.{self.cfg.metadata_extension}"):
                if self.archive_creator_id is None:
                    self.archive_creator_id = util.extract_source_from_filename(filename)
                    self.dataset_id = util.extract_archive_from_filename(filename)
                id = util.extract_id_from_filepath(filename)
                meta_resource = StructuredMetaResource(id=id)
                meta_resource.load()
                self.meta_resources[id] = meta_resource

    def _determine_ids_from_files_in_sip_directory(self):
        filenames = [f for f in os.listdir(self.sip_directory) if os.path.isfile(os.path.join(self.sip_directory, f))]
        filename = filenames[0] if filenames else None
        return  util.extract_source_from_filename(filename), util.extract_archive_from_filename(filename)