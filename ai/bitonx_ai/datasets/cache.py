"""On-disk dataset cache for parsed annotations and sample metadata."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from bitonx_ai.datasets.loaders import FloorplanDataset
from bitonx_ai.datasets.models import DatasetSample, JsonValue
from bitonx_ai.datasets.taxonomy import normalize_label


class DatasetCache:
    """JSON cache keyed by dataset, sample id, and source file fingerprints."""

    def __init__(self, cache_root: str | Path) -> None:
        self.cache_root = Path(cache_root)

    def cache_key(self, sample: DatasetSample) -> str:
        """Return a stable cache key for a sample and its current source files."""
        digest = hashlib.sha256()
        digest.update(sample.dataset_name.encode("utf-8"))
        digest.update(sample.sample_id.encode("utf-8"))
        digest.update(_source_fingerprint(sample).encode("utf-8"))
        return digest.hexdigest()

    def path_for_sample(self, sample: DatasetSample) -> Path:
        """Return the cache path for a sample."""
        dataset_dir = self.cache_root / normalize_label(sample.dataset_name)
        return dataset_dir / f"{self.cache_key(sample)}.json"

    def get(self, sample: DatasetSample) -> DatasetSample | None:
        """Return cached sample data if present and readable."""
        path = self.path_for_sample(sample)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, Mapping):
            return None
        return DatasetSample.from_dict(data)

    def put(self, sample: DatasetSample) -> Path:
        """Persist a sample in the cache."""
        path = self.path_for_sample(sample)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(sample.to_dict(include_annotations=True), handle, indent=2, sort_keys=True)
            handle.write("\n")
        return path

    def get_or_put(self, sample: DatasetSample) -> DatasetSample:
        """Return the cached sample, or cache and return the provided sample."""
        cached = self.get(sample)
        if cached is not None:
            return cached
        self.put(sample)
        return sample

    def cache_dataset(self, dataset: FloorplanDataset) -> dict[str, str]:
        """Cache every sample and return sample id to cache path mappings."""
        cached_paths: dict[str, str] = {}
        for sample in dataset:
            cached_paths[sample.sample_id] = str(self.put(sample))
        return cached_paths

    def remove(self, sample: DatasetSample) -> bool:
        """Remove a cached sample if it exists."""
        path = self.path_for_sample(sample)
        if not path.exists():
            return False
        path.unlink()
        return True

    def clear_dataset(self, dataset_name: str) -> int:
        """Remove cached files for one dataset and return the removed count."""
        dataset_dir = self.cache_root / normalize_label(dataset_name)
        if not dataset_dir.exists():
            return 0
        removed = 0
        for path in dataset_dir.glob("*.json"):
            path.unlink()
            removed += 1
        return removed


def _source_fingerprint(sample: DatasetSample) -> str:
    parts: list[str] = []
    for path in (sample.image_path, sample.annotation_path):
        if path is None:
            continue
        parts.append(str(path))
        if path.exists():
            stat = path.stat()
            parts.append(str(stat.st_size))
            parts.append(str(stat.st_mtime_ns))
        else:
            parts.append("missing")
    parts.append(str(len(sample.annotations)))
    return "|".join(parts)
