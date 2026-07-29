"""Dataset management pipeline for BitonX floor-plan data."""

from bitonx_ai.datasets.cache import DatasetCache
from bitonx_ai.datasets.integrity import DatasetIntegrityVerifier, file_sha256
from bitonx_ai.datasets.loaders import (
    CompositeFloorplanDataset,
    CubiCasa5KDataset,
    DatasetLoaderError,
    FloorplanDataset,
    ResPlanDataset,
    combine_datasets,
    load_dataset,
)
from bitonx_ai.datasets.metadata import DatasetMetadataManager
from bitonx_ai.datasets.models import (
    AnnotationKind,
    BoundingBox,
    DatasetKind,
    DatasetSample,
    DatasetVersionRecord,
    GraphEdgeAnnotation,
    GraphNodeAnnotation,
    ImageMetadata,
    ParsedAnnotations,
    PlanAnnotation,
    PlanGraph,
    Point2D,
    SplitName,
    ValidationIssue,
    ValidationReport,
    ValidationStatus,
)
from bitonx_ai.datasets.parsers import (
    CubiCasaSvgAnnotationParser,
    DatasetParserError,
    ResPlanAnnotationParser,
)
from bitonx_ai.datasets.splits import SplitManager, SplitManifest, SplitRatios
from bitonx_ai.datasets.statistics import DatasetStatistics, DatasetStatisticsCalculator
from bitonx_ai.datasets.validation import DatasetValidator, write_validation_report
from bitonx_ai.datasets.versioning import DatasetVersionManager
from bitonx_ai.datasets.visualization import DatasetVisualizer

__all__ = [
    "AnnotationKind",
    "BoundingBox",
    "CompositeFloorplanDataset",
    "CubiCasa5KDataset",
    "CubiCasaSvgAnnotationParser",
    "DatasetCache",
    "DatasetIntegrityVerifier",
    "DatasetKind",
    "DatasetLoaderError",
    "DatasetMetadataManager",
    "DatasetParserError",
    "DatasetSample",
    "DatasetStatistics",
    "DatasetStatisticsCalculator",
    "DatasetValidator",
    "DatasetVersionManager",
    "DatasetVersionRecord",
    "DatasetVisualizer",
    "FloorplanDataset",
    "GraphEdgeAnnotation",
    "GraphNodeAnnotation",
    "ImageMetadata",
    "ParsedAnnotations",
    "PlanAnnotation",
    "PlanGraph",
    "Point2D",
    "ResPlanAnnotationParser",
    "ResPlanDataset",
    "SplitManager",
    "SplitManifest",
    "SplitName",
    "SplitRatios",
    "ValidationIssue",
    "ValidationReport",
    "ValidationStatus",
    "combine_datasets",
    "file_sha256",
    "load_dataset",
    "write_validation_report",
]
