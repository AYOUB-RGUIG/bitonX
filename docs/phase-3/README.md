# BitonX Phase 3

Phase 3 creates shared contracts for the approved Engineering Intelligence architecture.

## Objectives

1. Define the mandatory drawing-to-report pipeline.
2. Separate AI perception contracts from deterministic engineering contracts.
3. Define shared schemas for pipeline jobs, artifacts, OCR, detection, segmentation, vectorization, geometry, graph, rules, formulas, quantity takeoff, cost, BOQ, reports, and errors.
4. Encode traceability requirements for every final quantity.
5. Provide example fixtures and validation tooling.

## Non-Goals

- No REST API implementation.
- No database models.
- No AI model code.
- No formula execution implementation.
- No business workflows.

## Mandatory Rule

AI is only responsible for perception and interpretation.

All engineering quantities must always be computed by deterministic engineering algorithms.

No LLM or deep learning model may calculate or estimate final quantities.

## Validation

Run:

```powershell
python scripts/validate-contracts.py
python -m unittest tests/test_contracts.py
```
