# Repository Structure

The Phase 2 structure follows the approved Phase 1 architecture baseline.

```text
bitonX/
  ai/
    bitonx_ai/
    tests/
    pyproject.toml
    Dockerfile
  backend/
    app/
    tests/
    pyproject.toml
    alembic.ini
    Dockerfile
  datasets/
    raw/
    processed/
    annotations/
    metadata/
    reports/
    train/
    validation/
    test/
    masks/
    polygons/
    embeddings/
    statistics/
    cache/
    exports/
  deployment/
    helm/
    kubernetes/
  docs/
    phase-1/
    phase-2/
  frontend/
    app/
    components/
    features/
    hooks/
    services/
    store/
    types/
    styles/
    assets/
    public/
    tests/
  infrastructure/
    monitoring/
    nginx/
    otel/
    postgres/
    rabbitmq/
  monitoring/
  scripts/
  shared/
  tests/
```

Empty implementation areas are tracked with `.gitkeep` or package `__init__.py` files.

