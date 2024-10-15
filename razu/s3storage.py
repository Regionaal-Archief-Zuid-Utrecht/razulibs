import os
import tempfile
import hashlib
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv


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

    def __init__(self):
        """
        Initializes the S3 client with credentials and endpoint information from environment variables.
        The credentials and endpoint are loaded from a .env file.
        """
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(env_path)

        self.endpoint = os.getenv('S3_ENDPOINT')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )

    def check_or_create_bucket(self, bucket_name):
        """
        Checks if a bucket exists in the S3 storage and creates it if it does not exist.
        
        :param bucket_name: The name of the bucket to check or create.
        :return: True if the bucket exists or was created successfully, False if an error occurred.
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                print(f"Bucket '{bucket_name}' does not exist. Creating bucket.")
                try:
                    self.s3_client.create_bucket(Bucket=bucket_name)
                    print(f"Bucket '{bucket_name}' created successfully.")
                    return True
                except Exception as e:
                    print(f"Failed to create bucket '{bucket_name}': {e}")
                    return False
            else:
                print(f"An error occurred while checking bucket '{bucket_name}': {e}")
                return False

    def store_file(self, bucket_name, filename, metadata):
        """
        Uploads a file to the specified S3 bucket along with its metadata.

        :param bucket_name: The name of the bucket to upload the file to.
        :param filename: The local path of the file to upload.
        :param metadata: A dictionary containing metadata for the uploaded file.
        """
        try:
            self.s3_client.upload_file(
                filename,
                bucket_name,
                os.path.basename(filename),
                ExtraArgs={"Metadata": metadata}
            )
            print(f"File {filename} uploaded successfully.")
        except FileNotFoundError:
            print(f"The file {filename} was not found.")
        except NoCredentialsError:
            print("Credentials not available.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def ls(self, bucket_name: str):
        """
        Lists the objects in the specified S3 bucket.

        :param bucket_name: The name of the bucket to list objects from.
        """
        response = self.s3_client.list_objects_v2(Bucket=bucket_name)
        for obj in response.get('Contents', []):
            print(obj['Key'])

    def get_file_metadata(self, bucket: str, file_key: str):
        """
        Retrieves the metadata of a specific file (object) from an S3 bucket.
        
        :param bucket: The name of the bucket where the file is stored.
        :param file_key: The key (filename) of the object in the bucket.
        :return: The metadata of the file, or None if the file or bucket does not exist.
        """
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=file_key)
            metadata = response.get('Metadata', {})
            print(f"Metadata for '{file_key}' in bucket '{bucket}': {metadata}")
            return metadata
        except self.s3_client.exceptions.NoSuchKey:
            print(f"File '{file_key}' does not exist in bucket '{bucket}'.")
        except self.s3_client.exceptions.NoSuchBucket:
            print(f"Bucket '{bucket}' does not exist.")
        except Exception as e:
            print(f"An error occurred while retrieving metadata: {e}")
            return None

    def verify_upload(self, bucket_name, file_key, local_md5):
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

    def update_acl(self, bucket_name, file_key, acl="public-read"):
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
        
    def get_bucket_policy(self, bucket_name):
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
                return None
            else:
                print(f"An error occurred: {e}")
                return None
            
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
