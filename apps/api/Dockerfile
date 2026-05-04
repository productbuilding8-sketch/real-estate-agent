FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN pip install uv

COPY pyproject.toml ./
RUN uv pip install --system -e ".[prod]"

# ── development target ─────────────────────────────────────────────────────────
FROM base AS development
RUN uv pip install --system -e ".[dev]"
COPY . .
CMD ["uvicorn", "dealflow.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── production target ──────────────────────────────────────────────────────────
FROM base AS production
COPY . .
CMD ["uvicorn", "dealflow.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
