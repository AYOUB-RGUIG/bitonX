"""Core dataset records for the BitonX dataset pipeline."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from bitonx_ai.datasets.taxonomy import phase3_object_type

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]


class DatasetKind(StrEnum):
    """Supported floor-plan dataset families."""

    CUBICASA5K = "cubicasa5k"
    RESPLAN = "resplan"
    UNIFIED = "unified"


class SplitName(StrEnum):
    """Canonical dataset split names."""

    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"

    @classmethod
    def coerce(cls, value: str | "SplitName") -> "SplitName":
        """Coerce common split aliases to canonical names."""
        if isinstance(value, SplitName):
            return value
        normalized = value.strip().lower()
        if normalized in {"val", "valid", "validation", "dev"}:
            return cls.VALIDATION
        if normalized in {"train", "training"}:
            return cls.TRAIN
        if normalized in {"test", "testing"}:
            return cls.TEST
        raise ValueError(f"Unsupported split name: {value!r}")


class AnnotationKind(StrEnum):
    """Geometry type for a parsed annotation."""

    POLYGON = "polygon"
    POLYLINE = "polyline"
    POINT = "point"
    BOUNDING_BOX = "bounding_box"


class ValidationStatus(StrEnum):
    """Validation statuses mirrored from the Phase 3 common contract."""

    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class Point2D:
    """A 2D point in image or plan coordinates."""

    x: float
    y: float

    def to_dict(self) -> dict[str, float]:
        """Serialize the point using the Phase 3 `Point2D` shape."""
        return {"x": self.x, "y": self.y}

    @classmethod
    def from_iterable(cls, values: Iterable[float]) -> "Point2D":
        """Build a point from a two-value iterable."""
        x, y = tuple(values)
        return cls(float(x), float(y))


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned bounding box in image or plan coordinates."""

    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        """Return the bounding-box area."""
        return max(self.width, 0.0) * max(self.height, 0.0)

    def to_dict(self) -> dict[str, float]:
        """Serialize the box using the Phase 3 `BoundingBox` shape."""
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_points(cls, points: Iterable[Point2D]) -> "BoundingBox":
        """Create a bounding box covering all points."""
        point_tuple = tuple(points)
        if not point_tuple:
            return cls(0.0, 0.0, 0.0, 0.0)
        min_x = min(point.x for point in point_tuple)
        min_y = min(point.y for point in point_tuple)
        max_x = max(point.x for point in point_tuple)
        max_y = max(point.y for point in point_tuple)
        return cls(min_x, min_y, max_x - min_x, max_y - min_y)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BoundingBox":
        """Deserialize a bounding box from JSON-like data."""
        return cls(
            x=float(data["x"]),
            y=float(data["y"]),
            width=float(data["width"]),
            height=float(data["height"]),
        )


