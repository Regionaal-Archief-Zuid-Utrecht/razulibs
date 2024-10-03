import os

from rdflib.namespace import SKOS

from razu.concept_resolver import Concept
from razu.manifest import Manifest
from razu.s3storage import S3Storage


class EDepot(S3Storage):
    """
    Provides RAZU-specific e-depot functionality, extending the S3Storage class.

    Inherits from:
        S3Storage: A class that provides S3 storage interaction methods.
    """

    def _get_bucket_name(self, properties):
        """
        Retrieves the bucket name from the properties of a file in the manifest.

        :param properties: A dictionary of file properties from the manifest.
        :return: The bucket name as a lowercase string.
        """
        return Concept(properties["Source"]).get_value(SKOS.notation).lower()

    def store_files_from_manifest(self, manifest_file, sip_directory):
        """
        Stores files listed in the manifest into their respective S3 buckets.

        :param manifest_file: The path to the manifest file.
        :param sip_directory: The directory where the files listed in the manifest are located.
        """
        manifest = Manifest(sip_directory, manifest_file)
        for filename, properties in manifest.files.items():
            full_filename = os.path.join(sip_directory, filename)
            bucket_name = self._get_bucket_name(properties)
            self.store_file(bucket_name, full_filename, properties)

    def validate_uploaded_files_from_manifest(self, manifest_file, sip_directory):
        """
        Validates that files listed in the manifest were correctly uploaded by comparing their checksums.

        :param manifest_file: The path to the manifest file.
        :param sip_directory: The directory where the files listed in the manifest are located.
        """
        manifest = Manifest(sip_directory, manifest_file)
        for filename, properties in manifest.files.items():
            bucket_name = self._get_bucket_name(properties)
            md = properties["MD5Hash"]
            self.verify_upload(bucket_name, filename, md)

    def update_acl_from_manifest(self, manifest_file, sip_directory, acl="public-read"):
        """
        Updates the access control list (ACL) of files in S3 based on the manifest.

        :param manifest_file: The path to the manifest file.
        :param sip_directory: The directory where the files listed in the manifest are located.
        :param acl: The access control list setting to apply to the files (default is 'public-read').
        """
        manifest = Manifest(sip_directory, manifest_file)
        for filename, properties in manifest.files.items():
            bucket_name = self._get_bucket_name(properties)
            self.update_acl(bucket_name, filename, acl)
