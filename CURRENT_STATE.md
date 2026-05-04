# DealFlow AI — Current State

> **For AI assistants:** Read this file first. It replaces guessing from the file tree.
> Last updated: 2026-05-03

---

## What This Project Is

**DealFlow AI** is a multi-tenant SaaS platform for real estate lead management. It ingests leads from multiple channels (webhooks, HubSpot, email, CSV), qualifies them with AI (Claude), routes them to agents, manages messaging (SMS/WhatsApp/email via Twilio), syncs to CRMs, and surfaces an activity timeline per lead.

**Monorepo layout:**

```
apps/
  api/        ← FastAPI backend (Python 3.12) — ACTIVE DEVELOPMENT
  web/        ← Next.js 15 frontend — APP SHELL DONE, Auth0 integrated
  worker/     ← ARQ async worker — NOT YET STARTED
packages/
  shared/     ← Shared DTOs/types — NOT YET STARTED
infra/
  docker-compose.yml    ← Local dev environment
  docker-compose.override.yml
docs/
  er-diagram.md         ← V2 schema reference (authoritative)
```

---

## What Is Built (Completed)

### apps/api — FastAPI backend

**Framework & Config**
- `src/dealflow/main.py` — `create_app(settings?)` factory; CORS; lifespan (DB init/teardown); Swagger at `/docs` (non-prod only)
- `src/dealflow/config.py` — `Settings` via pydantic-settings; `get_settings()` is `lru_cache`'d but **routes use `request.app.state.settings`** (not `get_settings()`) for testability
- `src/dealflow/core/errors.py` — Global error handlers; all errors return `{"error": {"code": str, "message": str, "details": any}}`

**Auth (Auth0 RS256 JWT)**
- `src/dealflow/core/auth.py` — `decode_jwt()`, `_JwksCache` (1h TTL), key rotation via `force` refresh on unknown `kid`, `TokenPayload` Pydantic model
- `src/dealflow/core/dependencies.py` — `get_current_user(request, credentials)` FastAPI dependency; reads domain/audience from `request.app.state.settings`

**API Routes** (`/api/v1/`)
| Route | File | Status |
|---|---|---|
| `GET /health` | `routes/health.py` | ✅ Done |
| `GET /version` | `routes/health.py` | ✅ Done |
| `GET /auth/me` | `routes/auth.py` | ✅ Done |

**RBAC Middleware** (DAI-012)
- `src/dealflow/core/rbac.py` — `RequestContext` (frozen dataclass), `check_permission()` (fnmatch glob), `resolve_context()` (User+TenantMembership+Role DB lookup), `_ROLE_CACHE` (dict, cleared in tests via `clear_role_cache()`)
- `src/dealflow/core/dependencies.py` — `get_tenant_id()` (parses `X-Tenant-ID` header), `get_tenant_context()` (JWT+tenant→RequestContext), `require_permission("perm:action")` (factory returning FastAPI dependency)

**Repository Layer**
- `src/dealflow/db/repositories/base.py` — `TenantRepository[T]`: `get()`, `list(*filters, limit, cursor)`, `add()`, `delete()`, `exists()`; enforces `tenant_id` on every query; validates model has `tenant_id` at init time

**Audit Service** (DAI-058)
- `src/dealflow/services/audit.py` — `AuditService(session, tenant_id)`: `log(action, entity_type, entity_id, before, after, actor_id, actor_type, ip_address)` → `AuditLog`; `add_timeline_event(lead_id, event_type, event_data, ...)` → `ActivityTimeline`; all writes share the caller's session (commit/rollback together)

**Database Layer**
- `src/dealflow/db/session.py` — `Base`, `init_db()`, `get_session()`, `NullPool` for tests
- `src/dealflow/db/models/` — 8 model files (see schema section below)
- `migrations/env.py` — Async Alembic with `asyncio.run(run_async_migrations())`

**V2 Database Schema — FULLY APPLIED** (`alembic upgrade head` → revision `e5f6a7b8c9d0`)

