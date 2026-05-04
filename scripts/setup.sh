#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> DealFlow AI — local setup"

# Copy env examples if .env files don't exist
copy_env() {
  local src="$1" dst="$2"
  if [[ ! -f "$dst" ]]; then
    cp "$src" "$dst"
    echo "  created $dst (fill in values before running)"
  else
    echo "  $dst already exists — skipped"
  fi
}

copy_env "$ROOT/.env.example"            "$ROOT/.env"
copy_env "$ROOT/apps/api/.env.example"   "$ROOT/apps/api/.env"
copy_env "$ROOT/apps/web/.env.example"   "$ROOT/apps/web/.env.local"
copy_env "$ROOT/apps/worker/.env.example" "$ROOT/apps/worker/.env"

# Check required tools
check_tool() {
  command -v "$1" &>/dev/null || { echo "  ERROR: $1 not found — install it first"; exit 1; }
}

echo "==> Checking required tools"
check_tool docker
check_tool pnpm
check_tool uv

echo "==> Installing JS dependencies"
cd "$ROOT" && pnpm install

echo "==> Installing Python dependencies (api)"
cd "$ROOT/apps/api" && uv pip install -e ".[dev]"

echo "==> Installing Python dependencies (worker)"
cd "$ROOT/apps/worker" && uv pip install -e ".[dev]"

echo ""
echo "Setup complete."
echo "Next steps:"
echo "  1. Fill in .env files with real values (Auth0, etc.)"
echo "  2. Run: docker compose -f infra/docker-compose.yml up -d postgres redis"
echo "  3. Run: bash scripts/migrate.sh"
echo "  4. Run: docker compose -f infra/docker-compose.yml up"
