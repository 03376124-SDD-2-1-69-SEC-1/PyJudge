"""Seed R2 ด้วย PDF โจทย์ 100 ข้อจาก programming.in.th

รายการโจทย์อยู่ที่ scripts/seed/pith-100-manifest.csv

รัน (จาก root ของ repo):
    # ดูก่อนว่าจะอัปไป bucket ไหน กี่ไฟล์
    uv run --env-file .env python scripts/seed_pith_to_r2.py --dry-run
    # อัปจริง
    uv run --env-file .env python scripts/seed_pith_to_r2.py

- ใช้ตัวแปร R2_* ชุดเดียวกับแอป (R2_ENDPOINT_URL, R2_BUCKET_NAME,
  R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY)
- PDF ที่โหลดมาเก็บ cache ไว้ที่ data/pith/ (อยู่ใน .gitignore แล้ว) รันซ้ำไม่โหลดใหม่
- object ที่มีอยู่แล้วบน R2 จะข้าม — รันซ้ำได้ปลอดภัย และสคริปต์นี้ไม่ลบอะไรเลย
- ผลลัพธ์ data/pith/uploaded.csv มี r2_key + sha256 + topic/difficulty
  ไว้ insert core.knowledge_documents ตอนทำ ingest
"""

from __future__ import annotations

import csv
import hashlib
import os
import sys
import time
import urllib.request
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from questly.database.storage.safety import assert_valid_r2_endpoint

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts" / "seed" / "pith-100-manifest.csv"
CACHE_DIR = ROOT / "data" / "pith"
OUT_CSV = CACHE_DIR / "uploaded.csv"
REQUIRED_VARS = (
    "R2_ENDPOINT_URL",
    "R2_BUCKET_NAME",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
)


def fetch_pdf(url: str, dest: Path) -> bytes:
    if dest.exists():
        return dest.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "questly-seed/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if not resp.headers.get("Content-Type", "").startswith("application/pdf"):
            raise RuntimeError(f"not a PDF: {url}")
        data = resp.read()
    dest.write_bytes(data)
    time.sleep(0.3)  # อย่ายิงเว็บเขารัว
    return data


def object_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    missing = [v for v in REQUIRED_VARS if not os.environ.get(v)]
    if missing:
        sys.exit(f"missing env: {', '.join(missing)} (ลืม --env-file .env หรือเปล่า)")
    try:
        assert_valid_r2_endpoint(os.environ["R2_ENDPOINT_URL"])
    except ValueError as error:
        sys.exit(str(error))
    bucket = os.environ["R2_BUCKET_NAME"]

    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8-sig")))
    print(f"bucket={bucket}  files={len(rows)}  dry_run={dry_run}")

    client = boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    uploaded = skipped = 0
    for n, r in enumerate(rows, 1):
        data = fetch_pdf(r["pdf_url"], CACHE_DIR / f"{r['task_id']}.pdf")
        r["sha256"] = hashlib.sha256(data).hexdigest()
        r["size_bytes"] = len(data)

        if object_exists(client, bucket, r["r2_key"]):
            status = "exists"
            skipped += 1
        elif dry_run:
            status = "would upload"
        else:
            client.put_object(
                Bucket=bucket,
                Key=r["r2_key"],
                Body=data,
                ContentType="application/pdf",
                # R2 metadata ต้องเป็น ASCII — ชื่อโจทย์ภาษาไทยเก็บใน DB แทน
                Metadata={
                    "task-id": r["task_id"],
                    "topic": r["topic"],
                    "difficulty": r["difficulty"],
                    "sha256": r["sha256"],
                },
            )
            status = "uploaded"
            uploaded += 1
        print(f"[{n:3}/{len(rows)}] {r['r2_key']:<48} {status}")

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"uploaded={uploaded} skipped={skipped} -> {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
