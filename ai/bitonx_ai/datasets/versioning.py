"""Dataset versioning helpers."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import re

from bitonx_ai.datasets.loaders import FloorplanDataset
from bitonx_ai.datasets.models import DatasetVersionRecord, JsonValue


class DatasetVersionManager:
    """Create and persist dataset version records."""

    def create_record(
        self,
        dataset: FloorplanDataset,
        *,
        dataset_version: str,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> DatasetVersionRecord:
        """Create a version record for a dataset snapshot."""
        return DatasetVersionRecord(
            dataset_name=dataset.name,
            dataset_kind=dataset.kind,
            dataset_version=dataset_version,
            content_hash=self.content_hash(dataset),
            sample_count=len(dataset),
            source_paths=tuple(sorted(_dataset_source_paths(dataset))),
            metadata=metadata or {},
        )

    def content_hash(self, dataset: FloorplanDataset) -> str:
        """Compute a deterministic hash from sample metadata and file stats."""
        digest = hashlib.sha256()
        for sample in sorted(dataset, key=lambda item: item.sample_id):
            digest.update(sample.sample_id.encode("utf-8"))
            digest.update(sample.dataset_kind.value.encode("utf-8"))
            digest.update(str(len(sample.annotations)).encode("utf-8"))
            for annotation in sorted(sample.annotations, key=lambda item: item.annotation_id):
                digest.update(annotation.annotation_id.encode("utf-8"))
                digest.update(annotation.category.encode("utf-8"))
                digest.update(annotation.kind.value.encode("utf-8"))
                digest.update(str(len(annotation.points)).encode("utf-8"))
            for path in (sample.image_path, sample.annotation_path):
                if path is None:
                    continue
                digest.update(str(path).encode("utf-8"))
                if path.exists():
                    stat = path.stat()
                    digest.update(str(stat.st_size).encode("utf-8"))
                    digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        return digest.hexdigest()

    def write(self, record: DatasetVersionRecord, path: str | Path) -> Path:
        """Write a dataset version record to JSON."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(record.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        return output_path

    def read(self, path: str | Path) -> DatasetVersionRecord:
        """Read a dataset version record from JSON."""
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, Mapping):
            raise ValueError(f"Dataset version record must be a JSON object: {path}")
        return DatasetVersionRecord.from_dict(data)

    def bump(self, version: str, *, part: str = "patch") -> str:
        """Bump a semantic dataset version string."""
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
        if not match:
            raise ValueError(f"Version must be semantic major.minor.patch: {version}")
        major, minor, patch = (int(value) for value in match.groups())
        if part == "major":
            return f"{major + 1}.0.0"
        if part == "minor":
            return f"{major}.{minor + 1}.0"
        if part == "patch":
            return f"{major}.{minor}.{patch + 1}"
        raise ValueError("Version bump part must be one of: major, minor, patch.")


def _dataset_source_paths(dataset: FloorplanDataset) -> set[str]:
    paths: set[str] = set()
    for sample in dataset:
        for path in (sample.image_path, sample.annotation_path):
            if path is not None:
                paths.add(str(path))
    return paths
