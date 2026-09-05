"""R2 (S3-compatible) object storage client — used by the /health/r2 route.

Per database/README.md rule 5, this module — and everything under
database/ — is the only place allowed to build the storage client directly.
core/* modules must only ever see a Protocol + a plain dataclass.
"""

from __future__ import annotations

import os

import boto3
from botocore.client import BaseClient
from botocore.config import Config

R2_ENDPOINT_URL = os.environ["R2_ENDPOINT_URL"]
R2_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]

MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", 20 * 1024 * 1024))

_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def get_r2_client() -> BaseClient:
    return _client


def check_r2(client: BaseClient) -> dict:
    """Confirm the R2 bucket is reachable."""
    client.head_bucket(Bucket=R2_BUCKET_NAME)
    return {"connected": True, "bucket": R2_BUCKET_NAME}


def upload_file(client: BaseClient, local_path: str, key: str) -> dict:
    """Upload a local file to the R2 bucket under the given object key."""
    client.upload_file(local_path, R2_BUCKET_NAME, key)
    return {"bucket": R2_BUCKET_NAME, "key": key}
