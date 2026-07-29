"""Dataset validation for Phase 4 dataset management."""

from __future__ import annotations

from collections import Counter
from itertools import islice
from pathlib import Path

from bitonx_ai.datasets.loaders import FloorplanDataset
from bitonx_ai.datasets.models import (
    AnnotationKind,
    DatasetKind,
    DatasetSample,
    PlanAnnotation,
    ValidationIssue,
    ValidationReport,
    ValidationStatus,
)
from bitonx_ai.datasets.taxonomy import normalize_label

FORBIDDEN_PHASE4_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "ai_model",
        "ai_prediction",
        "detection_result",
        "detectionresult",
        "model_name",
        "model_prediction",
        "model_version",
        "ocr_result",
        "ocrresult",
        "quantity_takeoff",
        "segmentation_mask",
        "segmentation_result",
        "segmentationmask",
        "segmentationresult",
    }
)


class DatasetValidator:
    """Validate dataset structure, annotations, metadata, and guardrails."""

    def __init__(
        self,
        *,
        require_annotations: bool = True,
        validate_images: bool = True,
        max_samples: int | None = None,
    ) -> None:
        self.require_annotations = require_annotations
        self.validate_images = validate_images
        self.max_samples = max_samples

    def validate(self, dataset: FloorplanDataset) -> ValidationReport:
        """Validate a full dataset."""
        issues: list[ValidationIssue] = []
        if not dataset.root.exists():
            issues.append(
                ValidationIssue(
                    code="DATASET_ROOT_MISSING",
                    message=f"Dataset root does not exist: {dataset.root}",
                    status=ValidationStatus.INVALID,
                    path=dataset.root,
                )
            )
        if len(dataset) == 0:
            issues.append(
                ValidationIssue(
                    code="DATASET_EMPTY",
                    message="Dataset contains no samples.",
                    status=ValidationStatus.WARNING,
                    path=dataset.root,
                )
            )

        duplicate_ids = [
            sample_id
            for sample_id, count in Counter(sample.sample_id for sample in dataset).items()
            if count > 1
        ]
        for sample_id in duplicate_ids:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_SAMPLE_ID",
                    message=f"Sample id appears more than once: {sample_id}",
                    status=ValidationStatus.INVALID,
                    sample_id=sample_id,
                )
            )

        sample_iterable = iter(dataset)
        if self.max_samples is not None:
            sample_iterable = islice(sample_iterable, self.max_samples)
        for sample in sample_iterable:
            issues.extend(self.validate_sample(sample))

        return ValidationReport(
            dataset_name=dataset.name,
            sample_count=len(dataset),
            issues=tuple(issues),
        )

    def validate_sample(self, sample: DatasetSample) -> tuple[ValidationIssue, ...]:
        """Validate one sample."""
        issues: list[ValidationIssue] = []
        issues.extend(_validate_paths(sample, validate_images=self.validate_images))
        issues.extend(_validate_guardrails(sample))

        if sample.metadata.get("parseError"):
            issues.append(
                ValidationIssue(
                    code="ANNOTATION_PARSE_ERROR",
                    message=str(sample.metadata["parseError"]),
                    status=ValidationStatus.INVALID,
                    sample_id=sample.sample_id,
                    path=sample.annotation_path,
                )
            )

        if self.require_annotations and not sample.annotations:
            issues.append(
                ValidationIssue(
                    code="ANNOTATIONS_EMPTY",
                    message="Sample has no parsed annotations.",
                    status=ValidationStatus.INVALID,
                    sample_id=sample.sample_id,
                    path=sample.annotation_path,
                )
            )

        annotation_ids: set[str] = set()
        for annotation in sample.annotations:
            if annotation.annotation_id in annotation_ids:
                issues.append(
                    ValidationIssue(
                        code="DUPLICATE_ANNOTATION_ID",
                        message=f"Annotation id appears more than once: {annotation.annotation_id}",
                        status=ValidationStatus.INVALID,
                        sample_id=sample.sample_id,
                        annotation_id=annotation.annotation_id,
                    )
                )
            annotation_ids.add(annotation.annotation_id)
            issues.extend(_validate_annotation(sample, annotation))

        issues.extend(_validate_graph(sample))
        return tuple(issues)


def _validate_paths(sample: DatasetSample, *, validate_images: bool) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    if sample.annotation_path is None:
        issues.append(
            ValidationIssue(
                code="ANNOTATION_PATH_MISSING",
                message="Sample does not have an annotation path.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
            )
        )
    elif not sample.annotation_path.exists():
        issues.append(
            ValidationIssue(
                code="ANNOTATION_FILE_MISSING",
                message=f"Annotation file does not exist: {sample.annotation_path}",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                path=sample.annotation_path,
            )
        )

    if sample.dataset_kind == DatasetKind.CUBICASA5K and sample.image_path is None:
        issues.append(
            ValidationIssue(
                code="IMAGE_PATH_MISSING",
                message="CubiCasa5K sample does not have an image path.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
            )
        )
    if sample.image_path is not None and not sample.image_path.exists():
        issues.append(
            ValidationIssue(
                code="IMAGE_FILE_MISSING",
                message=f"Image file does not exist: {sample.image_path}",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                path=sample.image_path,
            )
        )
    if validate_images and sample.image_path is not None and sample.image_path.exists():
        issues.extend(_validate_image_file(sample))
    return tuple(issues)


