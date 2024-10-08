import os
import shutil

from datetime import datetime

from .razuconfig import RazuConfig
from .concept_resolver import ConceptResolver
from .meta_object import MetaObject
from .manifest import Manifest



class Sip:
    def __init__(self, sip_dir, archive_creator_id, dataset_id: str) -> None:
        self.sip_dir = sip_dir
        self.archive_creator_id = archive_creator_id
        self.dataset_id = dataset_id
        
        actoren = ConceptResolver('actor')
        self.archive_creator_uri = actoren.get_concept_uri(self.archive_creator_id)
        self.cfg = RazuConfig(archive_creator_id=archive_creator_id, archive_id=dataset_id, save_dir=sip_dir, save=True)
        self.manifest = Manifest(self.sip_dir, f"{self.cfg.filename_prefix}.manifest.json")

    def add_object(self, object: MetaObject, source_dir = None):
        # process the metadata-file:
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

    def validate(self):
        self.manifest.verify()
