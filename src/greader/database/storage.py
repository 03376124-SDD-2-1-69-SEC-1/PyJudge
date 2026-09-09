"""R2 (S3-compatible) object storage client — used by the /health/r2 route.

Per database/README.md rule 5, this module — and everything under
database/ — is the only place allowed to build the storage client directly.
core/* modules must only ever see a Protocol + a plain dataclass.
"""

from __future__ import annotations

import os
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from dotenv import load_dotenv

MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", 20 * 1024 * 1024))


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
def get_r2_client() -> BaseClient:
    """Build the production client on first use, never during module import."""
    endpoint = _required_setting("R2_ENDPOINT_URL")
    _required_setting("R2_BUCKET_NAME")
    access_key = _required_setting("R2_ACCESS_KEY_ID")
    secret_key = _required_setting("R2_SECRET_ACCESS_KEY")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def check_r2(client: BaseClient) -> dict:
    """Confirm the R2 bucket is reachable."""
    bucket = _required_setting("R2_BUCKET_NAME")
    client.head_bucket(Bucket=bucket)
    return {"connected": True, "bucket": bucket}


def upload_file(client: BaseClient, local_path: str, key: str) -> dict:
    """Upload a local file to the R2 bucket under the given object key."""
    bucket = _required_setting("R2_BUCKET_NAME")
    client.upload_file(local_path, bucket, key)
    return {"bucket": bucket, "key": key}
