# Requirements Backlog

This backlog normalizes the source specification into implementation-ready work groups.

## Phase 2: Foundation

- Create backend package and FastAPI application.
- Create frontend Next.js application.
- Add Docker Compose for PostgreSQL, Redis, RabbitMQ, MinIO, Neo4j, backend, frontend.
- Add environment configuration and `.env.example`.
- Add Python and TypeScript formatting, linting, and type-checking.
- Add CI baseline for linting and tests.
- Add health-check endpoints.
- Add database migrations.

## Phase 3: Core Contracts

- Define shared status enums.
- Define the mandatory Engineering Intelligence pipeline manifest.
- Define AI-perception and deterministic-engineering stage boundaries.
- Define project, upload, artifact, and job schemas.
- Define OCR, detection, segmentation, vectorization, geometry, engineering graph, engineering rule, formula, quantity takeoff, cost, BOQ, and report schemas.
- Define traceability contracts proving that final quantities come from deterministic rules and formulas.
- Define guardrail metadata that forbids LLMs and deep learning models from producing final quantities.
- Add schema validation tests.
- Add example payload fixtures.
- Add API error envelope format.

## Phase 4: Upload And Orchestration

- Implement user, auth, project, and upload APIs.
- Store uploaded files in MinIO.
- Persist upload metadata in PostgreSQL.
- Generate checksums.
- Dispatch processing jobs.
- Persist pipeline stage status.
- Expose job status endpoints.

## Phase 5: Vision Preprocessing

- Convert PDF pages to images.
- Normalize PNG and JPG inputs.
- Detect page metadata and resolution.
- Deskew and rotate drawings.
- Improve contrast and reduce noise.
- Store normalized images and metadata.

## Phase 6: OCR And Scale

- Treat OCR as one perception stage, not as the product objective.
- Extract text regions.
- Extract room labels.
- Extract dimensions.
- Extract title and notes.
- Extract scale candidates.
- Persist OCR results with bounding boxes and confidence.
- Flag missing or conflicting scale for review.

## Phase 7: Baseline Detection And Segmentation

- Integrate baseline object detection.
- Detect walls, rooms, doors, windows, columns, stairs, dimensions, text, and symbols.
- Integrate baseline segmentation for core architectural elements.
- Persist detections, masks, confidence, and model version.

## Phase 8: Geometry And Graph

- Convert perception outputs into deterministic vector geometry.
- Convert masks and detections to polygons.
- Compute wall centerlines, room boundaries, openings, area, and perimeter.
- Validate geometry consistency.
- Generate engineering graph projection.
- Detect disconnected walls, floating openings, unenclosed rooms, and duplicates.

## Phase 9: Engineering Rules, Formula Engine, And Quantities

- Implement engineering rule engine.
- Implement formula registry.
- Implement unit conversion.
- Implement geometry formulas.
- Implement wall, floor, ceiling, paint, and opening-deduction formulas.
- Persist quantity trace records.
- Prohibit AI-generated final quantities in implementation and tests.
- Add deterministic formula tests.

## Phase 10: Cost, BOQ, Reports

- Implement material catalog.
- Implement cost line computation.
- Generate BOQ rows.
- Export JSON.
- Export CSV.
- Export Excel.
- Export PDF.
- Include traceability and validation notes in reports.

## Phase 11: Frontend Workspace

- Build authentication screens.
- Build dashboard and project list.
- Build upload flow.
- Build drawing viewer with pan, zoom, layers, and overlays.
- Build AI analysis panel.
- Build BOQ table with sorting, filtering, and export.
- Build report viewer.
- Add role-based UI guards.

## Phase 12: Hardening

- Add structured logging.
- Add OpenTelemetry hooks.
- Add Prometheus metrics.
- Add security checks.
- Add integration tests.
- Add deployment smoke tests.
- Add backup and restore notes.
