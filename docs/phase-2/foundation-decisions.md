# Foundation Decisions

## Dependency Management

- Root JavaScript workspace uses pnpm.
- Frontend dependencies live in `frontend/package.json`.
- Backend Python dependencies live in `backend/pyproject.toml`.
- AI Python dependencies live in `ai/pyproject.toml`.
- Shared Python tooling defaults live in the root `pyproject.toml`.

## Runtime Strategy

- Local development is Docker Compose first.
- Production Kubernetes files are intentionally reserved as deployment skeletons.
- Backend and AI remain separate Python packages.
- The first backend app exposes no business API routes in Phase 2.

## Engineering Intelligence Strategy

- BitonX is an Engineering Intelligence Platform, not an OCR application.
- OCR is one perception stage in a larger deterministic engineering pipeline.
- AI and deep learning are limited to visual understanding and interpretation.
- LLMs and deep learning models must never calculate or estimate final quantities.
- Quantity takeoff must always be produced by deterministic rule and formula execution.
- Every quantity must be reproducible from source geometry, engineering rule version, formula version, inputs, intermediate values, and units.
- If perception evidence is insufficient, the pipeline must request review instead of inventing quantities.

## Observability Strategy

- Services should use structured logging foundations from the start.
- Prometheus, Grafana, Loki, and OpenTelemetry collector configuration are present as foundations.
- Metrics and traces will be connected to real application flows in later phases.

## CI Strategy

CI is configured to run:

- Python syntax compilation.
- Python linting.
- Python tests.
- Frontend linting.
- Frontend type checking.
- Frontend tests.
- Docker Compose configuration validation.

CI may require dependency installation from package registries when run outside the restricted local sandbox.
