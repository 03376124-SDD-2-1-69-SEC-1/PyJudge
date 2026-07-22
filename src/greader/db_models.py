"""SQLAlchemy ORM models for persistence."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class AssignmentRecord(Base):
    """Persistent representation of a programming assignment."""

    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    input_format: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_format: Mapped[str] = mapped_column(Text, nullable=False, default="")
    constraints: Mapped[str] = mapped_column(Text, nullable=False, default="")
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False, default="Easy")
    programming_language: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Python"
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Draft")
    reference_solution: Mapped[str] = mapped_column(Text, nullable=False, default="")
    coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mutation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    test_cases: Mapped[list["TestCaseRecord"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    generation_requests: Mapped[list["GenerationRequestRecord"]] = relationship(
        back_populates="assignment",
    )

    __table_args__ = (
        Index("ix_assignments_difficulty", "difficulty"),
        Index("ix_assignments_status", "status"),
    )


class TestCaseRecord(Base):
    """Persistent representation of a single test case."""

    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_data: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="Normal")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    assignment: Mapped["AssignmentRecord"] = relationship(
        back_populates="test_cases",
    )

    __table_args__ = (
        Index("ix_test_cases_assignment_id", "assignment_id"),
        Index("ix_test_cases_category", "category"),
    )


class GenerationRequestRecord(Base):
    """Persistent audit record for one AI generation request."""

    __tablename__ = "generation_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    assignment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("assignments.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    safe_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    assignment: Mapped["AssignmentRecord | None"] = relationship(
        back_populates="generation_requests",
    )
    artifact: Mapped["GenerationArtifactRecord | None"] = relationship(
        back_populates="generation_request",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )

    __table_args__ = (
        Index("ix_generation_requests_assignment_id", "assignment_id"),
        Index("ix_generation_requests_status", "status"),
    )


class GenerationArtifactRecord(Base):
    """Persistent validated output produced by an AI provider."""

    __tablename__ = "generation_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    generation_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generation_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    generation_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    generation_request: Mapped["GenerationRequestRecord"] = relationship(
        back_populates="artifact",
    )

    __table_args__ = (
        Index("ix_generation_artifacts_generation_request_id", "generation_request_id"),
    )
