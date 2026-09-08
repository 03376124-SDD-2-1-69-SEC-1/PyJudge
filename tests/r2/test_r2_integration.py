"""Behaviour `moto` does not faithfully reproduce, checked against real R2.

เทสสามตัวนี้จงใจไม่ใช้ moto: presigned URL ต้อง fetch ผ่าน HTTP จริง,
multipart upload ต้องเช็ค ETag ที่ R2 คำนวณเอง, และ conditional write
(IfNoneMatch) เป็นพฤติกรรมที่ moto จำลองได้ไม่ตรงกับของจริงเสมอไป
ทุกอย่างที่เหลือ (upload แล้ว list เจอ) ยังอยู่ที่ tests/integration ผ่าน stub
"""

import io
import os

import httpx
import pytest
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

pytestmark = pytest.mark.r2

MULTIPART_PART_SIZE = 5 * 1024 * 1024


def test_presigned_get_url_serves_the_uploaded_object(
    r2_test_bucket: tuple, r2_test_prefix: str
) -> None:
    client, bucket = r2_test_bucket
    key = f"{r2_test_prefix}notes.txt"
    body = b"hello from the r2 integration test"
    client.put_object(Bucket=bucket, Key=key, Body=body)

    url = client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=60
    )
    response = httpx.get(url)

    assert response.status_code == 200
    assert response.content == body


def test_multipart_upload_of_a_large_pdf(
    r2_test_bucket: tuple, r2_test_prefix: str
) -> None:
    client, bucket = r2_test_bucket
    key = f"{r2_test_prefix}large.pdf"
    body = b"%PDF-1.4\n" + os.urandom(MULTIPART_PART_SIZE + 1)
    config = TransferConfig(
        multipart_threshold=MULTIPART_PART_SIZE,
        multipart_chunksize=MULTIPART_PART_SIZE,
    )

    client.upload_fileobj(io.BytesIO(body), bucket, key, Config=config)

    head = client.head_object(Bucket=bucket, Key=key)
    assert head["ContentLength"] == len(body)
    # ETag ที่มี "-" ต่อท้ายบอกจำนวน part — ยืนยันว่าอัปโหลดแบบ multipart จริง
    assert "-" in head["ETag"]


def test_put_object_conflicts_on_an_existing_key(
    r2_test_bucket: tuple, r2_test_prefix: str
) -> None:
    client, bucket = r2_test_bucket
    key = f"{r2_test_prefix}conflict.txt"
    client.put_object(Bucket=bucket, Key=key, Body=b"first", IfNoneMatch="*")

    with pytest.raises(ClientError) as exc_info:
        client.put_object(Bucket=bucket, Key=key, Body=b"second", IfNoneMatch="*")

    assert exc_info.value.response["Error"]["Code"] == "PreconditionFailed"
