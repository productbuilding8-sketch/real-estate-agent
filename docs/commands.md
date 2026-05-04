# DealFlow AI — Developer Command Reference

## Setup

```powershell
# First-time setup (copies .env files, installs deps)
bash scripts/setup.sh

# Add uv to current PowerShell session (if not in PATH)
$env:Path = "C:\Users\yash1\.local\bin;$env:Path"
```

---

## Docker

```powershell
# Start Postgres + Redis only (for local dev / testing)
docker compose -f infra/docker-compose.yml up -d postgres redis

# Start all services (api, worker, web, postgres, redis)
docker compose -f infra/docker-compose.yml up -d

# Stop all containers
docker compose -f infra/docker-compose.yml stop

# Stop and remove containers + volumes (full reset)
docker compose -f infra/docker-compose.yml down -v

# Check container status and health
docker compose -f infra/docker-compose.yml ps

# View logs
docker compose -f infra/docker-compose.yml logs -f postgres
docker compose -f infra/docker-compose.yml logs -f api

# Restart a single service
docker compose -f infra/docker-compose.yml restart api
```

---

## Database

```powershell
# Create test database (first time)
docker compose -f infra/docker-compose.yml exec postgres psql -U dealflow -c "CREATE DATABASE dealflow_test;"

# Run migrations (apply all pending)
bash scripts/migrate.sh

# Drop and recreate dev DB (destructive — prompts confirmation)
bash scripts/reset-db.sh

# Open Postgres shell
docker compose -f infra/docker-compose.yml exec postgres psql -U dealflow -d dealflow

# Open Postgres shell for test DB
docker compose -f infra/docker-compose.yml exec postgres psql -U dealflow -d dealflow_test

# Alembic commands (run from apps/api)
cd apps/api
uv run alembic upgrade head          # Apply all migrations
uv run alembic downgrade -1          # Roll back one migration
uv run alembic revision --autogenerate -m "description"  # Generate new migration
uv run alembic current               # Show current revision
uv run alembic history               # Show migration history
uv run alembic check                 # Fail if unapplied migrations exist
```

---

## API (FastAPI)

```powershell
# Install dependencies
cd apps/api
uv venv --python 3.12        # Create venv (first time only)
uv pip install -e ".[dev]"   # Install all deps

# Activate venv (PowerShell)
.venv\Scripts\activate.ps1

# Run dev server (hot reload)
uvicorn dealflow.main:app --reload --port 8000

# Run dev server without activating venv
uv run uvicorn dealflow.main:app --reload --port 8000
```

**API URLs (local):**
- Swagger UI: http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc
- Health:      http://localhost:8000/api/v1/health
- Version:     http://localhost:8000/api/v1/version

---

## Tests (API)

```powershell
cd apps/api

# Run all tests (requires Docker postgres + redis)
python -m pytest tests/ -v

# Run unit tests only (no Docker needed)
python -m pytest -m "not integration" -v

# Run integration tests only (requires Docker)
python -m pytest -m integration -v

# Run with coverage report
python -m pytest --cov=src/dealflow --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_health.py -v

# Run a specific test by name
python -m pytest tests/test_health.py::test_version_returns_fields -v
```

---

## Linting & Type Checking (API)

```powershell
cd apps/api

# Lint
uv run ruff check src

# Lint + auto-fix
uv run ruff check src --fix

# Format check
uv run ruff format --check src

# Auto-format
uv run ruff format src

# Type check
uv run mypy src
```

---

## Web (Next.js)

```powershell
# Install dependencies (first time)
cd apps/web
pnpm install

# Run dev server (hot reload)
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Type check
pnpm typecheck

# Lint
pnpm lint

# Run tests
pnpm test

# Run tests in watch mode
pnpm test:watch
```

**Web URLs (local):**
- App: http://localhost:3000

---

## Shared Package

```powershell
cd packages/shared

# Install deps
pnpm install

# Build (compile TypeScript)
pnpm build

# Type check
pnpm typecheck
```

---

## uv (Python package manager)

```powershell
# Install Python version
uv python install 3.12

# Create virtual environment
uv venv --python 3.12

# Install package
uv pip install <package>

# Install project in editable mode with dev deps
uv pip install -e ".[dev]"

# Run a command in the venv without activating
uv run <command>

# Check uv version
uv --version
```

---

## Git

```powershell
# Check status
git status

# Stage and commit
git add <files>
git commit -m "message"

# Push current branch
git push origin HEAD

# Create and switch to new branch
git checkout -b feature/dai-010-auth
```

---

## CI (GitHub Actions)

The CI pipeline runs automatically on push/PR to `main`. Jobs:

| Job | What it checks |
|---|---|
| `lint-api` | ruff lint + format |
| `typecheck-api` | mypy strict |
| `test-api` | pytest with real postgres + redis |
| `migration-check` | alembic upgrade head + alembic check |
| `lint-web` | eslint + tsc --noEmit |
| `test-web` | vitest |
| `build-web` | next build |

To run CI checks locally before pushing:
```powershell
# API full check
cd apps/api
uv run ruff check src && uv run ruff format --check src && uv run mypy src && python -m pytest -v

# Web full check
cd apps/web
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```
