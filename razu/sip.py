import os
import shutil

from datetime import datetime

from razu.config import Config
from .concept_resolver import ConceptResolver
from .meta_resource import StructuredMetaResource
from .meta_graph import MetaGraph
from .manifest import Manifest
# from .events import RazuEvents
from .meta_graph import MDTO

import razu.util as util


class MetaResourcesDict(dict):
    """ Provides dict a filter fir meta_resources that link to a referenced file."""
    
    @property
    def with_referenced_files(self) -> list:
        """Get list of resources that have referenced files."""
        return [resource for resource in self.values() if resource.has_ext_file]

    @property
    def all_uris(self) -> list:
        """Get all URIs from the meta resources, including both metadata and file URIs."""
        uris = []
        for meta_resource in self.values():
            uris.append(meta_resource.this_file_uri)
            if meta_resource.ext_file_uri is not None:
                uris.append(meta_resource.ext_file_uri)
        return uris

    @property
    def referenced_file_uris(self) -> list:
        """Get URIs of all referenced files."""
        uris = []
        for meta_resource in self.with_referenced_files:
            uris.append(meta_resource.ext_file_uri)
        return uris

    @property
    def combined_rdf_graph(self) -> MetaGraph:
        """Get combined RDF graph of all meta resources."""
        graph = MetaGraph()
        for resource in self.values():
            graph += resource.graph
        return graph


class Sip:
    """ Represents a SIP (Submission Information Package) """

    def __init__(self, sip_directory: str, file_source_directory=None):
        self.sip_directory = sip_directory
        self.file_source_directory = file_source_directory
        self.cfg = Config.get_instance()
        self.meta_resources = MetaResourcesDict()

    @classmethod
    def create_new(cls, archive_creator_id: str, archive_id: str, sip_directory: str, resource_directory=None) -> 'Sip':
        sip = cls(sip_directory, resource_directory)
        sip._create_new_sip(archive_creator_id, archive_id)

        sip.cfg.add_properties(
            archive_id=archive_id,
            archive_creator_id=archive_creator_id,
            sip_directory=sip_directory,
            resources_directory=resource_directory
        )
        return sip

    @classmethod
    def load_existing(cls, sip_directory: str, file_source_directory=None) -> 'Sip':
        sip = cls(sip_directory, file_source_directory)
        sip._open_existing_sip()
        sip._load_graph()
        return sip

    def _create_new_sip(self, archive_creator_id, dataset_id):
        self.archive_creator_id = archive_creator_id
        self.dataset_id = dataset_id
        os.makedirs(self.sip_directory, exist_ok=True)

        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.manifest = Manifest.create_new(self.sip_directory)
        # self.log_event = RazuEvents(self.sip_directory)

    def _open_existing_sip(self):
        if not os.listdir(self.sip_directory):
            raise ValueError(f"The SIP directory '{self.sip_directory}' is empty.")
        self.archive_creator_id, self.dataset_id = self._determine_ids_from_files_in_sip_directory()

        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        # self.manifest = Manifest(self.sip_directory)
        # self.log_event = RazuEvents(self.sip_directory)

    def get_meta_resource(self, id: str) -> StructuredMetaResource:
        """Get a meta resource by its ID."""
        if id not in self.meta_resources:
            raise KeyError(f"No meta resource found with ID: {id}")
        return self.meta_resources[id]

    def export_rdf(self, format='turtle') -> None:
        """Export the combined RDF graph in the specified format."""
        print(self.meta_resources.combined_rdf_graph.serialize(format=format))

    def create_meta_resource(self, id=None, rdf_type=MDTO.Informatieobject) -> StructuredMetaResource:
        # if self.log_event.is_locked:
        #     raise AssertionError("Sip is locked. Cannot create meta resource.")
        meta_resource = StructuredMetaResource(id=id, rdf_type=rdf_type)
        meta_resource.file_path = os.path.join(self.sip_directory, meta_resource.filename)
        self.meta_resources[meta_resource.id] = meta_resource
        return meta_resource

    def store_resource(self, resource: StructuredMetaResource) -> None:
        """Store a resource in the SIP and update the manifest."""
        # if self.log_event.is_locked:
        #     raise AssertionError("Sip is locked. Cannot store resource.")
        if resource.save():
            self.manifest.add_resource(resource, self.archive_creator_uri, self.dataset_id)

            # if resource.metadata_sources is None:
            #     self.log_event.metadata_modification(resource.this_file_uri, resource.this_file_uri)
            # else:
            #     for source in resource.metadata_sources:
            #         self.log_event.metadata_modification(resource.this_file_uri, source)

            print(f"Stored {resource.this_file_uri}.")

    def store_referenced_file(self, resource: StructuredMetaResource) -> None:
        """Store a referenced file in the SIP and update the manifest."""
        if resource.has_ext_file:
            origin_filepath = os.path.join(self.file_source_directory, resource.ext_file_original_filename)
            dest_filepath = os.path.join(self.sip_directory, resource.ext_filename)
            if not os.path.exists(dest_filepath):
                shutil.copy2(origin_filepath, dest_filepath)
                self.manifest.add_resource(resource, self.archive_creator_uri, self.dataset_id)
                # self.log_event.filename_change(resource.ext_file_uri, resource.ext_file_original_filename, resource.ext_filename)

                print(f"Stored referenced file {resource.ext_file_original_filename} as {resource.ext_file_uri}.")

    def store_meta_resources(self) -> None:
        """Store all meta resources and their referenced files."""
        for meta_resource in self.meta_resources.values():
            self.store_resource(meta_resource)
        for meta_resource in self.meta_resources.with_referenced_files:
            self.store_referenced_file(meta_resource)
        # self.log_event.process_queue()
        # self.log_event.save()
        self.manifest.save()

    def validate_referenced_files(self):
        pass
        # for meta_resource in self.meta_resources.with_referenced_files:
        #     self.log_event.fixity_check(meta_resource.ext_file_uri, meta_resource.validate_md5())

    def validate(self):
        pass

    def save(self):
        for meta_resource in self.meta_resources.values():
            self.store_resource(meta_resource)
        for meta_resource in self.meta_resources.with_referenced_files:
            self.store_referenced_file(meta_resource)
        # self.log_event.process_queue()
        # self.log_event.save()
        self.manifest.save()

    def _load_graph(self):
        for filename in os.listdir(self.sip_directory):
            if filename.endswith(self.cfg.metadata_extension):
                meta_resource = StructuredMetaResource()
                meta_resource.file_path = os.path.join(self.sip_directory, filename)
                meta_resource.load()
                self.meta_resources[meta_resource.id] = meta_resource

    def _determine_ids_from_files_in_sip_directory(self):
        filenames = [f for f in os.listdir(self.sip_directory) if os.path.isfile(os.path.join(self.sip_directory, f))]
        filename = filenames[0] if filenames else None
        return  util.extract_source_from_filename(filename), util.extract_archive_from_filename(filename)