| Migration | Revision | Tables |
|---|---|---|
| 0001_tenant_user_roles | `9f3c8d2e1a4b` | tenants, users, roles, tenant_memberships, agent_profiles, tenant_invitations |
| 0002_lead_ingestion | `a1b2c3d4e5f6` | lead_sources, ingestion_events, contacts, contact_points, leads, lead_preferences, lead_scores, lead_next_actions, dedupe_candidates, contact_merge_events |
| 0003_conversations | `b2c3d4e5f6a7` | conversations, messages, message_delivery_attempts |
| 0004_ai_operations | `c3d4e5f6a7b8` | prompt_versions, ai_actions, human_approvals, lead_assignments, tasks, appointments |
| 0005_integrations_sla_workflow | `d4e5f6a7b8c9` | integration_connections, crm_mappings, sync_logs, tenant_sla_settings, lead_sla_results, messaging_policy_settings, consent_records, opt_out_records, outbox_events |
| 0006_audit_knowledge | `e5f6a7b8c9d0` | audit_logs, activity_timeline, knowledge_documents, knowledge_chunks (+ pgvector extension + HNSW index) |

**Tests** — 57/57 unit tests pass (`pytest -k "not integration"`)

| File | What it covers |
|---|---|
| `tests/conftest.py` | `client` (no DB), `db_setup`/`db_session` (real Postgres), `db_client` (HTTP+DB) |
| `tests/test_health.py` | `/health`, `/version` routes |
| `tests/test_auth.py` | `decode_jwt()` unit tests + `/auth/me` route with mocked JWKS |
| `tests/test_tenant_schema.py` | ORM metadata assertions (unit) + tenant/user/role integration tests |
| `tests/test_rbac.py` | `check_permission()`, `RequestContext`, dependency unit tests, mocked `resolve_context`, integration tests |
| `tests/test_repository_base.py` | `TenantRepository` constructor guard, get/list/add/delete/exists with mocked session, cross-tenant isolation integration test |
| `tests/test_audit_service.py` | `AuditService.log()` and `add_timeline_event()` — all fields, defaults, PII flag, integration persistence |
| `tests/helpers/jwt_factory.py` | RSA key generation, JWKS builder, `make_token()` for tests |

---

---

## apps/web — Next.js 15 Frontend

**Stack:** Next.js 15.1 (App Router) · React 19 · TypeScript strict · Tailwind CSS · `@auth0/nextjs-auth0` v3.5 · Vitest

**Build:** `npm run build` passes clean (standalone output)

### File Tree (DAI-009, DAI-013 complete)

```
src/
  app/
    layout.tsx                    ← root layout, Auth0 UserProvider
    page.tsx                      ← redirects to /dashboard or /login based on session
    globals.css                   ← Tailwind base styles
    api/auth/[auth0]/route.ts     ← Auth0 handler (login/logout/callback/me)
    (auth)/login/page.tsx         ← branded login page → /api/auth/login
    (authenticated)/
      layout.tsx                  ← protected shell: Sidebar + TopNav
      dashboard/page.tsx          ← dashboard stub with welcome + stat cards
  components/layout/
    sidebar.tsx                   ← dark sidebar, nav with active state, disabled "soon" items
    top-nav.tsx                   ← top bar with page title + UserMenu
    user-menu.tsx                 ← avatar, name, dropdown, logout link
  lib/cn.ts                       ← clsx + tailwind-merge helper
  middleware.ts                   ← withMiddlewareAuthRequired() protects all non-public routes
```

### Auth Flow
1. Any protected route → middleware redirects to `/api/auth/login` if no session
2. Auth0 handles OAuth → redirects back to `/api/auth/callback`
3. Session stored via cookie; `getSession()` in server components, `useUser()` in client components
4. Logout at `/api/auth/logout`

