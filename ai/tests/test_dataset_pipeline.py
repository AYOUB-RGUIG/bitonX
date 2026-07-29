from __future__ import annotations

import base64
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from bitonx_ai.datasets import (
    CubiCasa5KDataset,
    DatasetCache,
    DatasetIntegrityVerifier,
    DatasetMetadataManager,
    DatasetStatisticsCalculator,
    DatasetValidator,
    DatasetVersionManager,
    DatasetVisualizer,
    FloorplanDataset,
    ResPlanDataset,
    SplitManager,
    SplitName,
    SplitRatios,
    ValidationStatus,
    combine_datasets,
)


class DatasetPipelineTest(unittest.TestCase):
    def test_cubicasa_loader_parses_svg_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            dataset_root = _write_cubicasa_fixture(tmp_path)

            dataset = CubiCasa5KDataset(dataset_root)

            self.assertEqual(len(dataset), 1)
            sample = dataset[0]
            self.assertEqual(sample.sample_id, "high_quality_architectural_41")
            self.assertIsNotNone(sample.image_path)
            self.assertTrue(sample.image_path.exists() if sample.image_path else False)
            self.assertTrue(
                {"wall", "door", "window", "kitchen", "bedroom", "plumbing"}.issubset(
                    set(sample.categories)
                )
            )
            self.assertTrue(
                all(annotation.phase3_object_type != "unknown" for annotation in sample.annotations)
            )

            report = DatasetValidator(validate_images=False).validate(dataset)
            self.assertEqual(report.status, ValidationStatus.VALID)

    def test_resplan_loader_parses_vector_records_and_canonical_split(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            dataset_root = _write_resplan_fixture(tmp_path)

            dataset = ResPlanDataset(dataset_root, split=SplitName.TRAIN)

            self.assertEqual(len(dataset), 1)
            sample = dataset[0]
            self.assertEqual(sample.sample_id, "rp_1")
            self.assertEqual(sample.split, SplitName.TRAIN)
            self.assertTrue({"bedroom", "living", "wall", "door"}.issubset(set(sample.categories)))
            self.assertIsNotNone(sample.graph)
            self.assertEqual(len(sample.graph.nodes) if sample.graph else 0, 2)
            self.assertEqual(len(sample.graph.edges) if sample.graph else 0, 1)

            report = DatasetValidator(validate_images=False).validate(dataset)
            self.assertEqual(report.status, ValidationStatus.VALID)

    def test_dataset_management_tools_operate_on_unified_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            cubicasa = CubiCasa5KDataset(_write_cubicasa_fixture(tmp_path))
            resplan = ResPlanDataset(_write_resplan_fixture(tmp_path), split=SplitName.TRAIN)
            dataset = combine_datasets([cubicasa, resplan], name="Phase4Fixture")

            statistics = DatasetStatisticsCalculator().compute(dataset)
            self.assertEqual(statistics.sample_count, 2)
            self.assertGreaterEqual(statistics.category_counts["wall"], 2)

            split_manager = SplitManager()
            split_manifest = split_manager.create(
                dataset,
                ratios=SplitRatios(train=0.5, validation=0.0, test=0.5),
                seed=7,
            )
            split_path = split_manager.write(split_manifest, tmp_path / "splits.json")
            self.assertEqual(split_manager.read(split_path).assignments, split_manifest.assignments)
            split_dataset = split_manager.apply(dataset, split_manifest)
            self.assertEqual({sample.split for sample in split_dataset}, {SplitName.TRAIN, SplitName.TEST})

            cache = DatasetCache(tmp_path / "cache")
            cached_path = cache.put(dataset[0])
            self.assertTrue(cached_path.exists())
            cached_sample = cache.get(dataset[0])
            self.assertIsNotNone(cached_sample)
            self.assertEqual(cached_sample.sample_id if cached_sample else "", dataset[0].sample_id)

            version_manager = DatasetVersionManager()
            version_record = version_manager.create_record(
                dataset,
                dataset_version="1.0.0",
                metadata={"phase": "4"},
            )
            version_path = version_manager.write(version_record, tmp_path / "dataset.version.json")
            self.assertEqual(
                version_manager.read(version_path).content_hash,
                version_record.content_hash,
            )
            self.assertEqual(version_manager.bump("1.0.0"), "1.0.1")

            metadata_manager = DatasetMetadataManager()
            metadata = metadata_manager.collect(
                dataset,
                statistics=statistics,
                version=version_record,
                license_name="fixture-only",
                source_url="https://example.invalid/dataset",
            )
            metadata_path = metadata_manager.write(metadata, tmp_path / "dataset.metadata.json")
            self.assertEqual(metadata_manager.read(metadata_path)["sampleCount"], 2)

            integrity = DatasetIntegrityVerifier()
            manifest = integrity.build_manifest(dataset)
            manifest_path = integrity.write_manifest(manifest, tmp_path / "dataset.integrity.json")
            self.assertFalse(integrity.verify_manifest(dataset, integrity.read_manifest(manifest_path)))

            visualizer = DatasetVisualizer()
            svg_path = visualizer.write_sample_svg(dataset[0], tmp_path / "sample.svg")
            preview_path = visualizer.write_dataset_preview_html(dataset, tmp_path / "preview.html")
            self.assertIn("<polygon", svg_path.read_text(encoding="utf-8"))
            self.assertIn("Phase4Fixture", preview_path.read_text(encoding="utf-8"))

    def test_validator_rejects_forbidden_phase4_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            dataset = CubiCasa5KDataset(_write_cubicasa_fixture(tmp_path))
            bad_sample = replace(
                dataset[0],
                metadata={**dataset[0].metadata, "ocrResult": "not allowed"},
            )
            bad_dataset = FloorplanDataset(
                name="bad",
                kind=dataset.kind,
                root=dataset.root,
                samples=[bad_sample],
            )

            report = DatasetValidator(validate_images=False).validate(bad_dataset)

            self.assertEqual(report.status, ValidationStatus.INVALID)
            self.assertTrue(
                any(issue.code == "PHASE4_FORBIDDEN_OUTPUT_METADATA" for issue in report.issues)
            )


def _write_cubicasa_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "cubicasa5k"
    sample_dir = root / "high_quality_architectural" / "41"
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "model.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80">
  <g id="Wall"><polygon points="0,0 100,0 100,5 0,5" /></g>
  <g id="Door"><polygon points="45,0 55,0 55,5 45,5" /></g>
  <g id="Window"><polygon points="0,30 5,30 5,50 0,50" /></g>
  <g class="Space Kitchen"><polygon points="5,5 50,5 50,40 5,40" /></g>
  <g class="Space Bedroom"><polygon points="50,5 95,5 95,40 50,40" /></g>
  <g class="FixedFurniture Toilet"><polygon points="70,20 80,20 80,30 70,30" /></g>
</svg>
""",
        encoding="utf-8",
    )
    (sample_dir / "F1_scaled.png").write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/"
            "l8fG8wAAAABJRU5ErkJggg=="
        )
    )
    return root


def _write_resplan_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "resplan"
    root.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "planID": "rp-1",
            "unitType": "Apartment",
            "area": 42.0,
            "wall_depth": 0.15,
            "bedroom": "POLYGON ((0 0, 4 0, 4 3, 0 3, 0 0))",
            "living": {
                "type": "Polygon",
                "coordinates": [[[4, 0], [8, 0], [8, 3], [4, 3], [4, 0]]],
            },
            "wall": "POLYGON ((3.9 0, 4.1 0, 4.1 3, 3.9 3, 3.9 0))",
            "door": "POLYGON ((3.9 1, 4.1 1, 4.1 2, 3.9 2, 3.9 1))",
            "graph": {
                "nodes": [
                    {"id": "bedroom_0", "type": "bedroom", "centroid": [2, 1.5]},
                    {"id": "living_0", "type": "living", "centroid": [6, 1.5]},
                ],
                "edges": [
                    {"source": "bedroom_0", "target": "living_0", "type": "via_door"}
                ],
            },
        },
        {
            "planID": "rp-2",
            "unitType": "Villa",
            "area": 64.0,
            "bedroom": "POLYGON ((0 0, 5 0, 5 5, 0 5, 0 0))",
        },
    ]
    with (root / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record))
            handle.write("\n")
    (root / "split.json").write_text(
        json.dumps({"train": ["rp-1"], "validation": ["rp-2"], "test": []}),
        encoding="utf-8",
    )
    return root


if __name__ == "__main__":
    unittest.main()
