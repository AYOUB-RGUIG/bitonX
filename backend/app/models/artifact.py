"""Artifact persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.base import utc_now

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.upload import UploadedFile


class Artifact(Base):
    """Stored binary or JSON artifact produced by the pipeline."""

    __tablename__ = "artifacts"
    __table_args__ = (
        CheckConstraint(
            "kind in ("
            "'source_drawing', 'normalized_image', 'enhanced_image', 'ocr_json', "
            "'detection_json', 'segmentation_mask', 'vector_geometry', 'geometry_json', "
            "'engineering_graph', 'rule_result', 'formula_result', 'quantity_takeoff', "
            "'cost_estimate', 'boq', 'report'"
            ")",
            name="ck_artifacts_kind",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    checksum: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="artifacts")
    uploads: Mapped[list["UploadedFile"]] = relationship(back_populates="artifact")
