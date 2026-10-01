"""จุดเดียวที่ตรวจความปลอดภัยก่อนเรียก R2 จริง ใช้ร่วมกันโดย
`scripts/ci_r2_cleanup.py` และ `tests/conftest.py` — ทั้งสองที่ลบ object จริง
เอา validation ไว้ที่เดียวกันเพื่อไม่ให้ path หนึ่งเช็คครบแต่อีก path ไม่เช็ค

ทั้งสองฟังก์ชัน raise ValueError พร้อมข้อความบอกอาการ (symptom) เท่านั้น
ห้าม log หรือ assert ค่าจริงของ endpoint เพราะเป็น secret — GitHub จะ mask
เป็น `***` อยู่แล้ว ทำให้ข้อความที่พิมพ์ค่าออกมาไม่มีประโยชน์กับคนอ่าน
"""

from __future__ import annotations

from urllib.parse import urlsplit

SAFE_PREFIX_ROOTS = ("ci/", "local/")
R2_HOST_SUFFIX = ".r2.cloudflarestorage.com"


def assert_valid_r2_endpoint(endpoint: str) -> None:
    """Raise ValueError describing the symptom if endpoint is malformed."""
    if not endpoint.startswith("https://"):
        raise ValueError("R2 endpoint must start with https://")
    if endpoint != endpoint.strip():
        raise ValueError("R2 endpoint has leading or trailing whitespace")
    path = urlsplit(endpoint).path.strip("/")
    if path:
        raise ValueError(
            "R2 endpoint must not include a path — boto3 appends the bucket "
            "name itself, so a trailing path segment doubles it up"
        )
    # host เช็คทีหลัง path เพราะ "https://" เปล่าๆ ก็ผ่าน startswith/strip/path
    # มาได้ — ต้องเช็ค host ไม่ว่างและมี account-id label ก่อนต่อท้าย suffix
    host = urlsplit(endpoint).netloc
    if not host:
        raise ValueError("R2 endpoint is missing a host")
    if not host.endswith(R2_HOST_SUFFIX):
        raise ValueError(f"R2 endpoint host must end with {R2_HOST_SUFFIX}")
    account_id = host[: -len(R2_HOST_SUFFIX)]
    if not account_id:
        raise ValueError("R2 endpoint is missing the account ID")


def assert_safe_prefix(prefix: str) -> None:
    """Raise ValueError if prefix is not safe to list-and-delete under.

    A safe prefix starts with one of SAFE_PREFIX_ROOTS and extends past it —
    "ci/" alone would delete everything any run has ever written.
    """
    if not prefix or prefix == "/":
        raise ValueError(f"refusing unsafe R2 prefix: {prefix!r}")
    root = next((r for r in SAFE_PREFIX_ROOTS if prefix.startswith(r)), None)
    if root is None:
        raise ValueError(f"refusing R2 prefix outside {SAFE_PREFIX_ROOTS}: {prefix!r}")
    if len(prefix) <= len(root):
        raise ValueError(f"refusing R2 prefix that stops at its root: {prefix!r}")
