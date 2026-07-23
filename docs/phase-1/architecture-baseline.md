# Architecture Baseline

This document normalizes the BitonX architecture into an implementation baseline.

## Architecture Choice

BitonX should begin as a modular monolith with asynchronous workers, not as separately deployed microservices.

The codebase must preserve service boundaries that can later become independent services:

- Auth service
- User service
- Project service
- Upload service
- Storage service
- Vision service
- OCR service
- Detection service
- Segmentation service
- Geometry service
- Graph service
- Quantity service
- Cost service
- Reporting service
- Notification service
- Model registry service

This keeps the architecture aligned with the specification while avoiding early distributed-system overhead.

## Primary System Components

- Frontend: Next.js, React, TypeScript, TailwindCSS, shadcn/ui, TanStack Query, Zustand, Konva, PDF.js.
- Backend API: FastAPI, Pydantic, SQLAlchemy, Alembic, JWT, OAuth2-ready authentication.
- Workers: Celery workers coordinated through RabbitMQ.
- Cache: Redis.
- Primary database: PostgreSQL.
- Graph database: Neo4j.
- Object storage: MinIO.
- AI runtime: Python, PyTorch, OpenCV, OCR libraries, ONNX Runtime where useful.
- Reporting: JSON, CSV, Excel, PDF generation.
- Local infrastructure: Docker Compose.

## Canonical Data Ownership

PostgreSQL is the canonical system of record for users, projects, uploads, jobs, artifacts, detected objects, geometry summaries, quantities, BOQ rows, reports, and audit logs.

MinIO is the canonical binary artifact store for uploaded files, normalized images, masks, model checkpoints, generated reports, and dataset cache files.

Neo4j is a graph projection generated from canonical pipeline outputs. It should be rebuildable from PostgreSQL and MinIO artifacts.

## Mandatory Engineering Intelligence Constraint

BitonX is not an OCR application. BitonX is an Engineering Intelligence Platform.

AI modules are allowed only for perception and interpretation. They may enhance images, classify drawings, extract text, detect objects, segment semantics, and help interpret visual evidence.

AI modules must never generate final quantities directly.

No Large Language Model may calculate quantities.

No Deep Learning model may estimate quantities.

Deep Learning is allowed only for visual understanding.

All engineering quantities must be computed by deterministic engineering algorithms. Final quantities must be fully explainable, reproducible, versioned, and traceable to source geometry, rule execution, and formula execution.

## Mandatory Deterministic Pipeline

Every drawing must pass through this deterministic pipeline:

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

Each stage must be idempotent for the same input artifact and configuration version.

The perception stages are image enhancement, OCR, object detection, and semantic segmentation.

The deterministic engineering stages are vectorization, geometry reconstruction, engineering graph construction, engineering rule engine, formula engine, quantity takeoff, cost estimation, BOQ generation, and report generation.

## Job State Model

All asynchronous work should use a shared state model:

- pending
- queued
- running
- succeeded
- failed
- canceled
- retrying
- partial_success
- needs_review

Every job should store:

- project id
- upload id
- stage name
- input artifact ids
- output artifact ids
- model version or formula version
- status
- error code
- error message
- started at
- finished at
- execution time

## Contract-First Rule

Before implementing a pipeline stage, define its request and response schemas.

Minimum shared contracts:

- Uploaded file metadata
- Image artifact metadata
- OCR result
- Detection result
- Segmentation result
- Geometry result
- Engineering graph result
- Quantity result
- Cost result
- Report result
- Pipeline job status

## Formula Engine Rule

AI modules may detect and infer engineering objects. They must not calculate final quantities directly.

All final quantities must be produced by deterministic formula modules with:

- formula id
- formula version
- source object ids
- inputs
- units
- intermediate values
- result
- validation status
- confidence

The formula engine must consume deterministic geometry and rule outputs, not raw AI guesses. If AI output is uncertain, missing, or contradictory, the pipeline must mark the drawing as needing review rather than inventing a quantity.

## Frontend Baseline

The first frontend should be an operational workspace, not a marketing landing page.

Primary screens:

- Login
- Register
- Dashboard
- Projects
- Project detail
- Upload drawing
- Drawing viewer
- AI analysis panel
- BOQ table
- Cost estimate
- Reports
- Settings

## Security Baseline

The MVP must include:

- Password hashing
- JWT access tokens
- Refresh-token-ready architecture
- Role-based authorization
- Permission-aware backend guards
- Secure upload validation
- File checksums
- Audit logs for sensitive operations
- Rate limiting hooks
- Environment-based secrets

## Testing Baseline

Testing should start with contract and deterministic-engine tests before heavy AI tests.

Required first test categories:

- API health tests
- Auth tests
- Upload validation tests
- Pipeline state transition tests
- Formula engine unit tests
- Quantity traceability tests
- Report generation smoke tests
