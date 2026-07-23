# MVP Freeze

This document freezes the initial BitonX build scope into a constrained, implementable MVP.

## MVP Objective

Build the first usable BitonX Quant workflow for 2D architectural drawing quantity takeoff:

1. Upload a PDF, PNG, or JPG architectural floor plan.
2. Normalize the drawing into processable images.
3. Extract text, dimensions, and scale candidates.
4. Detect basic building elements.
5. Reconstruct simple engineering geometry.
6. Calculate deterministic quantities through the formula engine.
7. Generate an explainable BOQ and report artifacts.

## Frozen In Scope

- User authentication with JWT.
- Basic role model: administrator, engineer, viewer.
- Project creation and drawing upload.
- Supported inputs: PDF, PNG, JPG.
- Initial drawing type: 2D architectural floor plans.
- AI pipeline orchestration through asynchronous jobs.
- Vision preprocessing for PDF-to-image conversion, cleanup, rotation, deskew, and metadata.
- OCR extraction for text, room labels, dimensions, title, notes, and scale candidates.
- Baseline detection for walls, doors, windows, rooms, columns, stairs, text, dimensions, and symbols.
- Baseline segmentation for walls, rooms, doors, windows, and columns.
- Geometry reconstruction for wall lines, room polygons, openings, area, perimeter, and basic dimensions.
- Engineering graph generation for building, floor, room, wall, door, window, opening, and material relationships.
- Deterministic formula engine for length, area, perimeter, wall surface area, floor area, ceiling area, opening deductions, and basic material quantities.
- Initial cost engine using a configurable material catalog.
- Report exports: JSON first, then CSV, Excel, and PDF.
- Frontend dashboard, project list, upload view, drawing viewer, AI results panel, BOQ table, and report view.
- Observability baseline: structured logs, health checks, queue status, and pipeline timing.
- Local development through Docker Compose.

## Frozen Out Of Scope For MVP

- DWG, DXF, and IFC import.
- BIM authoring or IFC editing.
- 3D modeling, digital twin generation, and 3D reconstruction.
- Structural analysis and finite element analysis.
- Full MEP analysis.
- Real-time collaboration.
- Mobile application or offline desktop application.
- Billing and subscriptions.
- Multi-organization enterprise tenancy.
- Custom plugin marketplace.
- Production Kubernetes deployment.
- Full autonomous model training platform.
- Country-specific code compliance beyond a configurable generic metric rule pack.

## Initial Quality Targets

These targets define MVP readiness, not final production accuracy.

- File validation must reject unsupported extensions, invalid MIME types, empty files, corrupted files, and files above the configured size limit.
- Every pipeline stage must persist status, timestamps, input artifact references, output artifact references, and errors.
- Every quantity must include source object, formula identifier, inputs, intermediate values, units, result, validation status, and confidence.
- AI output must never directly become a final quantity without deterministic formula validation.
- A report must clearly separate detected values, computed values, inferred values, and user-edited values.
- The system must support partial failure reporting when some pages or stages fail.

## Initial User Workflow

1. Engineer signs in.
2. Engineer creates a project.
3. Engineer uploads a drawing.
4. Backend validates and stores the file.
5. Pipeline processes the drawing asynchronously.
6. Engineer views overlays and extracted results.
7. Engineer reviews or corrects detected scale and quantities.
8. System generates BOQ and reports.
9. Engineer exports JSON, CSV, Excel, or PDF.

## Human Review Policy

MVP reports are review-assisted, not fully autonomous. The system should support an explicit review state before a BOQ or cost estimate is marked final.

## MVP Completion Gate

The MVP is complete when one representative architectural floor plan can pass through upload, preprocessing, OCR, detection, geometry reconstruction, quantity computation, BOQ generation, and report export with traceable results.

