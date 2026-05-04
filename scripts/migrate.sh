#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Running Alembic migrations"
cd "$ROOT/apps/api"
uv run alembic upgrade head
echo "==> Migrations complete"
