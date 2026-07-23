# bitonX
BitonX - AI Powered Construction Quantity Takeoff Platform

## Current Phase

Phase 3 is active: shared contracts for the Engineering Intelligence pipeline.

Phase 1 control documents are available in `docs/phase-1/`.
Phase 2 foundation notes are available in `docs/phase-2/`.
Phase 3 contract notes are available in `docs/phase-3/`.

## Foundation Commands

The repository is configured as a multi-project workspace:

- Backend: Python 3.12, FastAPI skeleton, SQLAlchemy/Alembic foundations.
- AI: Python 3.12 package skeleton for preprocessing, OCR, detection, segmentation, geometry, graph, quantity, cost, and evaluation modules.
- Frontend: Next.js 15, React 19, TypeScript skeleton.
- Infrastructure: Docker Compose with PostgreSQL, Neo4j, Redis, RabbitMQ, MinIO, Nginx, Prometheus, Grafana, Loki, and OpenTelemetry collector foundations.

Install dependencies before running build or test commands.

```powershell
pnpm install
python -m pip install -e "backend[dev]"
python -m pip install -e "ai[dev]"
```

Useful commands:

```powershell
pnpm lint
pnpm test
python -m compileall backend ai
python scripts/validate-contracts.py
```
