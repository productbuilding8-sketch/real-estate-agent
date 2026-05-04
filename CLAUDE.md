# DealFlow AI

## Stack

- Next.js
- FastAPI
- PostgreSQL
- Redis
- Auth0
- HubSpot
- Twilio

## Architecture

- apps/web = frontend
- apps/api = backend
- apps/worker = async jobs
- packages/shared = shared DTOs/types

## Rules

- Use production-grade structure
- Multi-tenant isolation mandatory
- Async-first backend
- Use typed APIs
- Prefer service-layer architecture
- Avoid tight coupling
- Use Docker Compose locally

## Definition of Done

- Tests pass
- Lint passes
- Types validated
- Docker environment runs
- API documented

## Execution Strategy

Claude must:

1. Read docs before coding
2. Propose architecture before implementation
3. Implement incrementally
4. Update docs after changes