### How to Run (apps/web)
```powershell
Set-Location apps\web
# Set .env.local with AUTH0_SECRET, AUTH0_BASE_URL, AUTH0_ISSUER_BASE_URL, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET
npm run dev    # http://localhost:3000
npm run build  # production build (standalone)
npm run typecheck
```

### Required Environment Variables (apps/web/.env.local)
```ini
AUTH0_SECRET=<32-byte random string — openssl rand -hex 32>
AUTH0_BASE_URL=http://localhost:3000
AUTH0_ISSUER_BASE_URL=https://your-tenant.auth0.com
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
AUTH0_AUDIENCE=https://api.dealflow.com
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## What Is NOT Built Yet

### API routes not yet implemented
- `POST /api/v1/webhooks/leads/{source_key}` — Lead ingestion endpoint (DAI-020)
- `GET/POST /api/v1/leads` — Lead list and creation (DAI-021)
- `GET /api/v1/leads/{id}` — Lead detail (DAI-022)
- `POST /api/v1/leads/{id}/conversations/messages` — Send message (DAI-030)
- `GET /api/v1/leads/{id}/timeline` — Activity timeline (DAI-040)
- `POST /api/v1/tenants/invitations` — Invite user (DAI-015)
- `GET /api/v1/users/me/tenants` — Tenant switcher (DAI-016)
- Any CRUD for tasks, appointments, agent_profiles, integrations

### Service / repository layer
- No repository base class yet (tenant_id filtering not enforced in code, only by convention)
- No service layer classes yet (business logic lives nowhere — needs to be built)

### Worker (apps/worker)
- ARQ worker not started — no job definitions, no queue consumers
- Planned jobs: stale-lead scan, SLA computation, outbox event dispatcher, dedup worker, AI action runner, sync retry worker, PII scrubbing worker

### Frontend (apps/web)
- Next.js app not started

### Integrations not wired
- Auth0 tenant creation on onboarding (user creation flow)
- Twilio webhook receiver
- HubSpot sync
- Google/MS Calendar booking

---

## Key Architecture Decisions (do not reverse without understanding why)

| Decision | Rule | Why |
|---|---|---|
| **Global users** | `users` has no `tenant_id`; `tenant_memberships` is the join | One Auth0 identity can join multiple brokerages |
| **No unique on phone/email** | `contact_points` has no unique constraint on `value_normalized` | Spouses, assistants, and recycled numbers share identifiers |
| **Idempotency everywhere** | `ingestion_events`, `sync_logs` both have idempotency_key unique constraints | Twilio/HubSpot retry delivers events twice |
| **Transactional outbox** | `outbox_events` written in same DB tx as business record | Redis unavailability must not lose jobs |
| **Per-agent calendar** | `integration_connections.agent_id` nullable FK | Each agent has their own Google/MS Calendar |
| **Deferred FKs in migrations** | `messages.ai_action_id`, `leads.ingestion_event_id`, `agent_profiles.default_calendar_connection_id` added via `ALTER TABLE` in later migrations | Forward reference between domains |
| **PII scrubbing** | `audit_logs.pii_fields_scrubbed = false` on insert; worker scrubs within 1h | Raw before/after state must not persist PII indefinitely |
| **settings via request.app.state** | All routes/dependencies read `request.app.state.settings`, never `get_settings()` | `lru_cache` singleton breaks test settings injection |
| **Error format** | `{"error": {"code": str, "message": str, "details": any}}` always | Consistent client parsing |

---

## How to Run Locally

```powershell
# 1. Start services (requires Docker Desktop)
Set-Location infra
docker compose up -d postgres redis

# 2. Run migrations
$env:DATABASE_URL = "postgresql+asyncpg://dealflow:dealflow@localhost:5432/dealflow"
Set-Location ..\apps\api
C:\Users\yash1\.local\bin\uv.exe run alembic upgrade head

# 3. Start API (reads from apps/api/.env)
C:\Users\yash1\.local\bin\uv.exe run uvicorn dealflow.main:app --reload --port 8000

