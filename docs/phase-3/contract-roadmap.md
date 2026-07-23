# Phase 3 Contract Roadmap

The Phase 3 contract package must make the pipeline enforceable before implementation begins.

## Pipeline Stages

1. Drawing
2. Image enhancement
3. OCR
4. Object detection
5. Semantic segmentation
6. Vectorization
7. Geometry reconstruction
8. Engineering graph construction
9. Engineering rule engine
10. Formula engine
11. Quantity takeoff
12. Cost estimation
13. BOQ generation
14. Report generation

## AI Perception Stages

- Image enhancement
- OCR
- Object detection
- Semantic segmentation

These stages may use computer vision, OCR, and deep learning. Their outputs are evidence, not final quantities.

## Deterministic Engineering Stages

- Vectorization
- Geometry reconstruction
- Engineering graph construction
- Engineering rule engine
- Formula engine
- Quantity takeoff
- Cost estimation
- BOQ generation
- Report generation

These stages must be deterministic, explainable, versioned, and reproducible.

## Guardrails

- LLM quantity calculation is forbidden.
- Deep learning quantity estimation is forbidden.
- AI output cannot become a final quantity without rule and formula execution.
- Quantity records must reference source geometry, rule results, formula results, units, and intermediate values.
- Missing or contradictory perception evidence must produce `needs_review`, not fabricated quantities.

