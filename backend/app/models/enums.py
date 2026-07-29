"""Shared enum values used by Phase 4 persistence models."""

from enum import StrEnum


class UserRole(StrEnum):
    """MVP user roles."""

    ADMINISTRATOR = "administrator"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class ProjectStatus(StrEnum):
    """Project lifecycle status values."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ArtifactKind(StrEnum):
    """Artifact kinds mirrored from the shared contracts."""

    SOURCE_DRAWING = "source_drawing"
    NORMALIZED_IMAGE = "normalized_image"
    ENHANCED_IMAGE = "enhanced_image"
    OCR_JSON = "ocr_json"
    DETECTION_JSON = "detection_json"
    SEGMENTATION_MASK = "segmentation_mask"
    VECTOR_GEOMETRY = "vector_geometry"
    GEOMETRY_JSON = "geometry_json"
    ENGINEERING_GRAPH = "engineering_graph"
    RULE_RESULT = "rule_result"
    FORMULA_RESULT = "formula_result"
    QUANTITY_TAKEOFF = "quantity_takeoff"
    COST_ESTIMATE = "cost_estimate"
    BOQ = "boq"
    REPORT = "report"


class PipelineStage(StrEnum):
    """Pipeline stages mirrored from the shared contracts."""

    DRAWING = "drawing"
    IMAGE_ENHANCEMENT = "image_enhancement"
    OCR = "ocr"
    OBJECT_DETECTION = "object_detection"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    VECTORIZATION = "vectorization"
    GEOMETRY_RECONSTRUCTION = "geometry_reconstruction"
    ENGINEERING_GRAPH_CONSTRUCTION = "engineering_graph_construction"
    ENGINEERING_RULE_ENGINE = "engineering_rule_engine"
    FORMULA_ENGINE = "formula_engine"
    QUANTITY_TAKEOFF = "quantity_takeoff"
    COST_ESTIMATION = "cost_estimation"
    BOQ_GENERATION = "boq_generation"
    REPORT_GENERATION = "report_generation"


class JobStatus(StrEnum):
    """Pipeline job status values mirrored from the shared contracts."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    RETRYING = "retrying"
    PARTIAL_SUCCESS = "partial_success"
    NEEDS_REVIEW = "needs_review"
