from io import BytesIO

import boto3
from botocore.exceptions import ClientError

from sqlalchemy_media.typing_ import FileLike
from .base import Store

CANNED_ACL_PUBLIC_READ = 'public-read'
CANNED_ACL_PRIVATE = 'private'


class S3Boto3Store(Store):
    """
    Store for dealing with s3 of aws through boto3

    .. versionadded:: 0.18.0

    """
    base_url = 'https://{0}.s3.amazonaws.com'

    def __init__(self, bucket_name: str, access_key: str, secret_key: str,
                 region: str, base_url: str = None, cdn_url: str = None,
                 policy: str = None, storage_class=None, encryption=False, reduced_redundancy=False):
        self.access_key = access_key
        self.secret_key = secret_key
        self.encryption = encryption
        self.reduced_redundancy = reduced_redundancy

        if base_url:
            self.base_url = base_url
        else:
            self.base_url = self.base_url.format(bucket_name)

        self._policy = policy or CANNED_ACL_PUBLIC_READ
        self._storage_class = storage_class or 'STANDARD'

        kw = {}
        # if endpoint_url is not None:
        #     kw['endpoint_url'] = endpoint_url
        if region is not None:
            kw['region_name'] = region

        self._conn = boto3.Session(aws_access_key_id=access_key,
                                   aws_secret_access_key=secret_key)
        self._s3 = self._conn.resource('s3', **kw)
        self.bucket = self._s3.Bucket(bucket_name)

        # Create bucket if it doesn't exist.
        try:
            self.bucket.meta.client.head_bucket(Bucket=bucket_name)
        except ClientError as err:
            self.bucket.create()
            self.bucket.wait_until_exists()

        if cdn_url and cdn_url.endswith('/'):
            cdn_url = cdn_url.rstrip('/')

        self.cdn_url = cdn_url

    def _upload_file(self, content, filename, content_type=None):
        key = self.bucket.Object(filename)

        put_parameters = {"ContentType": content_type}
        if self.encryption:
            put_parameters['ServerSideEncryption'] = 'AES256'
        if self.reduced_redundancy:
            put_parameters['StorageClass'] = 'REDUCED_REDUNDANCY'
        if self._policy:
            put_parameters['ACL'] = self._policy

        key.upload_fileobj(content, ExtraArgs=put_parameters)

    def put(self, filename: str, stream: FileLike):
        length = getattr(stream, 'content_length', 0)
        content_type = getattr(stream, 'content_type', None)
        self._upload_file(stream, filename, content_type)
        return length

    def delete(self, filename: str):
        k = self.bucket.Object(filename)
        k.reload()
        if k:
            k.delete()

    def open(self, filename: str, mode: str = 'rb') -> FileLike:
        key = self.bucket.Object(filename)
        key.reload()

        if key is None:
            raise IOError('File %s not existing' % filename)

        body = key.get()['Body']

        return BytesIO(body.read())

    def locate(self, attachment) -> str:
        if not attachment.path:
            return ''

        if self.cdn_url:
            base_url = self.cdn_url
        else:
            base_url = self.base_url
        return '%s/%s' % (base_url, attachment.path)
