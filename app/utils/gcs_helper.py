from flask import current_app
from google.cloud import storage
import os


class GCS:
    def __init__(self, root_path=None, bucket_name=None, credentials_path=None):
        if root_path == "":
            raise ValueError("root_path is not set")
        self.root_path = root_path

        self.bucket_name = bucket_name or current_app.config["GCS_BUCKET"]
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET is not set")

        # use svc account creds
        if credentials_path or current_app.config["GOOGLE_APPLICATION_CREDENTIALS"]:
            self.client = storage.Client.from_service_account_json(
                credentials_path or current_app.config["GOOGLE_APPLICATION_CREDENTIALS"]
            )
        else:
            # use ADC
            self.client = storage.Client()

    def get_root_path(self, blob_name):
        if self.root_path and self.root_path not in blob_name:
            return f"{self.root_path}/{blob_name}"
        return blob_name

    def upload_file_object(self, file_object, destination_blob_name):
        """
        Uploads a file object to the Google Cloud Storage bucket.

        Args:
            file_object (object): File object to upload
            destination_blob_name (str): Name of the blob in the bucket to create.

        Returns:
            The URL of the uploaded file.
        """
        path = self.get_root_path(destination_blob_name)
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(path)
        blob.upload_from_file(file_object)
        return path

    def get_file(self, blob_name):
        """
        Retrieves a file from the Google Cloud Storage bucket and saves it locally.

        Args:
            blob_name (str): Name of the blob in the bucket to retrieve.

        Returns:
            True if the file was successfully retrieved, False otherwise.
        """
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(self.get_root_path(blob_name))
        return blob

    def list_files(self, sub_path=None):
        # Get bucket object
        bucket = self.client.get_bucket(self.bucket_name)

        path = "/"
        if self.root_path:
            path = os.path.join(path, self.root_path)
        if sub_path:
            path = os.path.join(path, sub_path)

        # List blobs in the specified folder
        blobs = bucket.list_blobs(prefix=path, delimiter="/")
        file_list = []
        for blob in blobs:
            file_list.append(blob.name)

        return file_list
