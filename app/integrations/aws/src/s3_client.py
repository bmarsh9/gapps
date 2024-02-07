import boto3
from flask import current_app
from app.utils.singleton import Singleton

class S3(Singleton):

    _client = None
    def __init__(self):
        if self._client is None:
            self._client = boto3.client("s3", "us-east-1")

    @property
    def client(self):
        return self._client

    def upload_file_obj(self, fileObj, key, extra_args = {}):
        self.client.upload_fileobj(Fileobj=fileObj, Bucket=current_app.config['EVIDENCE_BUCKET'], Key=key, ExtraArgs=extra_args)

    def generate_presigned_url(self, bucket_name: str, key: str) -> str:
        params = {
            "Bucket": bucket_name,
            "Key": key,
        }
        return self.client.generate_presigned_url('get_object', Params=params, ExpiresIn=60)

    def generate_presigned_download_url(self, bucket_name: str, key: str, filename: str) -> str:
        params = {
            "Bucket": bucket_name,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename={filename}'
        }
        return self.client.generate_presigned_url('get_object', Params=params, ExpiresIn=60)