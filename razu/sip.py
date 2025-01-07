import os
import shutil
from datetime import datetime

from razu.config import Config
from razu.concept_resolver import ConceptResolver
from razu.meta_resource import StructuredMetaResource
from razu.meta_graph import MetaGraph, MDTO
from razu.manifest import Manifest
from razu.preservation_events import RazuPreservationEvents
import razu.util as util


class MetaResourcesDict(dict[str, StructuredMetaResource]):
    """Provides dict with additional methods for working with meta resources."""
    
    @property
    def with_referenced_files(self) -> list:
        """Get list of resources that have referenced files."""
        return [resource for resource in self.values() if resource.has_ext_file]

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

    def process_all(self, callback: callable) -> None:
        """Process all meta resources using the provided callback function."""
        for resource in self.values():
            callback(resource)

    def process_with_referenced_files(self, callback: callable) -> None:
        """Process all meta resources with referenced files using the provided callback function."""
        for resource in self.with_referenced_files:
            callback(resource)

    def export_rdf(self, format: str = 'turtle') -> None:
        """Export the combined RDF graph in the specified format."""
        print(self.combined_rdf_graph.serialize(format=format))


class Sip:
    """Represents a SIP (Submission Information Package)"""

    def __init__(self, sip_directory, resources_directory):
        self.cfg = Config.get_instance()
        self.sip_directory = sip_directory
        self.resources_directory = resources_directory
        self.meta_resources = MetaResourcesDict()


    @classmethod
    def create_new(cls, archive_creator_id: str, archive_id: str, sip_directory=None, resources_directory=None, ingestion_start_date=None) -> 'Sip':
        cfg = Config.get_instance()
        sip_directory = sip_directory or cfg.default_sip_directory
        resources_directory = resources_directory or cfg.default_resources_directory

        sip = cls(sip_directory, resources_directory)
        sip._create_new_sip(archive_creator_id, archive_id)
        return sip

    @classmethod
    def load_existing(cls, sip_directory: str, resources_directory:str) -> 'Sip':
        sip = cls(sip_directory, resources_directory)
        sip._open_existing_sip()
        sip._load_graph()
        return sip

    def _create_new_sip(self, archive_creator_id, archive_id):
        actoren = ConceptResolver('actor')
        self.archive_creator_id = archive_creator_id
        self.archive_id = archive_id
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.cfg.add_properties(
            archive_id=archive_id,
            archive_creator_id=archive_creator_id,
            sip_directory=self.sip_directory,
        )
        os.makedirs(self.sip_directory, exist_ok=True)
        self.manifest = Manifest.create_new(self.sip_directory)
        self.log_event = RazuPreservationEvents(self.sip_directory)

    def _open_existing_sip(self):
        if not os.listdir(self.sip_directory):
            raise ValueError(f"The SIP directory '{self.sip_directory}' is empty, cannot load SIP.")
        self.archive_creator_id, self.archive_id = self._determine_ids_from_files_in_sip_directory()
        self.cfg.add_properties(
            archive_id=self.archive_id,
            archive_creator_id=self.archive_creator_id,
            sip_directory=self.sip_directory,
        )   
        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.manifest = Manifest.load_existing(self.sip_directory)
        self.log_event = RazuPreservationEvents(self.sip_directory)

    def create_meta_resource(self, id=None, rdf_type=MDTO.Informatieobject) -> StructuredMetaResource:
        # if self.log_event.is_locked:
        #     raise AssertionError("Sip is locked. Cannot create meta resource.")
        meta_resource = StructuredMetaResource(id=id, rdf_type=rdf_type)
        meta_resource.file_path = os.path.join(self.sip_directory, meta_resource.filename)
        self.meta_resources[meta_resource.id] = meta_resource
        return meta_resource

    def store_metadata_resource(self, resource: StructuredMetaResource) -> None:
        """Store a resource in the SIP and update the manifest."""
        # if self.log_event.is_locked:
        #     raise AssertionError("Sip is locked. Cannot store resource.")
        if resource.save():
            self.manifest.add_metadata_resource(resource, self.archive_creator_uri, self.archive_id)

            # if resource.metadata_sources is None:
            #     self.log_event.metadata_modification(resource.this_file_uri, resource.this_file_uri)
            # else:
            #     for source in resource.metadata_sources:
            #         self.log_event.metadata_modification(resource.this_file_uri, source)

            print(f"Stored {resource.this_file_uri}.")

    def store_referenced_file(self, resource: StructuredMetaResource) -> None:
        """Store a referenced file in the SIP and update the manifest."""
        if resource.has_ext_file:
            origin_filepath = os.path.join(self.resources_directory, resource.ext_file_original_filename)
            dest_filepath = os.path.join(self.sip_directory, resource.ext_filename)
            if not os.path.exists(dest_filepath):
                shutil.copy2(origin_filepath, dest_filepath)
                self.manifest.add_referenced_resource(resource, self.archive_creator_uri, self.archive_id)
                # self.log_event.filename_change(resource.ext_file_uri, resource.ext_file_original_filename, resource.ext_filename)

                print(f"Stored referenced file {resource.ext_file_original_filename} as {resource.ext_file_uri}.")

    def store_meta_resources(self) -> None:
        """Store all meta resources and their referenced files."""
        self.meta_resources.process_all(self.store_metadata_resource)
        self.meta_resources.process_with_referenced_files(self.store_referenced_file)
        # self.log_event.process_queue()
        # self.log_event.save()
        self.manifest.save()

    def validate_referenced_files(self):
        pass
        # self.meta_resources.process_referenced_files(
        #     lambda resource: self.log_event.fixity_check(resource.ext_file_uri, resource.validate_md5())
        # )

    def save(self):
        """Save all meta resources and their referenced files."""
        self.meta_resources.process_all(self.store_metadata_resource)
        self.meta_resources.process_with_referenced_files(self.store_referenced_file)
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