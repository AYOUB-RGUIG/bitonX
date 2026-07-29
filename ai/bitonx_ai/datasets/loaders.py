"""Dataset loaders and unified dataset abstractions."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import pickle
from typing import Any, overload

from bitonx_ai.datasets.models import (
    DatasetKind,
    DatasetSample,
    ImageMetadata,
    JsonValue,
    ParsedAnnotations,
    SplitName,
)
from bitonx_ai.datasets.parsers import (
    CubiCasaSvgAnnotationParser,
    DatasetParserError,
    ResPlanAnnotationParser,
)
from bitonx_ai.datasets.taxonomy import normalize_label


class DatasetLoaderError(ValueError):
    """Raised when a dataset cannot be discovered or loaded."""


class FloorplanDataset(Sequence[DatasetSample]):
    """Immutable in-memory view over floor-plan dataset samples."""

    def __init__(
        self,
        *,
        name: str,
        kind: DatasetKind,
        root: Path,
        samples: Iterable[DatasetSample],
    ) -> None:
        self.name = name
        self.kind = kind
        self.root = Path(root)
        self._samples = tuple(samples)
        self._by_id = {sample.sample_id: sample for sample in self._samples}

    @overload
    def __getitem__(self, index: int) -> DatasetSample:
        ...

    @overload
    def __getitem__(self, index: slice) -> tuple[DatasetSample, ...]:
        ...

    def __getitem__(self, index: int | slice) -> DatasetSample | tuple[DatasetSample, ...]:
        """Return one sample or a tuple slice of samples."""
        return self._samples[index]

    def __len__(self) -> int:
        """Return sample count."""
        return len(self._samples)

    def __iter__(self) -> Iterator[DatasetSample]:
        """Iterate over samples."""
        return iter(self._samples)

    @property
    def sample_ids(self) -> tuple[str, ...]:
        """Return sample identifiers in deterministic order."""
        return tuple(sample.sample_id for sample in self._samples)

    def get_sample(self, sample_id: str) -> DatasetSample:
        """Return a sample by id."""
        try:
            return self._by_id[sample_id]
        except KeyError as exc:
            raise KeyError(f"Unknown sample id: {sample_id}") from exc


class CubiCasa5KDataset(FloorplanDataset):
    """Loader for the original CubiCasa5K folder layout."""

    def __init__(
        self,
        root: str | Path,
        *,
        split: str | SplitName | None = None,
        split_file: str | Path | None = None,
        load_annotations: bool = True,
        parser: CubiCasaSvgAnnotationParser | None = None,
        strict: bool = True,
    ) -> None:
        root_path = Path(root)
        split_name = _coerce_split(split)
        parser = parser or CubiCasaSvgAnnotationParser()
        sample_dirs = _discover_cubicasa_sample_dirs(root_path, split_name, split_file)
        samples = [
            _build_cubicasa_sample(
                root_path,
                sample_dir,
                split=split_name,
                parser=parser,
                load_annotations=load_annotations,
                strict=strict,
            )
            for sample_dir in sample_dirs
        ]
        super().__init__(
            name="CubiCasa5K",
            kind=DatasetKind.CUBICASA5K,
            root=root_path,
            samples=samples,
        )


class ResPlanDataset(FloorplanDataset):
    """Loader for ResPlan vector-geometry records."""

    def __init__(
        self,
        root: str | Path,
        *,
        split: str | SplitName | None = None,
        split_file: str | Path | None = None,
        load_annotations: bool = True,
        parser: ResPlanAnnotationParser | None = None,
        strict: bool = True,
    ) -> None:
        root_path = Path(root)
        split_name = _coerce_split(split)
        parser = parser or ResPlanAnnotationParser()
        split_map = _read_split_assignments(root_path, split_file)
        records = _discover_resplan_records(root_path)
        samples: list[DatasetSample] = []
        for record_info in records:
            record_split = _record_split(record_info.record, split_map)
            if split_name is not None and record_split != split_name:
                continue
            samples.append(
                _build_resplan_sample(
                    root_path,
                    record_info,
                    split=record_split,
                    parser=parser,
                    load_annotations=load_annotations,
                    strict=strict,
                )
            )
        super().__init__(
            name="ResPlan",
            kind=DatasetKind.RESPLAN,
            root=root_path,
            samples=samples,
        )


class CompositeFloorplanDataset(FloorplanDataset):
    """Unified dataset view that combines multiple dataset loaders."""

    def __init__(self, datasets: Iterable[FloorplanDataset], *, name: str = "UnifiedFloorplans") -> None:
        dataset_tuple = tuple(datasets)
        samples: list[DatasetSample] = []
        for dataset in dataset_tuple:
            samples.extend(dataset)
        root = dataset_tuple[0].root if dataset_tuple else Path(".")
        super().__init__(name=name, kind=DatasetKind.UNIFIED, root=root, samples=samples)
        self.datasets = dataset_tuple


def load_dataset(
    kind: str | DatasetKind,
    root: str | Path,
    **kwargs: object,
) -> FloorplanDataset:
    """Factory for supported dataset loaders."""
    dataset_kind = DatasetKind(str(kind))
    if dataset_kind == DatasetKind.CUBICASA5K:
        return CubiCasa5KDataset(root, **kwargs)
    if dataset_kind == DatasetKind.RESPLAN:
        return ResPlanDataset(root, **kwargs)
    raise DatasetLoaderError(f"Cannot load dataset kind through factory: {kind!r}")


def combine_datasets(
    datasets: Iterable[FloorplanDataset],
    *,
    name: str = "UnifiedFloorplans",
) -> CompositeFloorplanDataset:
    """Return a unified abstraction over multiple datasets."""
    return CompositeFloorplanDataset(datasets, name=name)


def read_image_metadata(path: Path) -> ImageMetadata | None:
    """Read basic image metadata without retaining image pixels."""
    if not path.exists():
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    with Image.open(path) as image:
        mime_type = Image.MIME.get(image.format) if image.format else None
        return ImageMetadata(
            width=int(image.width),
            height=int(image.height),
            mode=image.mode,
            mime_type=mime_type,
        )


def _coerce_split(split: str | SplitName | None) -> SplitName | None:
    return SplitName.coerce(split) if split is not None else None


def _discover_cubicasa_sample_dirs(
    root: Path,
    split: SplitName | None,
    split_file: str | Path | None,
) -> tuple[Path, ...]:
    if split_file is not None:
        entries = _read_text_split_file(Path(split_file))
        return tuple(root / entry for entry in entries)

    if split is not None:
        resolved_split_file = _resolve_split_file(root, split)
        if resolved_split_file is not None:
            entries = _read_text_split_file(resolved_split_file)
            return tuple(root / entry for entry in entries)

    if not root.exists():
        return ()
    return tuple(sorted({path.parent for path in root.rglob("model.svg")}))


def _resolve_split_file(root: Path, split: SplitName) -> Path | None:
    candidates: dict[SplitName, tuple[str, ...]] = {
        SplitName.TRAIN: ("train.txt", "training.txt"),
        SplitName.VALIDATION: ("val.txt", "valid.txt", "validation.txt", "dev.txt"),
        SplitName.TEST: ("test.txt", "testing.txt"),
    }
    for filename in candidates[split]:
        path = root / filename
        if path.exists():
            return path
    return None


def _read_text_split_file(path: Path) -> tuple[Path, ...]:
    entries: list[Path] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                entries.append(Path(stripped.strip("/\\")))
    return tuple(entries)


def _build_cubicasa_sample(
    root: Path,
    sample_dir: Path,
    *,
    split: SplitName | None,
    parser: CubiCasaSvgAnnotationParser,
    load_annotations: bool,
    strict: bool,
) -> DatasetSample:
    annotation_path = sample_dir / "model.svg"
    image_path = _find_cubicasa_image(sample_dir)
    sample_id = _cubicasa_sample_id(root, sample_dir)
    metadata: dict[str, JsonValue] = {
        "sourceFolder": str(_relative_or_absolute(sample_dir, root)),
    }
    if sample_dir.parent != root:
        metadata["styleSubset"] = sample_dir.parent.name

    parsed = _parse_if_requested(
        parser,
        annotation_path,
        sample_id=sample_id,
        load_annotations=load_annotations,
        strict=strict,
    )
    metadata.update(parsed.metadata)
    return DatasetSample(
        sample_id=sample_id,
        dataset_name="CubiCasa5K",
        dataset_kind=DatasetKind.CUBICASA5K,
        root=root,
        image_path=image_path,
        annotation_path=annotation_path,
        split=split,
        annotations=parsed.annotations,
        graph=parsed.graph,
        image_metadata=read_image_metadata(image_path) if image_path is not None else None,
        metadata=metadata,
    )


def _find_cubicasa_image(sample_dir: Path) -> Path | None:
    candidates = (
        sample_dir / "F1_scaled.png",
        sample_dir / "F1_original.png",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for pattern in ("*scaled.png", "*.png", "*.jpg", "*.jpeg"):
        matches = sorted(sample_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def _cubicasa_sample_id(root: Path, sample_dir: Path) -> str:
    relative = _relative_or_absolute(sample_dir, root)
    return normalize_label(str(relative).replace("\\", "/"))


def _parse_if_requested(
    parser: CubiCasaSvgAnnotationParser,
    annotation_path: Path,
    *,
    sample_id: str,
    load_annotations: bool,
    strict: bool,
) -> ParsedAnnotations:
    if not load_annotations:
        return ParsedAnnotations()
    if not annotation_path.exists():
        return ParsedAnnotations(
            metadata={"parseError": f"Missing annotation file: {annotation_path}"}
        )
    try:
        return parser.parse(annotation_path, sample_id=sample_id)
    except DatasetParserError:
        if strict:
            raise
        return ParsedAnnotations(metadata={"parseError": f"Could not parse {annotation_path}"})


@dataclass(frozen=True, slots=True)
class _ResPlanRecord:
    record: Mapping[str, object]
    source_path: Path
    record_index: int
    record_key: str | None = None


def _discover_resplan_records(root: Path) -> tuple[_ResPlanRecord, ...]:
    files = _discover_resplan_files(root)
    records: list[_ResPlanRecord] = []
    for file_path in files:
        records.extend(_load_resplan_records_from_file(file_path))
    return tuple(records)


def _discover_resplan_files(root: Path) -> tuple[Path, ...]:
    if root.is_file():
        if root.suffix.lower() == ".zip":
            raise DatasetLoaderError("Extract ResPlan.zip before loading the dataset.")
        return (root,)
    if not root.exists():
        return ()
    files: list[Path] = []
    for pattern in ("*.jsonl", "*.json", "*.pkl", "*.pickle"):
        files.extend(sorted(root.glob(pattern)))
    ignored = {"split.json", "dataset.metadata.json", "dataset.version.json"}
    return tuple(path for path in files if path.name not in ignored)


def _load_resplan_records_from_file(path: Path) -> tuple[_ResPlanRecord, ...]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return _load_resplan_jsonl(path)
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return _records_from_loaded_data(data, path)
    if suffix in {".pkl", ".pickle"}:
        with path.open("rb") as handle:
            data = pickle.load(handle)
        return _records_from_loaded_data(data, path)
    raise DatasetLoaderError(f"Unsupported ResPlan data file: {path}")


def _load_resplan_jsonl(path: Path) -> tuple[_ResPlanRecord, ...]:
    records: list[_ResPlanRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            stripped = line.strip()
            if not stripped:
                continue
            data = json.loads(stripped)
            if not isinstance(data, Mapping):
                raise DatasetLoaderError(f"JSONL record {index} in {path} is not an object.")
            records.append(_ResPlanRecord(record=data, source_path=path, record_index=index))
    return tuple(records)


def _records_from_loaded_data(data: object, path: Path) -> tuple[_ResPlanRecord, ...]:
    if isinstance(data, list):
        records: list[_ResPlanRecord] = []
        for index, item in enumerate(data):
            if not isinstance(item, Mapping):
                continue
            records.append(_ResPlanRecord(record=item, source_path=path, record_index=index))
        return tuple(records)

    if isinstance(data, Mapping):
        if _looks_like_single_resplan_record(data):
            return (_ResPlanRecord(record=data, source_path=path, record_index=0),)
        records = []
        for index, (key, item) in enumerate(data.items()):
            if isinstance(item, Mapping):
                records.append(
                    _ResPlanRecord(
                        record=item,
                        source_path=path,
                        record_index=index,
                        record_key=str(key),
                    )
                )
        return tuple(records)
    raise DatasetLoaderError(f"Unsupported ResPlan data container in {path}")


def _looks_like_single_resplan_record(data: Mapping[object, object]) -> bool:
    single_record_markers = {
        "area",
        "bathroom",
        "bedroom",
        "door",
        "graph",
        "inner",
        "kitchen",
        "living",
        "planID",
        "plan_id",
        "unitType",
        "wall",
        "wall_depth",
        "window",
    }
    return any(str(key) in single_record_markers for key in data)


def _read_split_assignments(
    root: Path,
    split_file: str | Path | None,
) -> dict[str, SplitName]:
    path: Path | None
    if split_file is not None:
        path = Path(split_file)
    elif root.is_dir() and (root / "split.json").exists():
        path = root / "split.json"
    else:
        path = None
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    assignments: dict[str, SplitName] = {}
    if isinstance(data, Mapping):
        for split_name, sample_ids in data.items():
            try:
                split = SplitName.coerce(str(split_name))
            except ValueError:
                continue
            if isinstance(sample_ids, Iterable) and not isinstance(sample_ids, (str, bytes)):
                for sample_id in sample_ids:
                    assignments[str(sample_id)] = split
    return assignments


def _record_split(record: Mapping[str, object], split_map: Mapping[str, SplitName]) -> SplitName | None:
    for key in _record_id_candidates(record, None):
        if key in split_map:
            return split_map[key]
    split_value = record.get("split")
    if split_value is not None:
        try:
            return SplitName.coerce(str(split_value))
        except ValueError:
            return None
    return None


def _record_id_candidates(record: Mapping[str, object], record_key: str | None) -> tuple[str, ...]:
    candidates: list[str] = []
    if record_key is not None:
        candidates.append(record_key)
    for key in ("planID", "plan_id", "id", "name"):
        value = record.get(key)
        if value is not None:
            candidates.append(str(value))
    return tuple(dict.fromkeys(candidates))


def _build_resplan_sample(
    root: Path,
    record_info: _ResPlanRecord,
    *,
    split: SplitName | None,
    parser: ResPlanAnnotationParser,
    load_annotations: bool,
    strict: bool,
) -> DatasetSample:
    sample_id = _resplan_sample_id(record_info.record, record_info.record_key, record_info.record_index)
    image_path = _resplan_image_path(root, record_info.record)
    metadata: dict[str, JsonValue] = {
        "sourceFile": str(record_info.source_path),
        "sourceRecordIndex": record_info.record_index,
    }
    if record_info.record_key is not None:
        metadata["sourceRecordKey"] = record_info.record_key

    parsed = ParsedAnnotations()
    if load_annotations:
        try:
            parsed = parser.parse_record(
                record_info.record,
                sample_id=sample_id,
                source_path=record_info.source_path,
                record_key=record_info.record_key,
            )
        except DatasetParserError:
            if strict:
                raise
            parsed = ParsedAnnotations(metadata={"parseError": f"Could not parse {sample_id}"})
    metadata.update(parsed.metadata)
    return DatasetSample(
        sample_id=sample_id,
        dataset_name="ResPlan",
        dataset_kind=DatasetKind.RESPLAN,
        root=root,
        image_path=image_path,
        annotation_path=record_info.source_path,
        split=split,
        annotations=parsed.annotations,
        graph=parsed.graph,
        image_metadata=read_image_metadata(image_path) if image_path is not None else None,
        metadata=metadata,
    )


def _resplan_sample_id(
    record: Mapping[str, object],
    record_key: str | None,
    record_index: int,
) -> str:
    candidates = _record_id_candidates(record, record_key)
    if candidates:
        return normalize_label(candidates[0])
    return f"resplan_{record_index:06d}"


def _resplan_image_path(root: Path, record: Mapping[str, object]) -> Path | None:
    raw_path = record.get("image_path") or record.get("image")
    if raw_path is None:
        return None
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    base = root if root.is_dir() else root.parent
    return base / path


def _relative_or_absolute(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path
