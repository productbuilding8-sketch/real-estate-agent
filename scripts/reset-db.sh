#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "WARNING: This will drop and recreate the local development database."
read -r -p "Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

echo "==> Dropping database"
docker compose -f "$ROOT/infra/docker-compose.yml" exec postgres \
  psql -U dealflow -c "DROP DATABASE IF EXISTS dealflow WITH (FORCE);"

echo "==> Recreating database"
docker compose -f "$ROOT/infra/docker-compose.yml" exec postgres \
  psql -U dealflow -c "CREATE DATABASE dealflow;"

echo "==> Running init SQL"
docker compose -f "$ROOT/infra/docker-compose.yml" exec postgres \
  psql -U dealflow -d dealflow -f /docker-entrypoint-initdb.d/init.sql

echo "==> Running migrations"
bash "$ROOT/scripts/migrate.sh"

echo "==> Database reset complete"
