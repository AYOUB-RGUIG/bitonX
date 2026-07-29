"""Project persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.base import utc_now
from app.models.enums import ProjectStatus

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.pipeline_job import PipelineJob
    from app.models.upload import UploadedFile
    from app.models.user import User


class Project(Base):
    """Construction project workspace."""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft', 'active', 'archived', 'deleted')",
            name="ck_projects_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ProjectStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="project")
    uploads: Mapped[list["UploadedFile"]] = relationship("UploadedFile", back_populates="project")
    jobs: Mapped[list["PipelineJob"]] = relationship("PipelineJob", back_populates="project")
