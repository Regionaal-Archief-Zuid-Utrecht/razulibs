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

        N.B. this function is used in store_files_from_manifest method but it doesn't necessarily work. it uses the os separator (ex. /) to split the path and find the bucket name.
        It will not work if manifest files are stored with a name like"NL-WbDRAZU-K50907905-500" using hyphens.
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

    def delete_files_from_manifest(self, manifest_file, bucket_name):
            """
            Delete files from S3 based on the manifest keys.
            
            :param manifest_file: The path to the manifest file.
            :param bucket_name: The name of the bucket where the files are stored.

            The method first uses the 'get_bucket_contents' to find objects in the bucket that correspond to the prefix in the manifest (ex.NL-WbDRAZU-K50907905-500).
            Both the list of object/keys in the manifest and the list of relative objects found in the bucket are logged as two separate txt files for comparison
            Then the list of objects find in the s3 is structured as required for input of the 'delete_objects' method (ex. 'Objects': [{Key: 'L-WbDRAZU-test-500-47.meta.json'}, {Key: 'L-WbDRAZU-test-500-48.meta.json'}])
            This payload is also logged as a txt file.
            After prompting the user twice, the 'delete_objects' method is called with the list of objects found in s3 to delete 'objects to delete'.
            Since the delete_objects method in boto3 doesn't flag files not found as errors but simply saves them in the 'Deleted' list, we call again 'get_bucket_contents' to find objects in the bucket that correspond to the prefix in the manifest
            If by any chance, some files were not deleted they are logged in the delete_log files as well under key 'NotDeleted'

            """
            # Load manifest and get toegang prefix
            manifest = Manifest.load_existing(save_directory=os.path.dirname(manifest_file), manifest_filename=os.path.basename(manifest_file))
            manifest_prefix = manifest.manifest_filename.split(".")[0]

            # save list of objects in manifest
            with open("logs/objects_in_manifest.txt", "w") as f:
                for key in manifest.entries.keys():
                    f.write(f"{key}\n")

            # Find objects in S3 and save them
            s3_objects_found_from_manifest = self.get_bucket_contents(bucket_name, manifest_prefix)
            with open("logs/s3_objects_found_from_manifest.txt", "w") as f:
                for item in s3_objects_found_from_manifest:
                    f.write(f"{item}\n")

            # Empty list of objects to delete
            objects_to_delete = []

            # Iterate over keys of objects to delete found in the s3 bucket and create the required argument for delete_objects
            for key in s3_objects_found_from_manifest:
                keys_dictionary = {"Key": key}
                objects_to_delete.append(keys_dictionary)

            # Write log file to save keys that will be passed as arguments: should be the same as s3_objects_found_from_manifest
            with open("logs/objects_to_delete.txt", "w") as f:
                for item in objects_to_delete:
                    f.write(f"{item}\n")

            # Get user confirmation 
            input(f"There are {len(manifest.entries)} objects in the manifest, of which {len(s3_objects_found_from_manifest)} were found in the bucket.\n\nPress Enter to continue...")
            # Print objects to delete for check
            print("The following objects will be deleted:")
            for item in objects_to_delete:
                print(item)
            sure = input("Are you sure you want to delete these files?  ‼️THIS CANNOT BE UNDONE‼️ Type 'yes' to confirm:     ")
            if sure.lower() != "yes":
                print("Operation Cancelled.")
                return
            else:
                sure2 = input(" Are you sure sure sure sure sure you want to delete these files?  ‼️THIS CANNOT BE UNDONE‼️ Type 'yes' to confirm:  ")
                if sure.lower() == "yes" and sure2.lower() == "yes":

                    # Delete objects in batches of 1000 (S3 delete_objects supports up to 1000 objects at a time)
                    print("Deleting files...")

                    # Helper to yield batches of 1000 objects
                    def get_batches(items, batch_size=1000):
                        start = 0
                        while start < len(items):
                            end = start + batch_size
                            yield items[start:end]
                            start = end

                    all_deleted = []
                    all_errors = []

                    # Delete objects in batches
                    for batch in get_batches(objects_to_delete, 1000): # wrong, i need to put those actually in the bucket here!
                        response = self.s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": batch})
                        if "Deleted" in response:
                            all_deleted.extend(response["Deleted"])
                        if "Errors" in response:
                            all_errors.extend(response["Errors"])

                    # look again in the bucket to list objects corresponding to manifest keys (should be empty)         
                    failed_deleted = s3_objects_found_from_manifest = self.get_bucket_contents(bucket_name, manifest_prefix)
                    if len(failed_deleted) == 0:
                        print("All files deleted successfully.")
                    else:
                        print("The following files were not deleted:") 
                        for item in failed_deleted:
                            print(item)

                    # Save the response log
                    delete_log = {"Deleted": all_deleted, "Errors": all_errors, "NotDeleted": failed_deleted}

                    with open("logs/delete_log.json", "w") as f:
                        json.dump(delete_log, f, indent=4)

                    print(f"Deletion complete: {len(all_errors)} errors, {len(failed_deleted)} not deleted.")
                    if failed_deleted or len(all_errors) > 0:
                        print("Check delete_log.json for details.")

                else:
                    print("Operation Cancelled.")
                    return

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
