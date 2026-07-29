"""Dataset integrity verification and manifest generation."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from bitonx_ai.datasets.loaders import FloorplanDataset
from bitonx_ai.datasets.models import JsonValue, ValidationIssue, ValidationStatus


class DatasetIntegrityVerifier:
    """Build and verify file-level dataset integrity manifests."""

    def build_manifest(self, dataset: FloorplanDataset) -> dict[str, JsonValue]:
        """Build an integrity manifest with checksums for referenced files."""
        samples: list[dict[str, JsonValue]] = []
        content_hasher = hashlib.sha256()
        for sample in dataset:
            sample_files: list[dict[str, JsonValue]] = []
            for role, path in (("image", sample.image_path), ("annotation", sample.annotation_path)):
                if path is None:
                    continue
                file_info = _file_integrity_info(path, role=role)
                sample_files.append(file_info)
                content_hasher.update(json.dumps(file_info, sort_keys=True).encode("utf-8"))
            sample_entry: dict[str, JsonValue] = {
                "sampleId": sample.sample_id,
                "datasetKind": sample.dataset_kind.value,
                "annotationCount": len(sample.annotations),
                "files": sample_files,
            }
            samples.append(sample_entry)
            content_hasher.update(sample.sample_id.encode("utf-8"))
            content_hasher.update(str(len(sample.annotations)).encode("utf-8"))

        return {
            "datasetName": dataset.name,
            "datasetKind": dataset.kind.value,
            "sampleCount": len(dataset),
            "contentHash": content_hasher.hexdigest(),
            "samples": samples,
        }

    def verify_manifest(
        self,
        dataset: FloorplanDataset,
        manifest: Mapping[str, object],
    ) -> tuple[ValidationIssue, ...]:
        """Verify a dataset against a previously generated manifest."""
        issues: list[ValidationIssue] = []
        expected_sample_count = manifest.get("sampleCount")
        if expected_sample_count != len(dataset):
            issues.append(
                ValidationIssue(
                    code="INTEGRITY_SAMPLE_COUNT_MISMATCH",
                    message=(
                        f"Manifest sample count {expected_sample_count} does not match "
                        f"dataset count {len(dataset)}."
                    ),
                    status=ValidationStatus.INVALID,
                )
            )

        sample_manifest = _manifest_by_sample_id(manifest)
        for sample in dataset:
            expected = sample_manifest.get(sample.sample_id)
            if expected is None:
                issues.append(
                    ValidationIssue(
                        code="INTEGRITY_SAMPLE_MISSING",
                        message=f"Sample is missing from integrity manifest: {sample.sample_id}",
                        status=ValidationStatus.INVALID,
                        sample_id=sample.sample_id,
                    )
                )
                continue
            issues.extend(_verify_sample_files(sample.sample_id, expected))
        return tuple(issues)

    def write_manifest(self, manifest: Mapping[str, object], path: str | Path) -> Path:
        """Write an integrity manifest to JSON."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        return output_path

    def read_manifest(self, path: str | Path) -> dict[str, object]:
        """Read an integrity manifest from JSON."""
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Integrity manifest must be a JSON object: {path}")
        return data


def file_sha256(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 checksum for a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _file_integrity_info(path: Path, *, role: str) -> dict[str, JsonValue]:
    exists = path.exists()
    info: dict[str, JsonValue] = {
        "role": role,
        "path": str(path),
        "exists": exists,
    }
    if not exists:
        return info
    stat = path.stat()
    info.update(
        {
            "sizeBytes": stat.st_size,
            "modifiedNs": stat.st_mtime_ns,
            "sha256": file_sha256(path),
        }
    )
    return info


def _manifest_by_sample_id(manifest: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    raw_samples = manifest.get("samples", [])
    samples: dict[str, Mapping[str, object]] = {}
    if not isinstance(raw_samples, list):
        return samples
    for raw_sample in raw_samples:
        if isinstance(raw_sample, Mapping):
            sample_id = raw_sample.get("sampleId")
            if sample_id is not None:
                samples[str(sample_id)] = raw_sample
    return samples


def _verify_sample_files(
    sample_id: str,
    sample_manifest: Mapping[str, object],
) -> tuple[ValidationIssue, ...]:
    raw_files = sample_manifest.get("files", [])
    if not isinstance(raw_files, list):
        return (
            ValidationIssue(
                code="INTEGRITY_FILES_INVALID",
                message="Manifest sample files entry must be a list.",
                status=ValidationStatus.INVALID,
                sample_id=sample_id,
            ),
        )

    issues: list[ValidationIssue] = []
    for raw_file in raw_files:
        if not isinstance(raw_file, Mapping):
            continue
        path_value = raw_file.get("path")
        if path_value is None:
            continue
        path = Path(str(path_value))
        if not path.exists():
            issues.append(
                ValidationIssue(
                    code="INTEGRITY_FILE_MISSING",
                    message=f"Referenced dataset file is missing: {path}",
                    status=ValidationStatus.INVALID,
                    sample_id=sample_id,
                    path=path,
                )
            )
            continue
        expected_size = raw_file.get("sizeBytes")
        if expected_size is not None and int(expected_size) != path.stat().st_size:
            issues.append(
                ValidationIssue(
                    code="INTEGRITY_FILE_SIZE_MISMATCH",
                    message=f"File size changed for {path}",
                    status=ValidationStatus.INVALID,
                    sample_id=sample_id,
                    path=path,
                )
            )
        expected_checksum = raw_file.get("sha256")
        if expected_checksum is not None and str(expected_checksum) != file_sha256(path):
            issues.append(
                ValidationIssue(
                    code="INTEGRITY_CHECKSUM_MISMATCH",
                    message=f"Checksum changed for {path}",
                    status=ValidationStatus.INVALID,
                    sample_id=sample_id,
                    path=path,
                )
            )
    return tuple(issues)
