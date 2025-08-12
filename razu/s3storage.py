import os
import tempfile
import hashlib
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv
import mimetypes
import urllib.parse


class S3Storage:
    """
    Provides methods for interacting with an S3-compatible storage service.

    It includes functionalities to:
    - Check or create a bucket
    - Upload files with metadata
    - List objects in a bucket
    - Retrieve file metadata
    - Verify the integrity of uploads using MD5 checksums
    - Update and retrieve access control lists (ACLs) of objects
    - Retrieve the bucket policy
    - Check and retrieve block public access settings
    
    The class initializes an S3 client using credentials (endpoint, access key, and secret key)
    retrieved from environment variables. The credentials should be stored in a `.env` file.

    NOTE: On my client "sudo hwclock -s" is sometimes required (when clock is 'skewed')

    Attributes:
        endpoint (str): S3 service endpoint URL.
        access_key (str): Access key for S3 service.
        secret_key (str): Secret key for S3 service.
        s3_client (boto3.Client): Initialized S3 client for performing operations.
    """

    def __init__(self) -> None:
        """
        Initializes the S3 client with credentials and endpoint information from environment variables.
        The credentials and endpoint are loaded from a .env file.
        """
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(env_path)

        # Stel omgevingsvariabelen in om het MissingContentLength probleem op te lossen
        os.environ['AWS_REQUEST_CHECKSUM_CALCULATION'] = 'when_required'
        os.environ['AWS_RESPONSE_CHECKSUM_VALIDATION'] = 'when_required'

        self.endpoint = os.getenv('S3_ENDPOINT')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )

    def check_or_create_bucket(self, bucket_name, enable_versioning=False) -> bool:
        """
        Checks if a bucket exists in the S3 storage and creates it if it does not exist.
        
        :param bucket_name: The name of the bucket to check or create.
        :param enable_versioning: If True, enables versioning on the bucket after creation.
        :return: True if the bucket exists or was created successfully, False if an error occurred.
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            if enable_versioning:
                self.set_bucket_versioning(bucket_name)
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                print(f"Bucket '{bucket_name}' does not exist. Creating bucket.")
                try:
                    self.s3_client.create_bucket(Bucket=bucket_name)
                    print(f"Bucket '{bucket_name}' created successfully.")
                    
                    if enable_versioning:
                        self.set_bucket_versioning(bucket_name)
                        
                    return True
                except Exception as e:
                    print(f"Failed to create bucket '{bucket_name}': {e}")
                    return False
            else:
                print(f"An error occurred while checking bucket '{bucket_name}': {e}")
                return False
                
    def set_bucket_versioning(self, bucket_name, status="Enabled") -> bool:
        """
        Sets the versioning status on an S3 bucket.
        
        :param bucket_name: The name of the bucket to set versioning status on.
        :param status: The versioning status to set. Valid values are 'Enabled' or 'Suspended'.
                      Default is 'Enabled'.
        :return: True if versioning status was set successfully, False otherwise.
        """
        if status not in ["Enabled", "Suspended"]:
            print(f"Invalid versioning status: {status}. Valid values are 'Enabled' or 'Suspended'.")
            return False
            
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={
                    'Status': status
                }
            )
            print(f"Versioning status set to '{status}' for bucket '{bucket_name}'.")
            return True
        except Exception as e:
            print(f"Failed to set versioning status for bucket '{bucket_name}': {e}")
            return False

    def store_file(self, bucket_name, object_key, local_filename, metadata) -> None:
        """
        Uploads a file to the specified S3 bucket along with its metadata.

        :param bucket_name: The name of the bucket to upload the file to.
        :param filename: The local path of the file to upload.
        :param metadata: A dictionary containing metadata for the uploaded file.
        """
        try:
            # Controleer of het bestand bestaat
            if not os.path.exists(local_filename):
                raise FileNotFoundError(f"The file {local_filename} was not found.")
                
            # Bepaal het MIME-type
            mime_type, _ = mimetypes.guess_type(object_key)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            # Maak de extra argumenten voor de upload
            extra_args = {
                "Metadata": self._encode_metadata(metadata), 
                "ContentType": mime_type
            }
            
            
            # Gebruik upload_file in plaats van put_object voor grote bestanden
            # upload_file handelt automatisch de bestandsgrootte en chunking af
            self.s3_client.upload_file(
                local_filename,
                bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            print(f"File {local_filename} uploaded successfully to {bucket_name}: {object_key} .")
        except FileNotFoundError:
            print(f"The file {local_filename} was not found.")
        except NoCredentialsError:
            print("Credentials not available.")
        except Exception as e:
            print(f"An error occurred: Failed to upload {local_filename} to {bucket_name}: {object_key}: {e}")

    def get_file_metadata(self, bucket: str, file_key: str) -> dict:
        """
        Retrieves the metadata of a specific file (object) from an S3 bucket.
        
        :param bucket: The name of the bucket where the file is stored.
        :param file_key: The key (filename) of the object in the bucket.
        :return: The metadata of the file, or None if the file or bucket does not exist.
        """
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=file_key)
            metadata = response.get('Metadata', {})
            #print(f"Metadata for '{file_key}' in bucket '{bucket}': {metadata}")
            return metadata
        except ClientError as e:
            # For missing objects or buckets, return None silently so callers can treat it as "does not exist".
            code = e.response.get('Error', {}).get('Code')
            if code in ('404', 'NotFound', 'NoSuchKey', 'NoSuchBucket'):
                return None
            # Other client errors should not be swallowed; re-raise to surface real issues.
            raise
        except Exception as e:
            # Unexpected exceptions should be propagated to aid debugging.
            raise

    def verify_upload(self, bucket_name, file_key, local_md5) -> None:
        """
        Verifies if a file was correctly uploaded by comparing its local MD5 checksum with the S3 ETag.

        :param bucket_name: The name of the bucket containing the file.
        :param file_key: The key (filename) of the uploaded file.
        :param local_md5: The MD5 checksum of the local file to compare against the uploaded file.
        """

        def calculate_md5(file_path):
            """Calculates the MD5 checksum of a file."""
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()

        response = self.s3_client.head_object(Bucket=bucket_name, Key=file_key)
        s3_etag = response['ETag'].strip('"')
        
        # Check for multi-part upload (S3 ETags of multi-part uploads contain '-' and part count)
        if '-' in s3_etag:
            print(f"Multi-part upload detected for {file_key}. Downloading file for verification...")
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                download_path = temp_file.name
            self.s3_client.download_file(bucket_name, file_key, download_path)
            downloaded_md5 = calculate_md5(download_path)
            if downloaded_md5 == local_md5:
                print(f"Multi-part upload verification successful: {file_key}")
            else:
                print(f"Multi-part upload verification failed for {file_key}. Local MD5: {local_md5}, Downloaded MD5: {downloaded_md5}")
            os.remove(download_path)
        else:
            if local_md5 == s3_etag:
                print(f"Upload verification successful: {file_key}")
            else:
                print(f"Upload verification failed for {file_key}. Local MD5: {local_md5}, S3 ETag: {s3_etag}")

    def update_acl(self, bucket_name, file_key, acl="public-read") -> None:
        """
        Updates the ACL (Access Control List) for a specific object in the S3 bucket.

        :param bucket_name: The name of the bucket containing the object.
        :param file_key: The key (filename) of the object whose ACL will be updated.
        :param acl: The ACL to apply, default is 'public-read'.
        """
        try:
            response = self.s3_client.put_object_acl(Bucket=bucket_name, Key=file_key, ACL=acl)
            print(f"ACL updated for {file_key} to {acl}.")
        except Exception as e:
            print(f"An error occurred while updating ACL: {e}")
        
    def get_bucket_contents(self, bucket_name: str, prefix: str = None) -> list:
        """
        Gets a list of all object keys in the specified S3 bucket using pagination.
        
        :param bucket_name: The name of the bucket to list objects from.
        :param prefix: Optional prefix to filter the listed objects.
        :return: List of all object keys in the bucket (optionally filtered by prefix).
        """
        paginator = self.s3_client.get_paginator('list_objects_v2')
        pagination_params = {'Bucket': bucket_name}
        if prefix:
            pagination_params['Prefix'] = prefix

        page_iterator = paginator.paginate(**pagination_params)

        all_keys = []
        for page in page_iterator:
            contents = page.get('Contents', [])
            all_keys.extend(obj['Key'] for obj in contents)

        return all_keys

    
    def get_bucket_policy(self, bucket_name) -> str:
        """
        Retrieves the policy of a specific S3 bucket.

        :param bucket_name: The name of the bucket to retrieve the policy from.
        :return: The bucket policy, or None if no policy is found.
        """
        try:
            response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
            print(f"Bucket policy for {bucket_name}: {response['Policy']}")
            return response['Policy']
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucketPolicy':
                print(f"No bucket policy found for {bucket_name}.")
                return ""
            else:
                print(f"An error occurred: {e}")
                return ""
            
    def get_object_acl(self, bucket_name, file_key):
        """
        Retrieves the ACL of a specific object in an S3 bucket.

        :param bucket_name: The name of the bucket containing the object.
        :param file_key: The key (filename) of the object.
        """
        try:
            response = self.s3_client.get_object_acl(Bucket=bucket_name, Key=file_key)
            for grant in response['Grants']:
                print(f"Grantee: {grant['Grantee']}, Permission: {grant['Permission']}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def get_block_public_access(self, bucket_name):
        """
        Checks if Block Public Access is enabled for a specific S3 bucket.

        :param bucket_name: The name of the bucket to check for Block Public Access configuration.
        :return: The public access block configuration, or None if not found.
        """
        try:
            response = self.s3_client.get_public_access_block(Bucket=bucket_name)
            block_config = response['PublicAccessBlockConfiguration']
            print(f"Block Public Access settings for {bucket_name}: {block_config}")
            return block_config
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchPublicAccessBlockConfiguration':
                print(f"No Block Public Access configuration found for {bucket_name}.")
            else:
                print(f"An error occurred: {e}")
            return None

    def list_buckets(self):
        """
        Lists all available buckets.

        Returns:
            list: A list of dictionaries containing bucket information.
                  Each dictionary contains 'Name' and 'CreationDate' of the bucket.

        Raises:
            NoCredentialsError: If credentials are not properly configured.
            ClientError: If there's an error in the S3 client operation.
        """
        try:
            response = self.s3_client.list_buckets()
            return response['Buckets']
        except (NoCredentialsError, ClientError) as e:
            raise e

    def get_bucket_versioning(self, bucket_name) -> str:
        """
        Gets the versioning status of an S3 bucket.
        
        :param bucket_name: The name of the bucket to check versioning status for.
        :return: The versioning status ('Enabled', 'Suspended', or 'Not enabled') of the bucket.
        """
        try:
            response = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
            
            # If 'Status' key exists in the response, versioning is either Enabled or Suspended
            if 'Status' in response:
                status = response['Status']
                print(f"Versioning status for bucket '{bucket_name}': {status}")
                return status
            else:
                print(f"Versioning is not enabled for bucket '{bucket_name}'.")
                return "Not enabled"
        except Exception as e:
            print(f"Failed to get versioning status for bucket '{bucket_name}': {e}")
            return "Error"

    def delete_bucket(self, bucket_name, force=False) -> bool:
        """
        Deletes an S3 bucket. By default, the bucket must be empty.
        
        :param bucket_name: The name of the bucket to delete.
        :param force: If True, all objects in the bucket will be deleted before deleting the bucket.
        :return: True if the bucket was deleted successfully, False otherwise.
        """
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=bucket_name)
            
            # If force is True, delete all objects in the bucket first
            if force:
                print(f"Force option enabled. Deleting all objects in bucket '{bucket_name}'...")
                
                # List and delete all object versions if versioning is enabled
                try:
                    # Check if versioning is enabled
                    versioning_status = self.get_bucket_versioning(bucket_name)
                    if versioning_status == "Enabled" or versioning_status == "Suspended":
                        # Delete all versions and delete markers
                        versions_response = self.s3_client.list_object_versions(Bucket=bucket_name)
                        
                        # Delete versions
                        if 'Versions' in versions_response:
                            for version in versions_response['Versions']:
                                self.s3_client.delete_object(
                                    Bucket=bucket_name,
                                    Key=version['Key'],
                                    VersionId=version['VersionId']
                                )
                        
                        # Delete delete markers
                        if 'DeleteMarkers' in versions_response:
                            for marker in versions_response['DeleteMarkers']:
                                self.s3_client.delete_object(
                                    Bucket=bucket_name,
                                    Key=marker['Key'],
                                    VersionId=marker['VersionId']
                                )
                except Exception as e:
                    print(f"Error deleting versioned objects: {e}")
                    return False
                
                # Delete all non-versioned objects
                try:
                    objects_response = self.s3_client.list_objects_v2(Bucket=bucket_name)
                    if 'Contents' in objects_response:
                        for obj in objects_response['Contents']:
                            self.s3_client.delete_object(
                                Bucket=bucket_name,
                                Key=obj['Key']
                            )
                except Exception as e:
                    print(f"Error deleting objects: {e}")
                    return False
                
                print(f"All objects in bucket '{bucket_name}' have been deleted.")
            
            # Delete the bucket
            self.s3_client.delete_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' deleted successfully.")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"Bucket '{bucket_name}' does not exist.")
            elif error_code == 'BucketNotEmpty':
                print(f"Bucket '{bucket_name}' is not empty. Use force=True to delete all objects first.")
            else:
                print(f"Failed to delete bucket '{bucket_name}': {e}")
            return False
        except Exception as e:
            print(f"An error occurred while deleting bucket '{bucket_name}': {e}")
            return False

    def delete_file(self, bucket_name, file_key):
        """
        Deletes a specific file (object) from an S3 bucket.
        
        :param bucket_name: The name of the bucket containing the file to delete.
        :param file_key: The key (filename) of the object to delete.
        :return: True if the file was deleted successfully, False otherwise.
        """
        try:
            # Check if the bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    print(f"Bucket '{bucket_name}' does not exist.")
                    return False
                raise
                
            # Delete the file
            self.s3_client.delete_object(Bucket=bucket_name, Key=file_key)
            print(f"File '{file_key}' deleted successfully from bucket '{bucket_name}'.")
            return True
            
        except ClientError as e:
            print(f"Failed to delete file '{file_key}' from bucket '{bucket_name}': {e}")
            return False
        except Exception as e:
            print(f"An error occurred while deleting file '{file_key}' from bucket '{bucket_name}': {e}")
            return False
            
    def _encode_metadata(self, metadata):
        """
        URL encode metadata values to handle non-ASCII characters.
        
        :param metadata: Dictionary with metadata
        :return: Dictionary with URL-encoded metadata values
        """
        encoded_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                encoded_metadata[key] = urllib.parse.quote(value)
            else:
                encoded_metadata[key] = urllib.parse.quote(str(value))
        return encoded_metadata
