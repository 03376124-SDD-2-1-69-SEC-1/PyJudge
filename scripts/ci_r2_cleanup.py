"""Delete every object under one CI run's R2 test prefix.

รันโดย .github/workflows/ci.yml หลัง pytest จบ (ทั้ง pass และ fail) เป็นการ
ล้าง object ที่เทสต์ r2 สร้างไว้ใต้ prefix ของ run นั้น ๆ lifecycle rule บน
bucket `greader-ci` (ลบของเก่ากว่า 1 วัน) เป็นตาข่ายรับอีกชั้นเผื่อ step นี้
ไม่ได้รัน (runner ถูก kill กลางคัน) — เหมือนกับที่ `--expires-at` รับ Neon branch

ห้ามแก้ guard ของ prefix เด็ดขาด: prefix ผิดพลาด (ว่าง, "/", หรือไม่ขึ้นต้น
ด้วย "ci/" หรือ "local/") ต้องทำให้ script exit ไม่ใช่ 0 ทันที ไม่งั้น bug เล็ก ๆ
ในตัวแปร environment จะกลายเป็นการลบทั้ง bucket guard เดียวกันนี้ (และการเช็ค
endpoint) อยู่ใน src/greader/r2_safety.py ใช้ร่วมกับ tests/conftest.py — ที่นั่น
เป็นอีกจุดที่ลบ object จริงเหมือนกัน
"""

from __future__ import annotations

import os
import sys

import boto3
from botocore.config import Config

from greader.r2_safety import assert_safe_prefix, assert_valid_r2_endpoint

REQUIRED_VARS = (
    "R2_TEST_ENDPOINT_URL",
    "R2_TEST_ACCESS_KEY_ID",
    "R2_TEST_SECRET_ACCESS_KEY",
    "R2_TEST_BUCKET_NAME",
    "R2_TEST_PREFIX",
)
DELETE_BATCH_SIZE = 1000


def main() -> None:
    missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
    if missing:
        sys.exit(f"missing required environment variables: {', '.join(missing)}")

    endpoint = os.environ["R2_TEST_ENDPOINT_URL"]
    try:
        assert_valid_r2_endpoint(endpoint)
    except ValueError as error:
        sys.exit(str(error))

    prefix = os.environ["R2_TEST_PREFIX"]
    try:
        assert_safe_prefix(prefix)
    except ValueError as error:
        sys.exit(str(error))

    bucket = os.environ["R2_TEST_BUCKET_NAME"]
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["R2_TEST_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_TEST_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

    paginator = client.get_paginator("list_objects_v2")
    keys = [
        entry["Key"]
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix)
        for entry in page.get("Contents", [])
    ]

    deleted = 0
    for start in range(0, len(keys), DELETE_BATCH_SIZE):
        batch = keys[start : start + DELETE_BATCH_SIZE]
        response = client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": key} for key in batch]},
        )
        deleted += len(response.get("Deleted", []))
        for error in response.get("Errors", []):
            print(f"::warning::failed to delete {error['Key']}: {error['Message']}")

    print(f"deleted {deleted} object(s) under {prefix!r} in bucket {bucket!r}")


if __name__ == "__main__":
    main()
