"""Validate Phase 3 contract files without external dependencies."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "shared" / "contracts"

EXPECTED_PIPELINE = [
    "drawing",
    "image_enhancement",
    "ocr",
    "object_detection",
    "semantic_segmentation",
    "vectorization",
    "geometry_reconstruction",
    "engineering_graph_construction",
    "engineering_rule_engine",
    "formula_engine",
    "quantity_takeoff",
    "cost_estimation",
    "boq_generation",
    "report_generation",
]

AI_STAGES = {"image_enhancement", "ocr", "object_detection", "semantic_segmentation"}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_manifest() -> None:
    manifest = load_json(CONTRACTS_DIR / "manifest.json")
    stages = manifest["pipeline"]
    ids = [stage["id"] for stage in stages]
    orders = [stage["order"] for stage in stages]

    assert_condition(ids == EXPECTED_PIPELINE, "Pipeline stage order does not match the mandate.")
    assert_condition(orders == list(range(1, len(EXPECTED_PIPELINE) + 1)), "Pipeline orders are invalid.")

    constraint = manifest["mandatoryConstraint"]
    assert_condition(constraint["bitonxIsOcrApplication"] is False, "BitonX must not be marked as OCR-only.")
    assert_condition(constraint["aiProducesFinalQuantities"] is False, "AI cannot produce final quantities.")
    assert_condition(constraint["llmMayCalculateQuantities"] is False, "LLMs cannot calculate quantities.")
    assert_condition(
        constraint["deepLearningMayEstimateQuantities"] is False,
        "Deep learning cannot estimate quantities.",
    )

    for stage in stages:
        stage_id = stage["id"]
        if stage_id in AI_STAGES:
            assert_condition(stage["kind"] == "ai_perception", f"{stage_id} must be AI perception.")
            assert_condition(stage["mayProduceFinalQuantity"] is False, f"{stage_id} cannot produce quantities.")
        elif stage_id != "drawing":
            assert_condition(
                stage["kind"] == "deterministic_engineering",
                f"{stage_id} must be deterministic engineering.",
            )
            assert_condition(stage["aiAllowed"] is False, f"{stage_id} cannot allow AI.")


def validate_schema_refs() -> None:
    schema_files = sorted(CONTRACTS_DIR.glob("*.schema.json"))
    available = {path.name for path in schema_files}

    for schema_file in schema_files:
        schema_text = schema_file.read_text(encoding="utf-8")
        schema = json.loads(schema_text)
        assert_condition("$schema" in schema, f"{schema_file.name} is missing $schema.")
        for token in schema_text.split('"$ref": "')[1:]:
            ref = token.split('"', 1)[0]
            if ".schema.json" in ref:
                ref_file = ref.split("#", 1)[0]
                assert_condition(ref_file in available, f"{schema_file.name} references missing {ref_file}.")


def validate_guardrail_shapes() -> None:
    common = load_json(CONTRACTS_DIR / "common.schema.json")
    perception = load_json(CONTRACTS_DIR / "perception.schema.json")
    engineering = load_json(CONTRACTS_DIR / "engineering.schema.json")

    no_quantity_guardrail = common["$defs"]["NoFinalQuantityGuardrail"]["properties"]
    assert_condition(
        no_quantity_guardrail["producesFinalQuantities"]["const"] is False,
        "Perception guardrail must forbid final quantities.",
    )

    for name, definition in perception["$defs"].items():
        if name.endswith("Result"):
            required = set(definition.get("required", []))
            assert_condition("guardrail" in required, f"{name} must require guardrail.")

    quantity_item = engineering["$defs"]["QuantityItem"]
    producer = quantity_item["properties"]["producerKind"]["const"]
    assert_condition(
        producer == "deterministic_formula_engine",
        "Quantity producer must be deterministic formula engine.",
    )


def validate_examples() -> None:
    examples = sorted((CONTRACTS_DIR / "examples").glob("*.json"))
    assert_condition(bool(examples), "No contract examples found.")

    for example in examples:
        payload = load_json(example)
        assert_condition(isinstance(payload, dict), f"{example.name} must contain a JSON object.")

    quantity = load_json(CONTRACTS_DIR / "examples" / "quantity-takeoff.example.json")
    for item in quantity["items"]:
        assert_condition(
            item["producerKind"] == "deterministic_formula_engine",
            "Quantity example violates deterministic producer rule.",
        )
        assert_condition(item["sourceGeometryIds"], "Quantity example needs source geometry.")
        assert_condition(item["engineeringRuleResultIds"], "Quantity example needs rule results.")
        assert_condition(item["formulaExecutionId"], "Quantity example needs formula execution.")


def main() -> int:
    try:
        validate_manifest()
        validate_schema_refs()
        validate_guardrail_shapes()
        validate_examples()
    except AssertionError as exc:
        print(f"Contract validation failed: {exc}", file=sys.stderr)
        return 1

    print("Contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

