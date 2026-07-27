from __future__ import annotations

from pathlib import Path

from django.conf import settings
from minio import Minio


def store_raw_company_dataset(path: Path, *, source_slug: str, checksum: str) -> str:
    """Upload an unchanged source file to the bronze bucket and return its S3 URI."""
    bucket = settings.MINIO_BUCKET_RAW
    object_name = (
        f"company-datasets/{source_slug}/{checksum[:12]}/{path.name}"
    )
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.fput_object(bucket, object_name, str(path))
    return f"s3://{bucket}/{object_name}"
