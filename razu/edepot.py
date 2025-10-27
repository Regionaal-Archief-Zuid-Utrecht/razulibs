import os
import json
from datetime import datetime
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

    @staticmethod
    def create_date_filter(after_date: str):
        """
        Create a filter function that only includes files with MD5HashDate after the specified date.
        
        :param after_date: Date string in ISO format (e.g., '2024-01-01T00:00:00')
        :return: Filter function for use with store_files_from_manifest
        """
        def date_filter(key, entry):
            if not entry.md5date:
                return True  # Include files without date
            return entry.md5date >= after_date
        return date_filter
    
    @staticmethod
    def create_modified_files_filter(reference_manifest_file: str, sip_directory: str):
        """
        Create a filter that only includes files that have different checksums compared to a reference manifest.
        
        :param reference_manifest_file: Path to the reference manifest file
        :param sip_directory: Directory containing the reference manifest
        :return: Filter function for use with store_files_from_manifest
        """
        try:
            reference_manifest = Manifest.load_existing(sip_directory, reference_manifest_file)
            reference_checksums = {key: entry.md5hash for key, entry in reference_manifest.entries.items()}
            
            def checksum_filter(key, entry):
                # Include file if it's new or has different checksum
                return key not in reference_checksums or reference_checksums[key] != entry.md5hash
            return checksum_filter
        except FileNotFoundError:
            # If reference manifest doesn't exist, include all files
            return lambda key, entry: True

    def store_files_from_manifest(self, manifest_file, sip_directory, only_if_new=False, file_filter=None):
        """
        Stores files listed in the manifest into their respective S3 buckets.

        :param manifest_file: The path to the manifest file.
        :param sip_directory: The directory where the files listed in the manifest are located.
        :param only_if_new: If True, only upload files if the key does not already exist in the bucket.
        :param file_filter: Optional callable that takes (key, entry) and returns True if file should be uploaded.
                           Example: lambda key, entry: entry.md5date >= '2024-01-01T00:00:00'
        """
        manifest = Manifest.load_existing(sip_directory, manifest_file)
        # Bepaal bucket_name één keer (op basis van eerste entry)
        # Bepaal bucket_name als het padsegment na 'nl-wbdrazu', zonder begin/eindslash
        bucket_name = self._get_bucket_name(manifest_file)
        print(f"{manifest_file} verwerken.")
        
        filtered_count = 0
        uploaded_count = 0
        
        for key, entry in manifest.entries.items():
            local_filename = os.path.join(sip_directory, key)
            properties = entry.to_dict()
            
            # Apply custom filter if provided
            if file_filter and not file_filter(key, entry):
                filtered_count += 1
                print(f"SKIP-FILTERED: {key}", end="\r")
                continue
                
            if only_if_new:
                # Check of de key al bestaat in de bucket
                meta = self.get_file_metadata(bucket_name, key)
                if meta is not None:
                    print(f"SKIP-EXISTING: {key}", end="\r")
                    continue
                    
            self.store_file(bucket_name, key, local_filename, properties)
            uploaded_count += 1

        print(f"\nUpload voltooid: {uploaded_count} bestanden geüpload, {filtered_count} gefilterd.")

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

    def update_acl_from_manifest(self, manifest_file, sip_directory, acl="public-read", file_filter=None):
        """
        Updates the access control list (ACL) of files in S3 based on the manifest.

        :param manifest_file: The path to the manifest file.
        :param sip_directory: The directory where the files listed in the manifest are located.
        :param acl: The access control list setting to apply to the files (default is 'public-read').
        :param file_filter: Optional callable that takes (key, entry) and returns True if ACL should be updated.
        """
        manifest = Manifest.load_existing(sip_directory, manifest_file)
        bucket_name = self._get_bucket_name(manifest_file)
        
        filtered_count = 0
        updated_count = 0
        
        for key, entry in manifest.entries.items():
            # Apply custom filter if provided
            if file_filter and not file_filter(key, entry):
                filtered_count += 1
                print(f"SKIP-FILTERED: {key}", end="\r")
                continue
                
            properties = entry.to_dict()
            print(f"{bucket_name} {key}, {acl}")
            self.update_acl(bucket_name, key, acl)
            updated_count += 1
            
        # Update the ACL of the manifest file itself if any file ACL was updated
        if updated_count > 0:
            manifest_rel_key = os.path.relpath(manifest_file, sip_directory)
            print(f"{bucket_name} {manifest_rel_key}, {acl} (manifest)")
            self.update_acl(bucket_name, manifest_rel_key, acl)
            
        print(f"\nACL update voltooid: {updated_count} bestanden bijgewerkt, {filtered_count} gefilterd.")
