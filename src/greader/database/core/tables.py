"""SQLModel ORM สำหรับ Postgres schema `core`

PLACEHOLDER — Database owner ยังไม่ได้ออกแบบ Core schema เต็มรูปแบบ (ดู
database/README.md). ตารางนี้มีไว้แค่พอให้ `rag.knowledge_sources
.core_document_id` และ `r2_object_key` (ดู database/rag/tables.py docstring
§4) มีแถวจริงฝั่ง core ให้ mirror อ้างถึง — ขยาย field เพิ่มทีหลังตาม
docs/HANDOFF-data-modeling.md เมื่อมี
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, func
from sqlmodel import Field, SQLModel

SCHEMA = "core"


# ---------------------------------------------------------------------------
# Column helpers (เหมือน database/rag/tables.py — คัดลอกมาเพื่อไม่ให้ไฟล์นี้
# import ข้าม service boundary ไปหา rag module)
# ---------------------------------------------------------------------------


def _pk() -> Optional[int]:
    return Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )


def _created_at() -> datetime:
    return Field(
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )


def _updated_at() -> datetime:
    return Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class KnowledgeDocument(SQLModel, table=True):
    __tablename__ = "knowledge_documents"
    __table_args__ = ({"schema": SCHEMA},)

    id: Optional[int] = _pk()
    r2_object_key: str = Field(nullable=False, unique=True)
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()