# 4. Run tests
C:\Users\yash1\.local\bin\uv.exe run pytest -k "not integration" -q
```

> **`uv` path:** `C:\Users\yash1\.local\bin\uv.exe` (not on system PATH)
> **Postgres image:** Must be `pgvector/pgvector:pg16` (in `infra/docker-compose.yml`) — standard `postgres:16-alpine` does NOT have the vector extension

---

## Environment Variables (apps/api/.env)

```ini
DATABASE_URL=postgresql+asyncpg://dealflow:dealflow@postgres:5432/dealflow
REDIS_URL=redis://redis:6379/0
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=https://api.dealflow.com
SECRET_KEY=...
```

> When running migrations from **host** (not inside Docker), override host:
> `$env:DATABASE_URL = "postgresql+asyncpg://dealflow:dealflow@localhost:5432/dealflow"`

---

## Dependency Management

| Tool | Command |
|---|---|
| Install / sync | `C:\Users\yash1\.local\bin\uv.exe sync --all-extras` |
| Add package | `C:\Users\yash1\.local\bin\uv.exe add <pkg>` |
| Run anything | `C:\Users\yash1\.local\bin\uv.exe run <cmd>` |

The `.venv` is at `apps/api/.venv`. **Do not use system Python or pip directly.**

---

## Database Schema Quick Reference

**38 tables total.** Full ER diagram: [`docs/er-diagram.md`](docs/er-diagram.md)

```
DOMAIN 1 — TENANT/AUTH (6 tables)
  tenants                  id, name, slug, timezone, is_active, settings
  users                    id, auth0_sub (UK), email, name — GLOBAL (no tenant_id)
  tenant_memberships       user_id FK, tenant_id FK, role_slug, expires_at — UNIQUE(user+tenant)
  roles                    id, name UK, slug UK, permissions — 5 seeded rows, never written at runtime
  agent_profiles           user_id FK, tenant_id FK, max_leads, is_available, default_calendar_connection_id
  tenant_invitations       tenant_id FK, email, role_slug, token UK (64-char), expires_at (72h)

DOMAIN 2 — LEAD INGESTION (10 tables)
  lead_sources             tenant_id, source_key UK, secret_hash (HMAC), type, config
  ingestion_events         tenant_id+source_id+idempotency_key UK, status, lead_id FK (nullable)
  contacts                 tenant_id, first_name, last_name, is_merged, merged_into_id (self-FK)
  contact_points           contact_id FK, type [email|phone|whatsapp|imessage|rcs], value_normalized
  leads                    tenant_id, contact_id FK, source_id FK, status, assigned_agent_id FK
  lead_preferences         lead_id FK (1:1), budget, location, property_types, financing_status
  lead_scores              lead_id FK, score, scoring_model, factors JSONB — append-only history
  lead_next_actions        lead_id FK, action_type, priority, status, crm_task_id
  dedupe_candidates        contact_a_id FK + contact_b_id FK, match_score, status [pending|merged|dismissed]
  contact_merge_events     winner_id FK, loser_id FK, merge_reason, field_decisions JSONB — immutable

DOMAIN 3 — CONVERSATIONS (3 tables)
  conversations            lead_id FK, contact_id FK, channel — UNIQUE(lead+contact+channel)
  messages                 conversation_id FK, direction, body, is_ai_generated, ai_action_id FK (deferred)
  message_delivery_attempts message_id FK, provider, provider_message_id, status — one row per send attempt

DOMAIN 4 — AI (3 tables)
  prompt_versions          name+version UK, template, input/output_schema, is_active
  ai_actions               lead_id FK, action_type, model, input_ref (pointer), output_json, safety_decision
  human_approvals          ai_action_id FK, draft_content, status [pending|approved|edited|rejected|expired]

DOMAIN 5 — OPERATIONS (3 tables)
  lead_assignments         lead_id FK, agent_id FK, assigned_at, unassigned_at (NULL=active)
  tasks                    lead_id FK, assigned_to_id FK, task_type, status, priority, due_at
  appointments             lead_id FK, agent_id FK, calendar_provider, calendar_event_id, scheduled_at

