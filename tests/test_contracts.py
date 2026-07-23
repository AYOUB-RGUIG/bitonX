import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "shared" / "contracts"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def test_manifest_enforces_engineering_intelligence_pipeline() -> None:
    manifest = load_json(CONTRACTS_DIR / "manifest.json")

    assert manifest["mandatoryConstraint"]["bitonxIsOcrApplication"] is False
    assert manifest["mandatoryConstraint"]["aiProducesFinalQuantities"] is False
    assert manifest["mandatoryConstraint"]["llmMayCalculateQuantities"] is False
    assert manifest["mandatoryConstraint"]["deepLearningMayEstimateQuantities"] is False

    stage_ids = [stage["id"] for stage in manifest["pipeline"]]
    assert stage_ids == [
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


def test_perception_schemas_require_no_final_quantity_guardrail() -> None:
    perception = load_json(CONTRACTS_DIR / "perception.schema.json")

    for name, definition in perception["$defs"].items():
        if name.endswith("Result"):
            assert "guardrail" in definition["required"], name


def test_quantity_contract_requires_deterministic_formula_producer() -> None:
    engineering = load_json(CONTRACTS_DIR / "engineering.schema.json")
    quantity_item = engineering["$defs"]["QuantityItem"]

    assert quantity_item["properties"]["producerKind"]["const"] == "deterministic_formula_engine"
    assert "formulaExecutionId" in quantity_item["required"]
    assert "engineeringRuleResultIds" in quantity_item["required"]
    assert "sourceGeometryIds" in quantity_item["required"]
