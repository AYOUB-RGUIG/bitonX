"""Dataset metadata management."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import json
from pathlib import Path

from bitonx_ai.datasets.loaders import FloorplanDataset
from bitonx_ai.datasets.models import DatasetVersionRecord, JsonValue
from bitonx_ai.datasets.statistics import DatasetStatistics


class DatasetMetadataManager:
    """Create, read, write, and update dataset metadata records."""

    def collect(
        self,
        dataset: FloorplanDataset,
        *,
        statistics: DatasetStatistics | None = None,
        version: DatasetVersionRecord | None = None,
        license_name: str | None = None,
        source_url: str | None = None,
        citation: str | None = None,
        description: str | None = None,
        extra: Mapping[str, JsonValue] | None = None,
    ) -> dict[str, JsonValue]:
        """Create a metadata record from the current dataset snapshot."""
        now = datetime.now(UTC).isoformat()
        metadata: dict[str, JsonValue] = {
            "datasetName": dataset.name,
            "datasetKind": dataset.kind.value,
            "root": str(dataset.root),
            "sampleCount": len(dataset),
            "createdAt": now,
            "updatedAt": now,
            "phase3Compliance": {
                "architecture": "engineering-intelligence-platform",
                "datasetManagementOnly": True,
                "containsOcrResults": False,
                "containsObjectDetectionResults": False,
                "containsSegmentationResults": False,
                "containsAiModels": False,
                "containsFinalQuantities": False,
            },
        }
        if description is not None:
            metadata["description"] = description
        if license_name is not None:
            metadata["license"] = license_name
        if source_url is not None:
            metadata["sourceUrl"] = source_url
        if citation is not None:
            metadata["citation"] = citation
        if statistics is not None:
            metadata["statistics"] = statistics.to_dict()
        if version is not None:
            metadata["version"] = version.to_dict()
        if extra is not None:
            metadata["extra"] = dict(extra)
        return metadata

    def write(self, metadata: Mapping[str, object], path: str | Path) -> Path:
        """Write dataset metadata to JSON."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return output_path

    def read(self, path: str | Path) -> dict[str, object]:
        """Read dataset metadata from JSON."""
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Dataset metadata must be a JSON object: {path}")
        return data

    def update(
        self,
        path: str | Path,
        updates: Mapping[str, JsonValue],
    ) -> dict[str, object]:
        """Update a metadata JSON file and return the updated record."""
        metadata = self.read(path)
        metadata.update(dict(updates))
        metadata["updatedAt"] = datetime.now(UTC).isoformat()
        self.write(metadata, path)
        return metadata