DOMAIN 6 — INTEGRATIONS (3 tables)
  integration_connections  tenant_id FK, agent_id FK (nullable for per-agent calendar), provider, credentials_enc
  crm_mappings             connection_id FK, dealflow_field, crm_field, crm_object, idempotency_key_field
  sync_logs                connection_id+idempotency_key UK, operation, crm_record_id, retry_count

DOMAIN 7 — SLA/CONSENT (5 tables)
  tenant_sla_settings      tenant_id FK (1:1), first_response_min, stale_lead_hrs, escalation_hrs
  lead_sla_results         lead_id FK (1:1), first_response_met, is_stale, is_escalated
  messaging_policy_settings tenant_id FK (1:1), sms_enabled, auto_send_sms, etc.
  consent_records          contact_id FK, channel — UNIQUE(contact+channel)
  opt_out_records          contact_id FK, channel, message_id FK, opted_out_at, reinstated_at

DOMAIN 8 — WORKFLOW (1 table)
  outbox_events            aggregate_type, aggregate_id, event_type, payload, status, attempts

DOMAIN 9 — AUDIT/TIMELINE (2 tables)
  audit_logs               entity_type, entity_id, before_state JSONB, after_state JSONB, pii_fields_scrubbed
  activity_timeline        lead_id FK, event_type, event_data JSONB, visible_to_agent

DOMAIN 10 — KNOWLEDGE BASE (2 tables)
  knowledge_documents      tenant_id FK, filename, status [processing|active|failed|archived]
  knowledge_chunks         document_id FK, content, embedding vector(1536) — HNSW cosine index
```

**Seeded roles** (in migration 0001, never modified at runtime):
- `owner_admin` — full control
- `manager` — approvals, reassignment, reports
- `agent` — assigned leads, conversations, tasks
- `implementation_admin` — integrations, sources, raw payload access
- `auditor` — read-only audit logs and reports

---

## Known Issues / Gotchas

1. ~~**`conftest.py` `db_client` fixture** returns `AsyncClient`, but `test_tenant_schema.py` types it as `AsyncSession`.~~ **Fixed** — `db_session: AsyncSession` fixture added to `conftest.py`; all integration tests updated to use it.

2. **`lru_cache` settings singleton** — `get_settings()` must NOT be called in route handlers or dependencies. Always use `request.app.state.settings`. This bug was fixed in `routes/health.py` and `core/dependencies.py` but could re-appear in new routes.

3. **`uv` not on system PATH** — must invoke as `C:\Users\yash1\.local\bin\uv.exe`. Add to PATH or alias.

4. **Postgres must be `pgvector/pgvector:pg16`** — not standard `postgres:16`. Migration 0006 calls `CREATE EXTENSION vector`.

5. **`IngestionEvent.lead_id` FK is deferred** — `leads.ingestion_event_id` FK to `ingestion_events` is also deferred (circular). Both are added via `ALTER TABLE` in migration 0002 after both tables exist.

---

## Next Logical Tasks (by priority)

1. **Lead ingestion endpoint** — `POST /api/v1/webhooks/leads/{source_key}`: validate HMAC → write `ingestion_event` → upsert `contact`+`contact_points` → create `lead` → write `outbox_event` → call `AuditService.log()`. All in one transaction. Uses `TenantRepository`.
2. **User registration flow** — On first Auth0 login: upsert `users`, create `tenant_memberships` row, create `agent_profiles` if role = agent.
3. **Outbox worker** — ARQ job that polls `outbox_events WHERE status = 'pending'` and dispatches to sub-jobs.
4. **Lead list API** — `GET /api/v1/leads?status=&assigned_to_me=` with tenant isolation, cursor pagination via `TenantRepository.list()`.
5. **CI pipeline** — `.github/workflows/ci.yml`: lint (ruff), typecheck (mypy), test (pytest), migration check (alembic check).
