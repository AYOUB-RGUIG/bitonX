"""Deterministic train/validation/test split management."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, replace
import json
from pathlib import Path
import random

from bitonx_ai.datasets.loaders import FloorplanDataset
from bitonx_ai.datasets.models import DatasetKind, DatasetSample, JsonValue, SplitName


@dataclass(frozen=True, slots=True)
class SplitRatios:
    """Train/validation/test ratios."""

    train: float = 0.8
    validation: float = 0.1
    test: float = 0.1

    def __post_init__(self) -> None:
        total = self.train + self.validation + self.test
        if any(value < 0 for value in (self.train, self.validation, self.test)):
            raise ValueError("Split ratios must be non-negative.")
        if abs(total - 1.0) > 1e-6:
            raise ValueError("Split ratios must sum to 1.0.")

    def to_dict(self) -> dict[str, float]:
        """Serialize ratios."""
        return {
            "train": self.train,
            "validation": self.validation,
            "test": self.test,
        }


@dataclass(frozen=True, slots=True)
class SplitManifest:
    """Persisted deterministic split assignments."""

    dataset_name: str
    dataset_kind: DatasetKind
    seed: int
    ratios: SplitRatios
    assignments: Mapping[str, SplitName]
    stratify_by: str | None = None

    @property
    def by_split(self) -> dict[str, list[str]]:
        """Return assignments grouped by split."""
        grouped: dict[str, list[str]] = {
            SplitName.TRAIN.value: [],
            SplitName.VALIDATION.value: [],
            SplitName.TEST.value: [],
        }
        for sample_id, split in self.assignments.items():
            grouped[split.value].append(sample_id)
        for sample_ids in grouped.values():
            sample_ids.sort()
        return grouped

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the split manifest."""
        return {
            "datasetName": self.dataset_name,
            "datasetKind": self.dataset_kind.value,
            "seed": self.seed,
            "ratios": self.ratios.to_dict(),
            "stratifyBy": self.stratify_by,
            "assignments": self.by_split,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SplitManifest":
        """Deserialize the split manifest."""
        ratios_data = data.get("ratios", {})
        ratios = (
            SplitRatios(
                train=float(ratios_data.get("train", 0.8)),
                validation=float(ratios_data.get("validation", 0.1)),
                test=float(ratios_data.get("test", 0.1)),
            )
            if isinstance(ratios_data, Mapping)
            else SplitRatios()
        )
        raw_assignments = data.get("assignments", {})
        assignments: dict[str, SplitName] = {}
        if isinstance(raw_assignments, Mapping):
            for split_name, sample_ids in raw_assignments.items():
                split = SplitName.coerce(str(split_name))
                if isinstance(sample_ids, list):
                    for sample_id in sample_ids:
                        assignments[str(sample_id)] = split
        return cls(
            dataset_name=str(data["datasetName"]),
            dataset_kind=DatasetKind(str(data["datasetKind"])),
            seed=int(data["seed"]),
            ratios=ratios,
            assignments=assignments,
            stratify_by=str(data["stratifyBy"]) if data.get("stratifyBy") is not None else None,
        )


class SplitManager:
    """Create, persist, and apply deterministic dataset splits."""

    def create(
        self,
        dataset: FloorplanDataset,
        *,
        ratios: SplitRatios | None = None,
        seed: int = 13,
        stratify_by: str | None = None,
    ) -> SplitManifest:
        """Create deterministic train/validation/test assignments."""
        split_ratios = ratios or SplitRatios()
        assignments: dict[str, SplitName] = {}
        groups = _group_samples(dataset, stratify_by)
        for group_key, sample_ids in groups.items():
            rng = random.Random(f"{seed}:{group_key}")
            shuffled = sorted(sample_ids)
            rng.shuffle(shuffled)
            assignments.update(_assign_group(shuffled, split_ratios))
        return SplitManifest(
            dataset_name=dataset.name,
            dataset_kind=dataset.kind,
            seed=seed,
            ratios=split_ratios,
            assignments=dict(sorted(assignments.items())),
            stratify_by=stratify_by,
        )

    def apply(self, dataset: FloorplanDataset, manifest: SplitManifest) -> FloorplanDataset:
        """Return a dataset view with split assignments applied."""
        samples: list[DatasetSample] = []
        for sample in dataset:
            split = manifest.assignments.get(sample.sample_id, sample.split)
            samples.append(replace(sample, split=split))
        return FloorplanDataset(
            name=dataset.name,
            kind=dataset.kind,
            root=dataset.root,
            samples=samples,
        )

    def write(self, manifest: SplitManifest, path: str | Path) -> Path:
        """Write a split manifest to JSON."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        return output_path

    def read(self, path: str | Path) -> SplitManifest:
        """Read a split manifest from JSON."""
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, Mapping):
            raise ValueError(f"Split manifest must be a JSON object: {path}")
        return SplitManifest.from_dict(data)


def _group_samples(
    dataset: FloorplanDataset,
    stratify_by: str | None,
) -> dict[str, list[str]]:
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for sample in dataset:
        if stratify_by is None:
            key = "all"
        else:
            value = sample.metadata.get(stratify_by)
            key = str(value) if value is not None else "missing"
        groups[key].append(sample.sample_id)
    return dict(groups)


def _assign_group(sample_ids: list[str], ratios: SplitRatios) -> dict[str, SplitName]:
    count = len(sample_ids)
    train_count = int(count * ratios.train)
    validation_count = int(count * ratios.validation)
    assignments: dict[str, SplitName] = {}
    for index, sample_id in enumerate(sample_ids):
        if index < train_count:
            split = SplitName.TRAIN
        elif index < train_count + validation_count:
            split = SplitName.VALIDATION
        else:
            split = SplitName.TEST
        assignments[sample_id] = split
    return assignments
