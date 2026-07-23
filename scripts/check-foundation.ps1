$ErrorActionPreference = "Stop"

Write-Host "Checking BitonX Phase 2 foundation..."

python -m compileall backend ai
node --check frontend/next.config.mjs
node --check frontend/postcss.config.mjs
node --check frontend/eslint.config.mjs
python scripts/validate-contracts.py

Write-Host "Foundation syntax checks completed."
