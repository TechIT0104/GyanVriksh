"""MinIO object storage helpers."""
import io

from minio import Minio

from app.config import settings

_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )
        for bucket in (settings.minio_bucket_docs, settings.minio_bucket_audio):
            if not _client.bucket_exists(bucket):
                _client.make_bucket(bucket)
    return _client


def upload_bytes(bucket: str, object_name: str, data: bytes, content_type="application/octet-stream") -> str:
    get_client().put_object(bucket, object_name, io.BytesIO(data), len(data), content_type=content_type)
    return f"s3://{bucket}/{object_name}"


def download_to_file(bucket: str, object_name: str, dest_path: str):
    get_client().fget_object(bucket, object_name, dest_path)


def presigned_url(bucket: str, object_name: str) -> str:
    return get_client().presigned_get_object(bucket, object_name)
