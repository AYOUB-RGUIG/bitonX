# Shared Contracts

Shared contracts define the BitonX Engineering Intelligence pipeline before implementation.

## Mandatory Architecture

BitonX is not an OCR application. It is an Engineering Intelligence Platform.

AI is limited to perception and interpretation:

- Image enhancement
- OCR
- Object detection
- Semantic segmentation

Deterministic engineering owns all final engineering outputs:

- Vectorization
- Geometry reconstruction
- Engineering graph construction
- Engineering rule engine
- Formula engine
- Quantity takeoff
- Cost estimation
- BOQ generation
- Report generation

No LLM may calculate quantities. No deep learning model may estimate quantities.

## Contract Files

- `manifest.json`: canonical pipeline order and architecture guardrails.
- `common.schema.json`: shared primitives, enums, geometry fragments, and trace metadata.
- `system.schema.json`: project, upload, artifact, job, and API error contracts.
- `perception.schema.json`: image enhancement, OCR, detection, and segmentation contracts.
- `engineering.schema.json`: vectorization, geometry, graph, rule, formula, and quantity contracts.
- `reporting.schema.json`: cost, BOQ, and report contracts.
- `examples/`: minimal valid example payloads.

## Validation

Run:

```powershell
python scripts/validate-contracts.py
```
