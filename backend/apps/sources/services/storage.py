from __future__ import annotations

from io import BytesIO

from django.conf import settings
from minio import Minio


def minio_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_raw_bucket(client: Minio | None = None) -> Minio:
    client = client or minio_client()
    if not client.bucket_exists(settings.MINIO_BUCKET_RAW):
        client.make_bucket(settings.MINIO_BUCKET_RAW)
    return client


def upload_bytes(
    *,
    object_key: str,
    content: bytes,
    content_type: str,
) -> str:
    client = ensure_raw_bucket()
    client.put_object(
        settings.MINIO_BUCKET_RAW,
        object_key,
        BytesIO(content),
        length=len(content),
        content_type=content_type or "application/octet-stream",
    )
    return object_key