@dataclass(frozen=True, slots=True)
class PlanAnnotation:
    """A parsed ground-truth annotation for a floor-plan sample."""

    annotation_id: str
    category: str
    source_label: str
    kind: AnnotationKind
    points: tuple[Point2D, ...] = ()
    bbox: BoundingBox | None = None
    confidence: float | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    @property
    def phase3_object_type(self) -> str:
        """Return the closest Phase 3 object type for this annotation."""
        return phase3_object_type(self.category)

    @property
    def resolved_bbox(self) -> BoundingBox:
        """Return the explicit box or compute one from the geometry."""
        if self.bbox is not None:
            return self.bbox
        return BoundingBox.from_points(self.points)

    @property
    def area(self) -> float:
        """Return polygon area using the shoelace formula when possible."""
        if self.kind != AnnotationKind.POLYGON or len(self.points) < 3:
            return 0.0
        area = 0.0
        points = self.points
        for index, point in enumerate(points):
            next_point = points[(index + 1) % len(points)]
            area += point.x * next_point.y - next_point.x * point.y
        return abs(area) / 2.0

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize this annotation to JSON-compatible data."""
        data: dict[str, JsonValue] = {
            "annotationId": self.annotation_id,
            "category": self.category,
            "phase3ObjectType": self.phase3_object_type,
            "sourceLabel": self.source_label,
            "kind": self.kind.value,
            "points": [point.to_dict() for point in self.points],
            "boundingBox": self.resolved_bbox.to_dict(),
            "metadata": dict(self.metadata),
        }
        if self.confidence is not None:
            data["confidence"] = self.confidence
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanAnnotation":
        """Deserialize an annotation from cache data."""
        points = tuple(
            Point2D(float(point["x"]), float(point["y"])) for point in data.get("points", [])
        )
        bbox_data = data.get("boundingBox")
        bbox = BoundingBox.from_dict(bbox_data) if isinstance(bbox_data, Mapping) else None
        return cls(
            annotation_id=str(data["annotationId"]),
            category=str(data["category"]),
            source_label=str(data["sourceLabel"]),
            kind=AnnotationKind(str(data["kind"])),
            points=points,
            bbox=bbox,
            confidence=float(data["confidence"]) if data.get("confidence") is not None else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class GraphNodeAnnotation:
    """A graph node attached to a floor-plan sample."""

    node_id: str
    category: str
    centroid: Point2D | None = None
    geometry_annotation_id: str | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the graph node."""
        data: dict[str, JsonValue] = {
            "nodeId": self.node_id,
            "category": self.category,
            "metadata": dict(self.metadata),
        }
        if self.centroid is not None:
            data["centroid"] = self.centroid.to_dict()
        if self.geometry_annotation_id is not None:
            data["geometryAnnotationId"] = self.geometry_annotation_id
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GraphNodeAnnotation":
        """Deserialize a graph node."""
        centroid_data = data.get("centroid")
        centroid = (
            Point2D(float(centroid_data["x"]), float(centroid_data["y"]))
            if isinstance(centroid_data, Mapping)
            else None
        )
        geometry_annotation_id = data.get("geometryAnnotationId")
        return cls(
            node_id=str(data["nodeId"]),
            category=str(data["category"]),
            centroid=centroid,
            geometry_annotation_id=(
                str(geometry_annotation_id) if geometry_annotation_id is not None else None
            ),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class GraphEdgeAnnotation:
    """A graph edge attached to a floor-plan sample."""

    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship: str
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the graph edge."""
        return {
            "edgeId": self.edge_id,
            "sourceNodeId": self.source_node_id,
            "targetNodeId": self.target_node_id,
            "relationship": self.relationship,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GraphEdgeAnnotation":
        """Deserialize a graph edge."""
        return cls(
            edge_id=str(data["edgeId"]),
            source_node_id=str(data["sourceNodeId"]),
            target_node_id=str(data["targetNodeId"]),
            relationship=str(data["relationship"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class PlanGraph:
    """Optional graph representation for a dataset sample."""

    nodes: tuple[GraphNodeAnnotation, ...] = ()
    edges: tuple[GraphEdgeAnnotation, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the graph."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanGraph":
        """Deserialize a graph."""
        return cls(
            nodes=tuple(GraphNodeAnnotation.from_dict(node) for node in data.get("nodes", [])),
            edges=tuple(GraphEdgeAnnotation.from_dict(edge) for edge in data.get("edges", [])),
        )


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    """Basic image metadata read without loading pixel arrays into samples."""

    width: int
    height: int
    mode: str | None = None
    mime_type: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize image metadata."""
        data: dict[str, JsonValue] = {"width": self.width, "height": self.height}
        if self.mode is not None:
            data["mode"] = self.mode
        if self.mime_type is not None:
            data["mimeType"] = self.mime_type
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ImageMetadata":
        """Deserialize image metadata."""
        return cls(
            width=int(data["width"]),
            height=int(data["height"]),
            mode=str(data["mode"]) if data.get("mode") is not None else None,
            mime_type=str(data["mimeType"]) if data.get("mimeType") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class DatasetSample:
    """Unified floor-plan dataset sample."""

    sample_id: str
    dataset_name: str
    dataset_kind: DatasetKind
    root: Path
    image_path: Path | None = None
    annotation_path: Path | None = None
    split: SplitName | None = None
    annotations: tuple[PlanAnnotation, ...] = ()
    graph: PlanGraph | None = None
    image_metadata: ImageMetadata | None = None
    checksum: str | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    @property
    def categories(self) -> tuple[str, ...]:
        """Return sorted categories present in this sample."""
        return tuple(sorted({annotation.category for annotation in self.annotations}))

    def with_annotations(
        self,
        annotations: Iterable[PlanAnnotation],
        *,
        graph: PlanGraph | None = None,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> "DatasetSample":
        """Return a copy of this sample with parsed annotations attached."""
        merged_metadata: dict[str, JsonValue] = dict(self.metadata)
        if metadata is not None:
            merged_metadata.update(metadata)
        return DatasetSample(
            sample_id=self.sample_id,
            dataset_name=self.dataset_name,
            dataset_kind=self.dataset_kind,
            root=self.root,
            image_path=self.image_path,
            annotation_path=self.annotation_path,
            split=self.split,
            annotations=tuple(annotations),
            graph=graph,
            image_metadata=self.image_metadata,
            checksum=self.checksum,
            metadata=merged_metadata,
        )

    def to_dict(self, *, include_annotations: bool = True) -> dict[str, JsonValue]:
        """Serialize the sample for cache, metadata, or reporting."""
        data: dict[str, JsonValue] = {
            "sampleId": self.sample_id,
            "datasetName": self.dataset_name,
            "datasetKind": self.dataset_kind.value,
            "root": str(self.root),
            "metadata": dict(self.metadata),
        }
        if self.image_path is not None:
            data["imagePath"] = str(self.image_path)
        if self.annotation_path is not None:
            data["annotationPath"] = str(self.annotation_path)
        if self.split is not None:
            data["split"] = self.split.value
        if self.image_metadata is not None:
            data["imageMetadata"] = self.image_metadata.to_dict()
        if self.checksum is not None:
            data["checksum"] = self.checksum
        if include_annotations:
            data["annotations"] = [annotation.to_dict() for annotation in self.annotations]
            if self.graph is not None:
                data["graph"] = self.graph.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DatasetSample":
        """Deserialize a dataset sample from cache data."""
        image_metadata_data = data.get("imageMetadata")
        graph_data = data.get("graph")
        split_data = data.get("split")
        return cls(
            sample_id=str(data["sampleId"]),
            dataset_name=str(data["datasetName"]),
            dataset_kind=DatasetKind(str(data["datasetKind"])),
            root=Path(str(data["root"])),
            image_path=Path(str(data["imagePath"])) if data.get("imagePath") else None,
            annotation_path=(
                Path(str(data["annotationPath"])) if data.get("annotationPath") else None
            ),
            split=SplitName.coerce(str(split_data)) if split_data is not None else None,
            annotations=tuple(
                PlanAnnotation.from_dict(annotation) for annotation in data.get("annotations", [])
            ),
            graph=PlanGraph.from_dict(graph_data) if isinstance(graph_data, Mapping) else None,
            image_metadata=(
                ImageMetadata.from_dict(image_metadata_data)
                if isinstance(image_metadata_data, Mapping)
                else None
            ),
            checksum=str(data["checksum"]) if data.get("checksum") is not None else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ParsedAnnotations:
    """Result returned by an annotation parser."""

    annotations: tuple[PlanAnnotation, ...] = ()
    graph: PlanGraph | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)
    canvas_width: float | None = None
    canvas_height: float | None = None


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A dataset validation message using Phase 3-compatible statuses."""

    code: str
    message: str
    status: ValidationStatus
    sample_id: str | None = None
    path: Path | None = None
    annotation_id: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the validation issue."""
        data: dict[str, JsonValue] = {
            "code": self.code,
            "message": self.message,
            "status": self.status.value,
        }
        if self.sample_id is not None:
            data["sampleId"] = self.sample_id
        if self.path is not None:
            data["path"] = str(self.path)
        if self.annotation_id is not None:
            data["annotationId"] = self.annotation_id
        return data

    def to_contract_message(self) -> dict[str, JsonValue]:
        """Serialize as the Phase 3 `ValidationMessage` contract shape."""
        data: dict[str, JsonValue] = {
            "code": self.code,
            "message": self.message,
            "status": self.status.value,
        }
        if self.sample_id is not None:
            data["sourceId"] = self.sample_id
        elif self.annotation_id is not None:
            data["sourceId"] = self.annotation_id
        return data


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Validation result for a dataset or a single sample."""

    dataset_name: str
    sample_count: int
    issues: tuple[ValidationIssue, ...] = ()
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def error_count(self) -> int:
        """Return invalid issue count."""
        return sum(1 for issue in self.issues if issue.status == ValidationStatus.INVALID)

    @property
    def warning_count(self) -> int:
        """Return warning or needs-review issue count."""
        return sum(
            1
            for issue in self.issues
            if issue.status in {ValidationStatus.WARNING, ValidationStatus.NEEDS_REVIEW}
        )

    @property
    def status(self) -> ValidationStatus:
        """Return the aggregate validation status."""
        if self.error_count:
            return ValidationStatus.INVALID
        if self.warning_count:
            return ValidationStatus.WARNING
        return ValidationStatus.VALID

    @property
    def is_valid(self) -> bool:
        """Return whether no invalid issues were found."""
        return self.status != ValidationStatus.INVALID

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the validation report."""
        return {
            "datasetName": self.dataset_name,
            "sampleCount": self.sample_count,
            "status": self.status.value,
            "errorCount": self.error_count,
            "warningCount": self.warning_count,
            "generatedAt": self.generated_at.isoformat(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class DatasetVersionRecord:
    """Version metadata for a dataset snapshot."""

    dataset_name: str
    dataset_kind: DatasetKind
    dataset_version: str
    content_hash: str
    sample_count: int
    schema_version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_paths: tuple[str, ...] = ()
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the version record."""
        return {
            "datasetName": self.dataset_name,
            "datasetKind": self.dataset_kind.value,
            "datasetVersion": self.dataset_version,
            "schemaVersion": self.schema_version,
            "contentHash": self.content_hash,
            "sampleCount": self.sample_count,
            "createdAt": self.created_at.isoformat(),
            "sourcePaths": list(self.source_paths),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DatasetVersionRecord":
        """Deserialize the version record."""
        created_at_raw = data.get("createdAt")
        created_at = (
            datetime.fromisoformat(str(created_at_raw))
            if created_at_raw is not None
            else datetime.now(UTC)
        )
        return cls(
            dataset_name=str(data["datasetName"]),
            dataset_kind=DatasetKind(str(data["datasetKind"])),
            dataset_version=str(data["datasetVersion"]),
            content_hash=str(data["contentHash"]),
            sample_count=int(data["sampleCount"]),
            schema_version=str(data.get("schemaVersion", "1.0")),
            created_at=created_at,
            source_paths=tuple(str(path) for path in data.get("sourcePaths", [])),
            metadata=dict(data.get("metadata", {})),
        )
