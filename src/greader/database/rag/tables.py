"""SQLModel ORM สำหรับ Postgres schema `rag`

Source of truth: docs/HANDOFF-data-modeling.md §5 (ERD), §6.1–§6.4 (เหตุผล
แต่ละ field), และ §7.1/§7.2/§7.4 (สิ่งที่ ERD บอกไม่ได้ ต้องเขียนมือใน
Alembic migration — อ่านก่อนรัน `alembic revision --autogenerate`)

Cross-schema note (§4 "เรื่อง PK: int vs UUID"): ไม่มี FK จริงจาก
`knowledge_sources.core_document_id` ไปยัง `core.knowledge_documents.id`
สอง service คุยกันผ่าน HTTP mirror เท่านั้น — `core_document_id` เป็นแค่
BIGINT ที่ "ควรจะ" ตรงกับ id ฝั่ง core แต่ int ผิดค่าแล้วจะไม่มีอะไรจับได้
เลย (int 42 มีอยู่ทุกตาราง) จึงเก็บ `r2_object_key` ซ้ำไว้ด้วย เพื่อ
cross-check ว่า mirror ชี้ถูกแถวจริง

หมายเหตุ dependency: ต้องมี `pgvector` (pip/uv) เพิ่มเติมสำหรับ Vector
column type — ตอนเช็ค pyproject.toml ใน handoff ยังไม่มีตัวนี้ระบุไว้
คู่กับ sqlmodel/psycopg/alembic
"""

from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

SCHEMA = "rag"
EMBEDDING_DIM = 768  # ล็อกตาม embedding model จริง (§6.4) — เปลี่ยนโมเดล
# ที่มิติต่างกันทีหลัง = ต้อง migrate column ใหม่ทั้งตาราง (one-way door)


# ---------------------------------------------------------------------------
# Column helpers (เหมือน database/core/tables.py — คัดลอกมาเพื่อไม่ให้
# ไฟล์นี้ import ข้าม service boundary ไปหา core module)
# ---------------------------------------------------------------------------


def _pk() -> int | None:
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


def _metadata_jsonb() -> dict:
    """คอลัมน์ JSONB ชื่อ `metadata` ใน DB — Python attribute ต้องชื่อ
    `metadata_` เพราะ `metadata` เป็นชื่อ reserved ของ SQLModel/SQLAlchemy"""
    return Field(
        default_factory=dict,
        sa_column=Column(
            "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
        ),
    )


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class KnowledgeSource(SQLModel, table=True):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        UniqueConstraint(
            "core_document_id", name="uq_knowledge_sources_core_document_id"
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_knowledge_sources_status",
        ),
        # §6.1 — filter ตอน retrieval ต้องพึ่ง metadata ที่ mirror มาจาก core
        Index("ix_knowledge_sources_metadata", "metadata", postgresql_using="gin"),
        {"schema": SCHEMA},
    )

    id: int | None = _pk()
    # logical link เท่านั้น ไม่ใช่ FK จริง (ดู module docstring ด้านบน)
    core_document_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    r2_object_key: str = Field(nullable=False)  # ซ้ำกับ core ตั้งใจ ใช้ verify link
    content_hash: str = Field(nullable=False)
    status: str = Field(nullable=False, default="pending")
    embedding_model: str | None = Field(default=None)  # เช่น "text-embedding-004"
    embedding_dim: int | None = Field(default=None)
    metadata_: dict = (
        _metadata_jsonb()
    )  # topic, difficulty, course — mirror มาเพื่อ filter
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()

    chunks: list[KnowledgeChunk] = Relationship(
        back_populates="source",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        # §7.4 — กัน chunk ซ้ำตอน re-ingest
        UniqueConstraint(
            "source_id", "content_hash", name="uq_knowledge_chunks_source_content_hash"
        ),
        # §6.2 — ใช้ดึง chunk ข้างเคียง (ก่อนหน้า/ถัดไป) ภายใน source เดียวกัน
        Index("ix_knowledge_chunks_source_chunk_index", "source_id", "chunk_index"),
        {"schema": SCHEMA},
    )

    id: int | None = _pk()
    source_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(f"{SCHEMA}.knowledge_sources.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    chunk_index: int = Field(nullable=False)  # ลำดับใน source (0, 1, 2, ...)
    page: int | None = Field(default=None)
    text: str = Field(nullable=False)
    token_count: int | None = Field(default=None)  # คุม context budget ตอนประกอบ prompt
    content_hash: str = Field(nullable=False)
    # ซ้ำจาก source ตั้งใจ (§6.4) — กัน vector คนละรุ่นปนกันแบบเงียบๆ
    embedding_model: str | None = Field(default=None)
    metadata_: dict = _metadata_jsonb()  # question_no, content_type
    # HNSW index ต้องเขียนมือใน Alembic migration (§7.1) — autogenerate ไม่สร้างให้:
    #   CREATE INDEX ON rag.knowledge_chunks USING hnsw (embedding vector_cosine_ops);
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(EMBEDDING_DIM), nullable=True)
    )
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()

    source: KnowledgeSource | None = Relationship(back_populates="chunks")
