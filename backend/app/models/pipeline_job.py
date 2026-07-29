"""Pipeline job persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.upload import UploadedFile


class PipelineJob(Base):
    """Persisted status for an asynchronous pipeline stage."""

    __tablename__ = "pipeline_jobs"
    __table_args__ = (
        CheckConstraint(
            "stage in ("
            "'drawing', 'image_enhancement', 'ocr', 'object_detection', "
            "'semantic_segmentation', 'vectorization', 'geometry_reconstruction', "
            "'engineering_graph_construction', 'engineering_rule_engine', 'formula_engine', "
            "'quantity_takeoff', 'cost_estimation', 'boq_generation', 'report_generation'"
            ")",
            name="ck_pipeline_jobs_stage",
        ),
        CheckConstraint(
            "status in ("
            "'pending', 'queued', 'running', 'succeeded', 'failed', 'canceled', "
            "'retrying', 'partial_success', 'needs_review'"
            ")",
            name="ck_pipeline_jobs_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    upload_id: Mapped[str | None] = mapped_column(ForeignKey("uploaded_files.id"), index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    output_artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(255))
    model_version: Mapped[str | None] = mapped_column(String(64))
    formula_version: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(String(1024))

    project: Mapped["Project"] = relationship(back_populates="jobs")
    upload: Mapped[UploadedFile | None] = relationship(back_populates="jobs")
