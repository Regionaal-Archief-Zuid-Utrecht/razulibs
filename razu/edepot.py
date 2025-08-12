import os
import json
from rdflib.namespace import SKOS
from typing import Any, Callable, TypeVar, Optional, Dict, List, Union

from razu.concept_resolver import Concept
from razu.manifest import Manifest
from razu.s3storage import S3Storage

T = TypeVar('T')

class EDepot(S3Storage):
    """
    Provides RAZU-specific e-depot functionality, extending the S3Storage class.

    Inherits from:
        S3Storage: A class that provides S3 storage interaction methods.
    """

    @staticmethod
    def _get_bucket_name(manifest_file):
        """
        Bepaalt de bucket name als het padsegment na 'nl-wbdrazu' in het manifest_file pad.
        Gooit een exception als dit niet lukt.

        :param manifest_file: Het pad naar het manifest-bestand.
        :return: De bucket name als string.
        """
        manifest_path = os.path.normpath(manifest_file)
        if 'nl-wbdrazu' in manifest_path:
            after = manifest_path.split('nl-wbdrazu', 1)[1]
            segments = after.strip(os.sep).split(os.sep)
            if segments and segments[0]:
                return segments[0]
            else:
                raise ValueError(f"Kan bucket_name niet bepalen uit manifest_file: '{manifest_file}' (geen segment na 'nl-wbdrazu')")
        else:
            raise ValueError(f"Kan bucket_name niet bepalen uit manifest_file: '{manifest_file}' (geen 'nl-wbdrazu' in pad)")

    def print_output(self, method: Callable[..., T], *args, print_output: bool = True, 
                                  pretty_print: bool = True, **kwargs) -> Optional[T]:
        """
        A generic wrapper function that executes a method and either returns its result or prints it.

        Args:
            method: The method to execute.
            *args: Positional arguments to pass to the method.
            print_output: If True, prints the output instead of returning it.
            pretty_print: If True, formats the output for better readability (when printing).
            **kwargs: Keyword arguments to pass to the method.

        Returns:
            The result of the method if print_output is False, otherwise None.
        """
        result = method(*args, **kwargs)
        
        if print_output and result is not None:
            if pretty_print:
                if isinstance(result, (dict, list)):
                    print(json.dumps(result, indent=2, default=str))
                else:
                    print(result)
            else:
                print(result)
            return None
        
        return result

    def store_files_from_manifest(self, manifest_file, sip_directory, only_if_new=False):
        """
        Stores files listed in the manifest into their respective S3 buckets.

        :param manifest_file: The path to the manifest file.
        :param sip_directory: The directory where the files listed in the manifest are located.
        :param only_if_new: If True, only upload files if the key does not already exist in the bucket.
        """
        manifest = Manifest.load_existing(sip_directory, manifest_file)
        # Bepaal bucket_name één keer (op basis van eerste entry)
        # Bepaal bucket_name als het padsegment na 'nl-wbdrazu', zonder begin/eindslash
        bucket_name = self._get_bucket_name(manifest_file)
        print(f"{manifest_file} verwerken. Als key al bestaat dan wordt er niets geprint.")
        for key, entry in manifest.entries.items():
            local_filename = os.path.join(sip_directory, key)
            properties = entry.to_dict()
            #print(key)
            if only_if_new:
                # Check of de key al bestaat in de bucket
                meta = self.get_file_metadata(bucket_name, key)
                if meta is not None:
                    #print(f"SKIP: {key} bestaat al in bucket {bucket_name}")
                    continue
            self.store_file(bucket_name, key, local_filename, properties)

        # Upload manifest file zelf
        manifest_rel_key = os.path.relpath(manifest_file, sip_directory)
        print(manifest_rel_key)
        self.store_file(bucket_name, manifest_rel_key, manifest_file, {})

    def validate_uploaded_files_from_manifest(self, manifest_file, sip_directory):
        """
        Validates that files listed in the manifest were correctly uploaded by comparing their checksums.

        :param manifest_file: The path to the manifest file.
        :param sip_directory: The directory where the files listed in the manifest are located.
        """
        manifest = Manifest.load_existing(sip_directory, manifest_file)
        bucket_name = self._get_bucket_name(manifest_file)
        for filename, entry in manifest.entries.items():
            properties = entry.to_dict()
            md = properties["MD5Hash"]
            self.verify_upload(bucket_name, filename, md)

    def update_acl_from_manifest(self, manifest_file, sip_directory, acl="public-read"):
        """
        Updates the access control list (ACL) of files in S3 based on the manifest.

        :param manifest_file: The path to the manifest file.
        :param sip_directory: The directory where the files listed in the manifest are located.
        :param acl: The access control list setting to apply to the files (default is 'public-read').
        """
        manifest = Manifest.load_existing(sip_directory, manifest_file)
        bucket_name = self._get_bucket_name(manifest_file)
        for key, entry in manifest.entries.items():
            properties = entry.to_dict()
            print(f"{bucket_name} {key}, {acl}")
            self.update_acl(bucket_name, key, acl)
