from flask import current_app
import os
import boto3
from google.cloud import storage
from botocore.exceptions import NoCredentialsError, ClientError
import shutil
import glob
from datetime import timedelta
from app.utils.exceptions import FileDoesNotExist


class FileStorageHandler:
    def __init__(
        self,
        provider,
        s3_bucket_name=None,
        gcs_bucket_name=None,
        aws_access_key=None,
        aws_secret_key=None,
        region=None,
        skip_auth=False,
    ):
        self.provider = provider.lower()
        self.s3_bucket_name = s3_bucket_name
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.region = region
        self.gcs_bucket_name = gcs_bucket_name

        if self.provider not in ["local", "s3", "gcs"]:
            raise ValueError(
                "Invalid provider specified. Must be 'local', 's3', or 'gcs'."
            )
        if not skip_auth:
            self._refresh()

    def _refresh(self):
        # Initialize based on provider
        if self.provider == "local":
            return
        elif self.provider == "s3":
            self._initialize_s3(
                self.s3_bucket_name,
                self.aws_access_key,
                self.aws_secret_key,
                self.region,
            )
        elif self.provider == "gcs":
            self._initialize_gcs(self.gcs_bucket_name)
        else:
            raise ValueError("Unsupported provider")

    def _initialize_s3(self, s3_bucket_name, aws_access_key, aws_secret_key, region):
        self.s3_bucket_name = s3_bucket_name or current_app.config.get("AWS_BUCKET")
        if not self.s3_bucket_name:
            raise ValueError("s3_bucket_name is required for S3 storage")

        access_key = current_app.config.get("AWS_ACCESS_KEY") or aws_access_key
        secret_key = current_app.config.get("AWS_SECRET_KEY") or aws_secret_key
        region_name = current_app.config.get("AWS_REGION") or region

        if not access_key:
            current_app.logger.debug(
                "AWS_ACCESS_KEY is not configured, boto3 will try to use ADC"
            )
        if not secret_key:
            current_app.logger.debug(
                "AWS_SECRET_KEY is not configured, boto3 will try to use ADC"
            )
        if not region_name:
            current_app.logger.debug(
                "AWS_REGION is not configured, boto3 will try to use ADC"
            )

        if access_key and secret_key:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region_name,
            )
        else:
            self.s3_client = boto3.client("s3", region_name=region_name)

    def _initialize_gcs(self, gcs_bucket_name):
        self.gcs_bucket_name = gcs_bucket_name or current_app.config.get("GCS_BUCKET")
        if not self.gcs_bucket_name:
            raise ValueError("gcs_bucket_name is required for GCS storage")
        self.gcs_client = storage.Client()

    def _check_provider(self, required_provider):
        if self.provider != required_provider:
            raise ValueError(
                f"This instance is not configured for {required_provider} storage"
            )

    # Generic Methods
    def upload_file(self, file, file_name=None, folder=None, abs_path=None):
        """
        Upload file to a provider

        Parameters:
            file (str or file_object): Path to local file or file object
            file_name (str): Name to save the file as
            folder (str): folder to save the file in
            abs_path: (str): Full path to save the file as, overrides file_name and folder

        Returns:
            Path to the saved file
        """
        if self.provider == "local":
            return self.upload_to_local(
                file, file_name=file_name, folder=folder, abs_path=abs_path
            )
        elif self.provider == "s3":
            return self.upload_to_s3(
                file=file, file_name=file_name, folder=folder, abs_path=abs_path
            )
        elif self.provider == "gcs":
            return self.upload_to_gcs(
                file=file, file_name=file_name, folder=folder, abs_path=abs_path
            )

    def list_files(self, path):
        if self.provider == "local":
            return self.list_local_files(path=path)
        elif self.provider == "s3":
            return self.list_s3_files(path=path)
        elif self.provider == "gcs":
            return self.list_gcs_files(path=path)

    def get_file(self, path, as_blob=False):
        if self.provider == "local":
            return self.get_local_file(path=path, as_blob=as_blob)
        elif self.provider == "s3":
            return self.get_s3_file(path=path, as_blob=as_blob)
        elif self.provider == "gcs":
            return self.get_gcs_file(path=path, as_blob=as_blob)

    def delete_file(self, path):
        if self.provider == "local":
            return self.delete_local_file(path=path)
        elif self.provider == "s3":
            return self.delete_s3_file(path=path)
        elif self.provider == "gcs":
            return self.delete_gcs_file(path=path)

    def get_size(self, folder):
        if self.provider == "local":
            return self.get_local_size(folder=folder)
        elif self.provider == "s3":
            return self.get_s3_size(folder=folder)
        elif self.provider == "gcs":
            return self.get_gcs_size(folder=folder)

    def does_file_exist(self, abs_path):
        if self.provider == "local":
            return self.does_local_file_exist(abs_path)
        elif self.provider == "s3":
            return self.does_s3_file_exist(abs_path)
        elif self.provider == "gcs":
            return self.does_gcs_file_exist(abs_path)

    def does_local_file_exist(self, abs_path):
        if os.path.isfile(abs_path):
            return True
        return False

    def does_s3_file_exist(self, abs_path):
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket_name, Key=abs_path)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def does_gcs_file_exist(self, abs_path):
        bucket = self.gcs_client.bucket(self.gcs_bucket_name)
        blob = bucket.blob(abs_path)
        if blob.exists(self.gcs_client):
            return True
        return False

    def get_local_size(self, folder):
        """
        Does not calculate sub folders
        """
        folder = folder.rstrip(os.sep)
        return sum(
            os.path.getsize(f) for f in glob.glob(f"{folder}/*") if os.path.isfile(f)
        )

    def get_s3_size(self, folder):
        folder = folder.lstrip(os.sep)
        size = 0

        # List all objects under the folder prefix
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.s3_bucket_name, Prefix=folder):
            for obj in page.get("Contents", []):
                size += obj["Size"]
        return size

    def get_gcs_size(self, folder):
        size = 0

        # List all blobs (objects) with the specified prefix
        bucket = self.gcs_client.bucket(self.gcs_bucket_name)
        blobs = bucket.list_blobs(prefix=folder)
        for blob in blobs:
            size += blob.size
        return size

    def delete_local_file(self, path):
        try:
            os.remove(path)
            return True
        except FileNotFoundError:
            raise Exception(f"File not found for deletion:{path}")
        except Exception as e:
            raise Exception(f"Unknown error when deleting local file: {path}")

    def delete_s3_file(self, path):
        self._check_provider("s3")
        return self.s3_client.delete_object(Bucket=self.s3_bucket_name, Key=path)

    def delete_gcs_file(self, path):
        raise ValueError("Not Implemented")

    # Local Storage Methods
    def upload_to_local(self, file, file_name=None, folder=None, abs_path=None):
        self._check_provider("local")

        if not abs_path:
            if not folder:
                raise ValueError("folder is required without abs_path")
            if not file_name:
                raise ValueError("file_name is required without abs_path")
            abs_path = os.path.join(folder, file_name)

        # moving a file to another directory
        if isinstance(file, str):
            if not os.path.isfile(file):
                raise ValueError(f"File not found: {file}")
            shutil.move(file, abs_path)
        else:
            file.save(abs_path)
        return abs_path

    def list_local_files(self, path):
        self._check_provider("local")
        if not path:
            raise ValueError(f"Path is required: {path}")
        return os.listdir(path)

    def get_local_file(self, path, as_blob=False):
        self._check_provider("local")

        if not self.does_file_exist(path):
            raise FileDoesNotExist(f"File:{path} does not exist in local")

        if not path.startswith(current_app.config["EVIDENCE_FOLDER"]):
            path = os.path.join(current_app.config["EVIDENCE_FOLDER"], path)

        if as_blob:
            with open(path, "rb") as file:
                return file.read()

        return os.path.relpath(path, current_app.config["EVIDENCE_FOLDER"])

    # S3 Methods
    def upload_to_s3(self, file, file_name=None, folder=None, abs_path=None):
        self._check_provider("s3")

        if not abs_path:
            if not file_name:
                raise ValueError("file_name is required when abs_path is not specified")
            abs_path = file_name
            if folder:
                abs_path = os.path.join(folder, file_name)

        # remove leading /, otherwise s3 will see it as a folder
        abs_path = abs_path.lstrip(os.sep)

        try:
            if isinstance(file, str):
                if not os.path.isfile(abs_path):
                    raise ValueError(f"File not found:{abs_path}")
                self.s3_client.upload_file(file, self.s3_bucket_name, abs_path)
            else:
                self.s3_client.upload_fileobj(file, self.s3_bucket_name, abs_path)
            current_app.logger.debug(
                f"File '{file_name}' uploaded to S3 bucket '{self.s3_bucket_name}' at path '{abs_path}'"
            )
            return abs_path
        except FileNotFoundError:
            current_app.logger.error(f"The file '{file_name}' was not found.")
            return False
        except NoCredentialsError:
            current_app.logger.error("AWS credentials not available.")
            return False
        except ClientError as e:
            current_app.logger.error(f"An error occurred: {e}")
            return False

    def get_s3_file(self, path, as_presign=False, as_blob=False, save_to=None):
        self._check_provider("s3")

        if not self.does_file_exist(path):
            raise FileDoesNotExist(f"File:{path} does not exist in S3")

        if as_blob:
            obj = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=path)
            return obj["Body"].read()

        elif save_to:
            self.s3_client.download_file(self.s3_bucket_name, path, save_to)
            return save_to

        elif as_presign:
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket_name, "Key": path},
                ExpiresIn=int(timedelta(minutes=60).total_seconds()),
            )

        return self.s3_client.head_object(Bucket=self.s3_bucket_name, Key=path)

    def list_s3_files(self, path=""):
        self._check_provider("s3")

        files = []
        response = self.s3_client.list_objects_v2(
            Bucket=self.s3_bucket_name, Prefix=path
        )
        for content in response.get("Contents", []):
            key = content["Key"]
            name = os.path.basename(key)
            signed_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket_name, "Key": key},
                ExpiresIn=3600,
            )
            files.append(
                {
                    "name": name,
                    "path": key,
                    "provider": "s3",
                    "source": signed_url,
                    "options": {
                        "type": "local",
                        "file": {"name": name, "size": content["Size"]},
                    },
                }
            )
        return files

    # GCS Methods
    def upload_to_gcs(self, file, file_name=None, folder=None, abs_path=None):
        """
        Upload a file to GCS, allowing optional folder and filename, but preferring abs_path.

        file: FileStorage object or local file path
        file_name: Name of the file (required if abs_path is not provided)
        folder: Folder path in GCS (optional, ignored if abs_path is used)
        abs_path: Absolute GCS path (overrides folder and file_name)
        """
        self._check_provider("gcs")

        # If abs_path is provided, override folder and file_name
        if abs_path:
            folder, file_name = os.path.split(abs_path)

        # Ensure file_name is provided
        if not file_name:
            raise ValueError("file_name is required when abs_path is not specified")

        gcs_path = (
            os.path.join(folder, file_name).replace(os.sep, "/")
            if folder
            else file_name
        )

        bucket = self.gcs_client.bucket(self.gcs_bucket_name)
        blob = bucket.blob(gcs_path)

        if isinstance(file, str):
            if not os.path.isfile(file):
                raise ValueError(f"File not found: {file}")
            blob.upload_from_filename(file)
        else:
            blob.upload_from_file(file)

        current_app.logger.debug(
            f"File: {file_name} uploaded to GCS bucket: {self.gcs_bucket_name} in folder: {folder or 'root'}"
        )
        return gcs_path

    def list_gcs_files(self, path=""):
        self._check_provider("gcs")

        bucket = self.gcs_client.bucket(self.gcs_bucket_name)
        return [blob.name for blob in bucket.list_blobs(prefix=path)]

    def get_gcs_file(self, path, as_presign=False, as_blob=False, save_to=None):
        self._check_provider("gcs")

        bucket = self.gcs_client.bucket(self.gcs_bucket_name)
        blob = bucket.blob(path)

        if not self.does_file_exist(path):
            raise FileDoesNotExist(f"File:{path} does not exist in GCS")

        if as_blob:
            return blob.download_as_bytes()
        elif save_to:
            blob.download_to_filename(save_to)
            return path
        elif as_presign:
            return blob.generate_signed_url(expiration=timedelta(minutes=60))
        return blob
