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


    def upload_file_obj(self, fileObj, key):
        self.client.upload_fileobj(Fileobj=fileObj, Bucket=current_app.config['EVIDENCE_BUCKET'], Key=key)

    def generate_presigned_url(self, bucket_name, key):
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=60
        )