def _validate_image_file(sample: DatasetSample) -> tuple[ValidationIssue, ...]:
    if sample.image_metadata is None:
        return (
            ValidationIssue(
                code="IMAGE_METADATA_UNREADABLE",
                message="Image metadata could not be read.",
                status=ValidationStatus.WARNING,
                sample_id=sample.sample_id,
                path=sample.image_path,
            ),
        )
    if sample.image_metadata.width <= 0 or sample.image_metadata.height <= 0:
        return (
            ValidationIssue(
                code="IMAGE_DIMENSIONS_INVALID",
                message="Image dimensions must be positive.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                path=sample.image_path,
            ),
        )
    return ()


def _validate_guardrails(sample: DatasetSample) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for key in sample.metadata:
        normalized = normalize_label(key)
        if normalized in FORBIDDEN_PHASE4_METADATA_KEYS:
            issues.append(
                ValidationIssue(
                    code="PHASE4_FORBIDDEN_OUTPUT_METADATA",
                    message=(
                        "Phase 4 is dataset management only; OCR, detection, segmentation, "
                        f"AI model, and quantity outputs are not allowed in metadata key {key!r}."
                    ),
                    status=ValidationStatus.INVALID,
                    sample_id=sample.sample_id,
                )
            )
    for annotation in sample.annotations:
        for key in annotation.metadata:
            normalized = normalize_label(key)
            if normalized in FORBIDDEN_PHASE4_METADATA_KEYS:
                issues.append(
                    ValidationIssue(
                        code="PHASE4_FORBIDDEN_OUTPUT_ANNOTATION_METADATA",
                        message=(
                            "Phase 4 annotations must be ground-truth dataset records, not OCR, "
                            "detection, segmentation, AI model, or quantity outputs."
                        ),
                        status=ValidationStatus.INVALID,
                        sample_id=sample.sample_id,
                        annotation_id=annotation.annotation_id,
                    )
                )
    return tuple(issues)


def _validate_annotation(
    sample: DatasetSample,
    annotation: PlanAnnotation,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    if not annotation.category:
        issues.append(
            ValidationIssue(
                code="ANNOTATION_CATEGORY_EMPTY",
                message="Annotation category must be present.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                annotation_id=annotation.annotation_id,
            )
        )
    if not annotation.source_label:
        issues.append(
            ValidationIssue(
                code="ANNOTATION_SOURCE_LABEL_EMPTY",
                message="Annotation source label must be present.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                annotation_id=annotation.annotation_id,
            )
        )

    point_count = len(annotation.points)
    if annotation.kind == AnnotationKind.POLYGON and point_count < 3:
        issues.append(
            ValidationIssue(
                code="POLYGON_TOO_FEW_POINTS",
                message="Polygon annotations must contain at least three points.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                annotation_id=annotation.annotation_id,
            )
        )
    if annotation.kind == AnnotationKind.POLYLINE and point_count < 2:
        issues.append(
            ValidationIssue(
                code="POLYLINE_TOO_FEW_POINTS",
                message="Polyline annotations must contain at least two points.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                annotation_id=annotation.annotation_id,
            )
        )
    if annotation.kind == AnnotationKind.POINT and point_count != 1:
        issues.append(
            ValidationIssue(
                code="POINT_ANNOTATION_INVALID",
                message="Point annotations must contain exactly one point.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                annotation_id=annotation.annotation_id,
            )
        )

    bbox = annotation.resolved_bbox
    if bbox.width < 0 or bbox.height < 0:
        issues.append(
            ValidationIssue(
                code="BOUNDING_BOX_INVALID",
                message="Bounding-box width and height must be non-negative.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                annotation_id=annotation.annotation_id,
            )
        )
    if annotation.kind == AnnotationKind.POLYGON and annotation.area <= 0:
        issues.append(
            ValidationIssue(
                code="POLYGON_ZERO_AREA",
                message="Polygon area is zero; annotation may need review.",
                status=ValidationStatus.WARNING,
                sample_id=sample.sample_id,
                annotation_id=annotation.annotation_id,
            )
        )
    if annotation.confidence is not None and not 0 <= annotation.confidence <= 1:
        issues.append(
            ValidationIssue(
                code="CONFIDENCE_OUT_OF_RANGE",
                message="Annotation confidence must be between 0 and 1 when present.",
                status=ValidationStatus.INVALID,
                sample_id=sample.sample_id,
                annotation_id=annotation.annotation_id,
            )
        )
    return tuple(issues)


def _validate_graph(sample: DatasetSample) -> tuple[ValidationIssue, ...]:
    if sample.graph is None:
        return ()
    issues: list[ValidationIssue] = []
    node_ids = {node.node_id for node in sample.graph.nodes}
    for edge in sample.graph.edges:
        missing: list[str] = []
        if edge.source_node_id not in node_ids:
            missing.append(edge.source_node_id)
        if edge.target_node_id not in node_ids:
            missing.append(edge.target_node_id)
        if missing:
            issues.append(
                ValidationIssue(
                    code="GRAPH_EDGE_NODE_MISSING",
                    message=f"Graph edge references unknown node id(s): {', '.join(missing)}",
                    status=ValidationStatus.INVALID,
                    sample_id=sample.sample_id,
                    annotation_id=edge.edge_id,
                )
            )
    return tuple(issues)


def write_validation_report(report: ValidationReport, path: str | Path) -> Path:
    """Write a validation report to JSON."""
    import json

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return output_path
