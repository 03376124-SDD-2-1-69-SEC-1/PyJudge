"""R2 (S3-compatible) object storage client — used by the /health/r2 route.

Per database/README.md rule 5, this module — and everything under
database/ — is the only place allowed to build the storage client directly.
core/* modules must only ever see a Protocol + a plain dataclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.config import Config
from dotenv import load_dotenv

MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", 20 * 1024 * 1024))


class R2Client(Protocol):
    """S3 operations required by the existing health and upload endpoints."""

    def head_bucket(self, *, Bucket: str) -> object: ...

    def upload_file(self, local_path: str, bucket: str, key: str) -> None: ...


@dataclass(frozen=True, slots=True)
class R2Storage:
    """An explicitly configured client and its target bucket."""

    client: R2Client
    bucket: str

    def __post_init__(self) -> None:
        if not self.bucket or not self.bucket.strip():
            raise ValueError("R2 storage requires a nonempty bucket")


def get_max_upload_size_bytes() -> int:
    """Read the existing upload limit after loading deferred configuration."""
    load_dotenv()
    return int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", MAX_UPLOAD_SIZE_BYTES))


def _required_setting(name: str) -> str:
    load_dotenv()
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


@lru_cache(maxsize=1)
def get_r2_storage() -> R2Storage:
    """Build the production client and bucket together on first use."""
    endpoint = _required_setting("R2_ENDPOINT_URL")
    bucket = _required_setting("R2_BUCKET_NAME")
    access_key = _required_setting("R2_ACCESS_KEY_ID")
    secret_key = _required_setting("R2_SECRET_ACCESS_KEY")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    return R2Storage(client=client, bucket=bucket)


def check_r2(storage: R2Storage) -> dict:
    """Confirm the R2 bucket is reachable."""
    storage.client.head_bucket(Bucket=storage.bucket)
    return {"connected": True, "bucket": storage.bucket}


def upload_file(storage: R2Storage, local_path: str, key: str) -> dict:
    """Upload a local file to the R2 bucket under the given object key."""
    storage.client.upload_file(local_path, storage.bucket, key)
    return {"bucket": storage.bucket, "key": key}
