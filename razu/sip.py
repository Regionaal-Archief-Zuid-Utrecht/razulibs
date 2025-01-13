import os
import shutil
from typing import Callable, Dict, List, Optional
from functools import reduce
from operator import add

from razu.config import Config
from razu.identifiers import Identifiers
from razu.concept_resolver import ConceptResolver
from razu.meta_resource import StructuredMetaResource
from razu.meta_graph import MetaGraph, MDTO
from razu.manifest import Manifest
from razu.preservation_events import RazuPreservationEvents
from razu.decorators import unless_locked
import razu.util as util


class MetaResourcesDict(dict[str, StructuredMetaResource]):
    """Provides dict with additional methods for working with meta resources."""
    
    @property
    def with_referenced_files(self) -> list[StructuredMetaResource]:
        """Get list of resources that have referenced files."""
        return [meta_resource for meta_resource in self.values() if meta_resource.has_referenced_file]

    @property
    def description_uris(self) -> list[str]:
        """Get URIs of all resource descriptions."""
        return [meta_resource.description_uri for meta_resource in self.values()]

    @property
    def referenced_file_uris(self) -> list[str]:
        """Get URIs of all referenced files."""
        return [meta_resource.referenced_file_uri for meta_resource in self.with_referenced_files]

    @property
    def all_uris(self) -> list[str]:
        """Get all URIs (both description and referenced file URIs)."""
        return self.description_uris + self.referenced_file_uris

    @property
    def combined_rdf_graph(self) -> MetaGraph:
        """Get combined RDF graph of all meta resources."""
        return reduce(add, (meta_resource.graph for meta_resource in self.values()), MetaGraph())

    def export_rdf(self, format: str = 'turtle') -> None:
        """Export the combined RDF graph in the specified format."""
        print(self.combined_rdf_graph.serialize(format=format))

    def process_all(self, callback: Callable[[StructuredMetaResource], None]) -> None:
        """Process all meta resources using the provided callback function."""
        list(map(callback, self.values()))

    def process_having_referenced_files(self, callback: Callable[[StructuredMetaResource], None]) -> None:
        """Process all meta resources with referenced files using the provided callback function."""
        list(map(callback, self.with_referenced_files))


class Sip:
    """Represents a SIP (Submission Information Package)"""

    def __init__(self, sip_directory, resources_directory):
        self.cfg = Config.get_instance()
        self.sip_directory = sip_directory
        self.resources_directory = resources_directory
        self.meta_resources = MetaResourcesDict()
    
    @property
    def is_locked(self) -> bool:
        return self.log_event.is_locked

    @classmethod
    def create_new(cls, archive_creator_id: str, archive_id: str, sip_directory=None, resources_directory=None, ingestion_start_date=None) -> 'Sip':
        cfg = Config.get_instance()
        sip_directory = sip_directory or cfg.default_sip_directory
        resources_directory = resources_directory or cfg.default_resources_directory

        sip = cls(sip_directory, resources_directory)
        sip._create_new_sip(archive_creator_id, archive_id)
        return sip

    @classmethod
    def load_existing(cls, sip_directory: str, resources_directory=None) -> 'Sip':
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

    def get_metadata_resource_by_id(self, id: str) -> StructuredMetaResource:
        return self.meta_resources[id]

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

    @unless_locked
    def create_meta_resource(self, id: str, rdf_type=MDTO.Informatieobject) -> StructuredMetaResource:
        meta_resource = StructuredMetaResource(id, rdf_type=rdf_type)
        self.meta_resources[meta_resource.id] = meta_resource
        return meta_resource

    def store_metadata_resource(self, resource: StructuredMetaResource) -> None:
        """Store a resource in the SIP and update the manifest."""
        if resource.save():
            self.manifest.add_metadata_resource(resource, self.archive_creator_uri, self.archive_id)
            if resource.has_metadata_sources:
                for source in resource.metadata_sources:
                    self.log_event.metadata_modification(resource.description_uri, source)
            else:
                self.log_event.metadata_modification(resource.description_uri, resource.description_uri)
            print(f"Stored {resource.description_uri}.")

    def store_referenced_file_if_missing(self, resource: StructuredMetaResource) -> None:
        """Store a referenced file in the SIP and update the manifest."""
        if not resource.has_referenced_file:
            return
        destination_filepath = os.path.join(self.sip_directory, resource.referenced_file_filename)
        if not os.path.exists(destination_filepath):
            origin_filepath = os.path.join(self.resources_directory, resource.referenced_file_original_filename)
            shutil.copy2(origin_filepath, destination_filepath)
            self.manifest.add_referenced_resource(resource, self.archive_creator_uri, self.archive_id)
            self.log_event.filename_change(resource.description_uri, resource.referenced_file_original_filename, resource.referenced_file_filename)
            print(f"Stored referenced file {resource.referenced_file_original_filename} as {resource.referenced_file_uri}.")

    def validate_referenced_files(self):
        self.meta_resources.process_having_referenced_files(
            lambda resource: self.log_event.fixity_check(resource.referenced_file_uri, resource.validate_referenced_file_md5checksum())
        )

    def save(self):
        """Save all meta resources and their referenced files."""
        self.meta_resources.process_all(self.store_metadata_resource)
        if self.resources_directory:
            self.meta_resources.process_having_referenced_files(self.store_referenced_file_if_missing)
        self.log_event.process_queue()
        self.log_event.save()
        self.manifest.save()

    @unless_locked
    def lock(self):
        self.log_event.ingestion_end(self.meta_resources.all_uris)

    def _load_graph(self):
        id_factory = Identifiers(self.cfg)
        for filename in os.listdir(self.sip_directory):
            if os.path.isfile(os.path.join(self.sip_directory, filename)) and filename.endswith(f"{self.cfg.metadata_suffix}.{self.cfg.metadata_extension}"):
                if self.archive_creator_id is None:
                    self.archive_creator_id = id_factory.extract_source_id_from_filename(filename)
                    self.dataset_id = id_factory.extract_archive_id_from_filename(filename)
                id = id_factory.extract_id_from_file_path(filename)
                meta_resource = StructuredMetaResource(id=id)
                meta_resource.load()
                self.meta_resources[id] = meta_resource

    def _determine_ids_from_files_in_sip_directory(self):
        id_factory = Identifiers(self.cfg)
        filenames = [f for f in os.listdir(self.sip_directory) if os.path.isfile(os.path.join(self.sip_directory, f))]
        filename = filenames[0] if filenames else None
        return  id_factory.extract_source_id_from_filename(filename), id_factory.extract_archive_id_from_filename(filename)
