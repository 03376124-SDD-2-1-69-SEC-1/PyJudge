"""SQLModel ORM สำหรับ Postgres schema `core`

Source of truth: docs/HANDOFF-data-modeling.md §5 (ERD) และ §6 (เหตุผลแต่ละ field)

Decision ที่ตกลงแล้ว (§4) ที่ไฟล์นี้ยึดตาม:
- PK = BIGSERIAL (int) ไม่ใช่ UUID
- Sync ล้วน ไม่มี async engine/session ในไฟล์นี้ (อยู่ที่ database/session.py)
- ไม่มี FK ข้าม schema ไป rag เลย (ดู database/rag/tables.py คนละไฟล์)

กฎเหล็ก (database/README.md): "อย่าให้ Core service import ORM หรือ storage
client โดยตรง" — ไฟล์นี้ถูก import ได้เฉพาะจาก database/core/*_repository.py
(adapter ที่แปลง ORM row ↔ dataclass ใน core/assignments/models.py) เท่านั้น
ห้าม import ตรงจาก src/greader/core/*
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

SCHEMA = "core"


# ---------------------------------------------------------------------------
# Column helpers — เขียนเป็นฟังก์ชัน (ไม่ใช่ constant) เพราะ Column object
# ผูกกับตารางเดียวได้ตารางเดียว ต้อง instantiate ใหม่ทุกครั้งที่เรียกใช้
# ---------------------------------------------------------------------------


def _pk() -> Optional[int]:
    """BIGSERIAL PK ตาม §4 (int ไม่ใช่ UUID)"""
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
            onupdate=func.now(),  # ทำงานเฉพาะตอน UPDATE ผ่าน SQLAlchemy session
            # เท่านั้น ถ้ามีใครแก้แถวด้วย raw SQL ตรงๆ ต้องอัปเดตคอลัมน์นี้เอง
        ),
    )


def _metadata_jsonb() -> dict:
    """คอลัมน์ JSONB ชื่อ `metadata` ใน DB — Python attribute ต้องชื่อ
    `metadata_` เพราะ `metadata` เป็นชื่อ reserved ของ SQLModel/SQLAlchemy
    เอง (ใช้เก็บ MetaData registry ของทุก model class)"""
    return Field(
        default_factory=dict,
        sa_column=Column(
            "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
        ),
    )


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('instructor', 'admin')", name="ck_users_role"),
        {"schema": SCHEMA},
    )

    id: Optional[int] = _pk()
    email: str = Field(nullable=False, unique=True, index=True)
    display_name: Optional[str] = Field(default=None)
    role: str = Field(nullable=False, default="instructor")
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()

    documents: list["KnowledgeDocument"] = Relationship(back_populates="uploader")
    generation_requests: list["GenerationRequest"] = Relationship(
        back_populates="requester"
    )


class KnowledgeDocument(SQLModel, table=True):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'ingesting', 'ready', 'failed')",
            name="ck_knowledge_documents_status",
        ),
        {"schema": SCHEMA},
    )

    id: Optional[int] = _pk()
    # natural key ใช้ cross-check ตอน mirror ไป rag.knowledge_sources
    r2_object_key: str = Field(nullable=False, unique=True, index=True)
    filename: str = Field(nullable=False)
    content_hash: str = Field(nullable=False)  # sha256 กันไฟล์ซ้ำ
    status: str = Field(nullable=False, default="uploaded")
    metadata_: dict = _metadata_jsonb()  # topic, difficulty, course
    uploaded_by: Optional[int] = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()

    uploader: Optional[User] = Relationship(back_populates="documents")


class GenerationRequest(SQLModel, table=True):
    __tablename__ = "generation_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'generating', 'completed', 'failed')",
            name="ck_generation_requests_status",
        ),
        {"schema": SCHEMA},
    )

    id: Optional[int] = _pk()
    prompt: str = Field(nullable=False)
    filters: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
        # topic, difficulty — ต้อง match key ใน knowledge_documents.metadata
    )
    status: str = Field(nullable=False, default="pending")
    error_code: Optional[str] = Field(default=None)
    requested_by: Optional[int] = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey(f"{SCHEMA}.users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()

    requester: Optional[User] = Relationship(back_populates="generation_requests")
    artifacts: list["GenerationArtifact"] = Relationship(back_populates="request")


class GenerationArtifact(SQLModel, table=True):
    __tablename__ = "generation_artifacts"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('pending', 'applied', 'discarded')",
            name="ck_generation_artifacts_review_status",
        ),
        {"schema": SCHEMA},
    )

    id: Optional[int] = _pk()
    request_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(f"{SCHEMA}.generation_requests.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    draft: dict = Field(
        sa_column=Column(JSONB, nullable=False)
        # title, statement, test_cases — ไม่มี default ตั้งใจ ต้องส่งมาตอน insert เสมอ
    )
    citations: list[dict] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
        # แต่ละ item: {chunk_id, source_id, page, score, text_snapshot}
    )
    model_provider: Optional[str] = Field(default=None)
    model_name: Optional[str] = Field(default=None)  # เช่น "gemini-2.0-flash"
    review_status: str = Field(nullable=False, default="pending")
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()

    request: Optional[GenerationRequest] = Relationship(back_populates="artifacts")
    # uselist=False ระบุชัดว่าเป็น one-to-one — SQLAlchemy เดาเองได้จาก
    # unique=True บน assignments.artifact_id อยู่แล้ว แต่เขียนไว้กันพลาด
    # ถ้าวันหลังมีคนถอด unique ออก จะได้ error ตรงจุดแทนที่จะเงียบๆ
    # กลายเป็น list
    assignment: Optional["Assignment"] = Relationship(
        back_populates="artifact",
        sa_relationship_kwargs={"uselist": False},
    )


class Assignment(SQLModel, table=True):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')",
            name="ck_assignments_difficulty",
        ),
        {"schema": SCHEMA},
    )

    id: Optional[int] = _pk()
    # NULL ได้ ถ้าสร้างมือผ่าน CRUD ปกติ (ไม่ผ่าน AI approval flow)
    #
    # unique=True บังคับความสัมพันธ์ 1 artifact : 0-หรือ-1 assignment ตาม ERD
    # (`||--o|`) กัน apply artifact เดิมซ้ำจนได้ assignment ซ้ำ
    #
    # ไม่ชนกับเคส manual CRUD เพราะ Postgres ถือว่า NULL แต่ละตัว "ไม่เท่ากัน"
    # ในการเช็ค UNIQUE — จึงมีแถวที่ artifact_id IS NULL ได้ไม่จำกัด
    artifact_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey(f"{SCHEMA}.generation_artifacts.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
    )
    title: str = Field(nullable=False)
    problem_statement: str = Field(nullable=False)
    difficulty: str = Field(nullable=False)
    metadata_: dict = _metadata_jsonb()  # topic, language, course
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()

    artifact: Optional[GenerationArtifact] = Relationship(back_populates="assignment")
    test_cases: list["TestCase"] = Relationship(
        back_populates="assignment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class TestCase(SQLModel, table=True):
    __tablename__ = "test_cases"
    __table_args__ = (
        # เปิดใช้ถ้าอยากกันลำดับชนกันในโจทย์เดียวกัน (§7.4 บอกว่ายังไม่ตกลง
        # ว่าต้องการไหม — default คือปิดไว้ก่อน):
        # UniqueConstraint(
        #     "assignment_id", "order_index", name="uq_test_cases_assignment_order"
        # ),
        {"schema": SCHEMA},
    )

    id: Optional[int] = _pk()
    assignment_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(f"{SCHEMA}.assignments.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    input_data: str = Field(nullable=False)
    expected_output: str = Field(nullable=False)
    is_hidden: bool = Field(nullable=False, default=False)
    order_index: int = Field(nullable=False, default=0)
    created_at: datetime = _created_at()
    updated_at: datetime = _updated_at()

    assignment: Optional[Assignment] = Relationship(back_populates="test_cases")