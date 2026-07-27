from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from typing import BinaryIO

from django.conf import settings
from minio import Minio


def minio_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket(bucket_name: str, client: Minio | None = None) -> Minio:
    client = client or minio_client()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
    return client


def ensure_raw_bucket(client: Minio | None = None) -> Minio:
    return ensure_bucket(settings.MINIO_BUCKET_RAW, client)


def upload_bytes(
    *,
    object_key: str,
    content: bytes,
    content_type: str,
    bucket_name: str | None = None,
) -> str:
    selected_bucket = bucket_name or settings.MINIO_BUCKET_RAW
    client = ensure_bucket(selected_bucket)
    client.put_object(
        selected_bucket,
        object_key,
        BytesIO(content),
        length=len(content),
        content_type=content_type or "application/octet-stream",
    )
    return object_key


def upload_stream(
    *,
    object_key: str,
    stream: BinaryIO,
    length: int,
    content_type: str,
    bucket_name: str | None = None,
) -> str:
    selected_bucket = bucket_name or settings.MINIO_BUCKET_RAW
    client = ensure_bucket(selected_bucket)
    client.put_object(
        selected_bucket,
        object_key,
        stream,
        length=length,
        content_type=content_type or "application/octet-stream",
    )
    return object_key


def stream_object(
    object_key: str,
    *,
    bucket_name: str | None = None,
    chunk_size: int = 64 * 1024,
) -> Iterator[bytes]:
    selected_bucket = bucket_name or settings.MINIO_BUCKET_RAW
    client = minio_client()
    response = client.get_object(selected_bucket, object_key)
    try:
        while chunk := response.read(chunk_size):
            yield chunk
    finally:
        response.close()
        response.release_conn()


def download_bytes(
    object_key: str,
    *,
    bucket_name: str | None = None,
) -> bytes:
    selected_bucket = bucket_name or settings.MINIO_BUCKET_RAW
    client = minio_client()
    response = client.get_object(selected_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_object(
    object_key: str,
    *,
    bucket_name: str | None = None,
) -> None:
    selected_bucket = bucket_name or settings.MINIO_BUCKET_RAW
    client = minio_client()
    client.remove_object(
        selected_bucket,
        object_key,
    )
