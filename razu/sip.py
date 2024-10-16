import os
import shutil

from datetime import datetime
from rdflib import URIRef, BNode

from razuconfig import RazuConfig
from concept_resolver import ConceptResolver
from meta_resource import StructuredMetaResource
from meta_graph import MetaGraph
from manifest import Manifest

import util as util


class Sip:

    def __init__(self, sip_dir, archive_creator_id, dataset_id: str) -> None:
        """
        Loads a SIP from sip_dir or
        creates one.
        """
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
        self._load_meta_resources()

    def save_graph(self):


    def create_object(self, **kwargs):
        # TODO: identifiers kunnen de mist in gaan als zowel een uri wordt meegegeven als soms ook vertrouwd wordt op
        # automatische toekenning met self.newest_id
        valid_kwargs = {}
        if 'entity_id' not in kwargs:
            self.newest_id += 1
            valid_kwargs['entity_id'] = self.newest_id
        else:
            valid_kwargs['entity_id'] = kwargs['entity_id']

        if 'rdf_type' in kwargs:
            valid_kwargs['rdf_type'] = kwargs['rdf_type']
        return StructuredMetaResource(**valid_kwargs)

    def store_object(self, object: StructuredMetaResource, source_dir = None):
        # process the metadata-file:
        self.graph += object
        object.save()
        md5checksum = self.manifest.calculate_md5(object.meta_file_path)
        md5date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.manifest.add_entry(object.meta_filename, md5checksum, md5date) 
        self.manifest.update_entry(object.meta_filename, {
            "ObjectUID": object.object_identifier,
            "Source": self.archive_creator_uri,
            "Dataset": self.dataset_id
        })
        
        # process the (optional) referenced file:
        if source_dir is not None:
            origin_filepath = os.path.join(source_dir, object.original_filename)
            dest_filepath  = os.path.join(self.sip_dir, object.filename)
            shutil.copy2(origin_filepath, dest_filepath)

            self.manifest.add_entry(object.filename, object.md5checksum, object.checksum_datetime) 
            self.manifest.update_entry(object.filename, {
                "ObjectUID": object.object_identifier,
                "Source": self.archive_creator_uri,
                "Dataset": self.dataset_id,
                "FileFormat": object.fileformat_uri,
                "OriginalFilename": object.original_filename
            })
        self.manifest.save()

    def _load_meta_resources(self):
        for filename in self.manifest.get_filenames():
            if filename.endswith(f"{self.cfg.metadata_suffix}.json"):
                file_path = os.path.join(self.sip_dir, filename)
                id = util.extract_id_from_filename(file_path)
                self.meta_resources[id] = StructuredMetaResource(id=id)
                self.meta_resources[id].load(file_path)
