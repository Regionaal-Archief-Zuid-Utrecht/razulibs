import os
import shutil

from datetime import datetime
from rdflib import URIRef, BNode

from .razuconfig import RazuConfig
from .concept_resolver import ConceptResolver
from .meta_resource import StructuredMetaResource
from .meta_graph import MetaGraph
from .manifest import Manifest
from .id_manager import IDManager
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

        self.id_manager = IDManager()
        for filename in self.manifest.get_filenames():
            if filename.endswith(f'{self.cfg.metadata_suffix}.json'):
                self.id_manager.register_id(util.extract_id_from_filename(filename))
        
        if self.id_manager.get_count() > 0:
            self._load_graph()

    def export_rdf(self, format = 'turtle'):
        graph = MetaGraph()
        for key in self.meta_resources:
            graph += self.meta_resources[key].graph
        print(graph.serialize(format=format))

    def _load_graph(self):
        for filename in self.manifest.get_filenames():
            if filename.endswith(f"{self.cfg.metadata_suffix}.json"):
                id = util.extract_id_from_filename(filename)
                meta_resource = StructuredMetaResource(id=id)
                meta_resource.load()
                self.meta_resources[id] = meta_resource




    def create_object(self, entity_id = None, rdf_type = None):
        kwargs = {}
        if entity_id is None:
            kwargs['id'] = self.id_manager.generate_id()
        else:
            kwargs['id'] = self.id_manager.register_id(entity_id)

        if rdf_type is not None:
            kwargs['rdf_type'] = rdf_type

        return StructuredMetaResource(**kwargs)


    def save_metadata(self, object: StructuredMetaResource, source_dir = None):
        object.save()
        md5checksum = self.manifest.calculate_md5(object.file_path)
        md5date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.manifest.add_entry(object.filename, md5checksum, md5date) 
        self.manifest.update_entry(object.filename, {
            "ObjectUID": object.uid,
            "Source": self.archive_creator_uri,
            "Dataset": self.dataset_id
        })
        self.manifest.save()


    def _save_ext_file(self, object: StructuredMetaResource, source_dir = None):
        origin_filepath = os.path.join(source_dir, object.ext_file_original_filename)
        dest_filepath  = os.path.join(self.sip_dir, object.ext_filename)
        shutil.copy2(origin_filepath, dest_filepath)

        self.manifest.add_entry(object.ext_filename, object.ext_file_md5checksum, object.ext_file_checksum_datetime) 
        self.manifest.update_entry(object.filename, {
            "ObjectUID": object.uid,
            "Source": self.archive_creator_uri,
            "Dataset": self.dataset_id,
            "FileFormat": object.ext_file_fileformat_uri,
            "OriginalFilename": object.ext_file_original_filename
        })
        self.manifest.save()


    def store_object(self, object: StructuredMetaResource, source_dir = None):
        self.save_metadata(object, source_dir)
        
        # process the (optional) referenced file:
        if source_dir is not None:
            self._save_ext_file(object, source_dir)
            

    def validate(self):
        self.manifest.verify()
