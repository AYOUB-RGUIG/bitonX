# BitonX Phase 2

Phase 2 creates the production foundation for later implementation.

## Objectives

1. Create the complete production repository structure.
2. Generate the development environment.
3. Configure dependency management.
4. Configure Docker and Docker Compose.
5. Configure environment files.
6. Configure CI/CD.
7. Configure linting, formatting, and testing tools.
8. Configure logging and monitoring foundations.
9. Create backend, frontend, and AI project skeletons only.

## Explicit Non-Goals

- No business logic.
- No AI models.
- No REST API implementation.
- No quantity formulas.
- No persistence models beyond package and migration scaffolding.

## Foundation Validation

Phase 2 can be checked without installing external dependencies by running:

```powershell
python -m compileall backend ai
node --check frontend/next.config.mjs
node --check frontend/eslint.config.mjs
```

Full build validation requires installing dependencies:

```powershell
pnpm install
python -m pip install -e "backend[dev]"
python -m pip install -e "ai[dev]"
pnpm lint
pnpm test
python -m pytest
docker compose config
```
