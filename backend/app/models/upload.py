"""Uploaded file persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.base import utc_now

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.pipeline_job import PipelineJob
    from app.models.project import Project


class UploadedFile(Base):
    """Source drawing uploaded by a user for a project."""

    __tablename__ = "uploaded_files"
    __table_args__ = (
        CheckConstraint(
            "mime_type in ('application/pdf', 'image/png', 'image/jpeg')",
            name="ck_uploaded_files_mime_type",
        ),
        CheckConstraint("size_bytes > 0", name="ck_uploaded_files_size_positive"),
        CheckConstraint("page_count is null or page_count > 0", name="ck_uploaded_files_page_count"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    page_count: Mapped[int | None] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="uploads")
    artifact: Mapped["Artifact"] = relationship(back_populates="uploads")
    jobs: Mapped[list["PipelineJob"]] = relationship(back_populates="upload")
