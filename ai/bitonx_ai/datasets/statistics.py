"""Dataset statistics for unified floor-plan datasets."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

from bitonx_ai.datasets.loaders import FloorplanDataset
from bitonx_ai.datasets.models import DatasetKind, JsonValue


@dataclass(frozen=True, slots=True)
class DatasetStatistics:
    """Aggregated statistics for a dataset snapshot."""

    dataset_name: str
    dataset_kind: DatasetKind
    sample_count: int
    annotation_count: int
    category_counts: Mapping[str, int] = field(default_factory=dict)
    phase3_object_type_counts: Mapping[str, int] = field(default_factory=dict)
    split_counts: Mapping[str, int] = field(default_factory=dict)
    image_width: Mapping[str, float] = field(default_factory=dict)
    image_height: Mapping[str, float] = field(default_factory=dict)
    annotations_per_sample: Mapping[str, float] = field(default_factory=dict)
    graph_node_count: int = 0
    graph_edge_count: int = 0

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize statistics to JSON-compatible data."""
        return {
            "datasetName": self.dataset_name,
            "datasetKind": self.dataset_kind.value,
            "sampleCount": self.sample_count,
            "annotationCount": self.annotation_count,
            "categoryCounts": dict(self.category_counts),
            "phase3ObjectTypeCounts": dict(self.phase3_object_type_counts),
            "splitCounts": dict(self.split_counts),
            "imageWidth": dict(self.image_width),
            "imageHeight": dict(self.image_height),
            "annotationsPerSample": dict(self.annotations_per_sample),
            "graphNodeCount": self.graph_node_count,
            "graphEdgeCount": self.graph_edge_count,
        }


class DatasetStatisticsCalculator:
    """Compute reusable statistics without reading large image arrays."""

    def compute(self, dataset: FloorplanDataset) -> DatasetStatistics:
        """Compute statistics for a dataset."""
        category_counts: Counter[str] = Counter()
        phase3_counts: Counter[str] = Counter()
        split_counts: Counter[str] = Counter()
        widths: list[int] = []
        heights: list[int] = []
        annotation_total = 0
        graph_nodes = 0
        graph_edges = 0

        for sample in dataset:
            annotation_total += len(sample.annotations)
            for annotation in sample.annotations:
                category_counts[annotation.category] += 1
                phase3_counts[annotation.phase3_object_type] += 1
            split_counts[sample.split.value if sample.split is not None else "unassigned"] += 1
            if sample.image_metadata is not None:
                widths.append(sample.image_metadata.width)
                heights.append(sample.image_metadata.height)
            if sample.graph is not None:
                graph_nodes += len(sample.graph.nodes)
                graph_edges += len(sample.graph.edges)

        return DatasetStatistics(
            dataset_name=dataset.name,
            dataset_kind=dataset.kind,
            sample_count=len(dataset),
            annotation_count=annotation_total,
            category_counts=dict(sorted(category_counts.items())),
            phase3_object_type_counts=dict(sorted(phase3_counts.items())),
            split_counts=dict(sorted(split_counts.items())),
            image_width=_numeric_summary(widths),
            image_height=_numeric_summary(heights),
            annotations_per_sample=_numeric_summary(
                [len(sample.annotations) for sample in dataset]
            ),
            graph_node_count=graph_nodes,
            graph_edge_count=graph_edges,
        )


def _numeric_summary(values: list[int]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "min": float(min(values)),
        "max": float(max(values)),
        "mean": float(sum(values) / len(values)),
    }
