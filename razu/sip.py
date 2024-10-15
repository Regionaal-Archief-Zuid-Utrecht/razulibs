import os
import shutil

from datetime import datetime
from rdflib import URIRef, BNode

from .razuconfig import RazuConfig
from .concept_resolver import ConceptResolver
from .meta_object import MetaObject
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
        
        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.cfg = RazuConfig(archive_creator_id=archive_creator_id, archive_id=dataset_id, save_dir=sip_dir, save=True)

        if not os.path.exists(self.sip_dir):
            os.makedirs(self.sip_dir)
            print(f"Created empty SIP at {self.sip_dir}.")

        self.graph = MetaGraph()
        self.manifest = Manifest(self.sip_dir, self.cfg.manifest_filename)

        self.id_manager = IDManager()
        for filename in self.manifest.get_filenames():
            if filename.endswith(f'{self.cfg.metadata_suffix}.json'):
                self.id_manager.register_id(util.extract_id_from_filename(filename))
        
        if self.id_manager.get_count() > 0:
            self._load_graph()

    def _load_graph(self):
        for filename in self.manifest.get_filenames():
            if filename.endswith(f"{self.cfg.metadata_suffix}.json"):
                rdf = MetaGraph()
                file_path = os.path.join(self.sip_dir, filename)
                rdf.parse(file_path, format="json-ld")
                self.graph += rdf

    def save_graph(self):
        """
        For each unique entity in the graph with a URI, create a MetaObject, fill it with the relevant
        properties (and blank nodes), and store it.
        """
        def add_related_triples_to_meta_object(meta_object, node, processed_nodes=None):
            """ Recursively add triples related to the given node (including blank nodes) to the MetaObject. """
            if processed_nodes is None:
                processed_nodes = set()  # Houd de verwerkte nodes bij

            if node in processed_nodes:
                return  # Voorkom dubbele verwerking van dezelfde node

            processed_nodes.add(node)

            for predicate, obj in self.graph.predicate_objects(node):
                meta_object.add(predicate, obj)

                if isinstance(obj, BNode):
                    # Verwerk blank nodes recursief
                    add_related_triples_to_meta_object(meta_object, obj, processed_nodes)

        processed_subjects = set()  # Houd bij welke subjects zijn verwerkt

        for subject in self.graph.subjects():
            if isinstance(subject, URIRef) and subject not in processed_subjects:
                meta_object = MetaObject(uri=subject)
                add_related_triples_to_meta_object(meta_object, subject)
                self.save_object_metadata(meta_object)
                processed_subjects.add(subject)  # Voeg het subject toe aan de set van verwerkte subjects


    def create_object(self, entity_id = None, rdf_type = None):
        kwargs = {}
        if entity_id is None:
            kwargs['entity_id'] = self.id_manager.generate_id()
        else:
            kwargs['entity_id'] = self.id_manager.register_id(entity_id)

        if rdf_type is not None:
            kwargs['rdf_type'] = rdf_type

        return MetaObject(**kwargs)


    def save_object_metadata(self, object: MetaObject, source_dir = None):
        object.save()
        md5checksum = self.manifest.calculate_md5(object.meta_file_path)
        md5date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.manifest.add_entry(object.meta_filename, md5checksum, md5date) 
        self.manifest.update_entry(object.meta_filename, {
            "ObjectUID": object.object_identifier,
            "Source": self.archive_creator_uri,
            "Dataset": self.dataset_id
        })
        self.manifest.save()


    def save_object_file(self, object: MetaObject, source_dir = None):
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


    def store_object(self, object: MetaObject, source_dir = None):
        # process the metadata-file:
        self.graph += object
        self.save_object_metadata(object, source_dir)
        
        # process the (optional) referenced file:
        if source_dir is not None:
            self.save_object_file(object, source_dir)
            

    def validate(self):
        self.manifest.verify()
