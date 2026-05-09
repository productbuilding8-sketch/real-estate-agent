# DealFlow AI — UI Testing Guide

Reference for validating the full stack locally (FastAPI + Next.js + PostgreSQL).

---

## Prerequisites

Both services must be running before any tests.

### Start FastAPI
```bash
cd apps/api
DATABASE_URL="postgresql+asyncpg://dealflow:dealflow@localhost:5432/dealflow" DEV_MODE=true \
  uv run uvicorn dealflow.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Next.js
```bash
cd apps/web
pnpm dev
```

### Seed demo data (run once, idempotent)
```bash
cd apps/api
DATABASE_URL="postgresql://dealflow:dealflow@localhost:5432/dealflow" \
  uv run python scripts/seed_demo.py
```

Expected output:
```
Clearing existing demo data...
Seeding agents...
  4 agents seeded
Seeding leads...
  + James Whitfield (new, score=0.82)
  ...
Done! Seeded 4 agents + 15 leads.
```

---

## 1. API Health Checks

```bash
# Infrastructure
curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok","db":true,"redis":true}
```

### Auth headers for all API calls
```bash
H1="Authorization: Bearer dev-token"
H2="X-Tenant-ID: 00000000-0000-0000-0000-000000000001"
BASE="http://localhost:8000/api/v1"
```

---

## 2. API Endpoint Tests

### Leads list (verify agent names join)
```bash
curl -s -H "$H1" -H "$H2" "$BASE/leads?limit=5" | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  [print(x['contact']['full_name'], '->', x.get('assigned_agent_name')) for x in d['items']]"
```
Expected: leads with assigned agents show real names (e.g. `James Whitfield -> Sarah Chen`), not null.

### Lead detail (verify timeline + preferences)
```bash
LEAD_ID=$(curl -s -H "$H1" -H "$H2" "$BASE/leads?limit=1" | \
  python -c "import sys,json; print(json.load(sys.stdin)['items'][0]['id'])")

curl -s -H "$H1" -H "$H2" "$BASE/leads/$LEAD_ID" | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  print('timeline events:', len(d['timeline'])); \
  print('preferences:', bool(d.get('preferences'))); \
  print('contact points:', len(d['contact']['contact_points']))"
```

### Team members
```bash
curl -s -H "$H1" -H "$H2" "$BASE/team/members" | \
  python -c "import sys,json; [print(x['name'], x['role_slug']) for x in json.load(sys.stdin)]"
```
Expected: 5 members — Alex Johnson (owner_admin), Local Dev (owner_admin), Michael Torres (agent), Priya Nair (agent), Sarah Chen (manager).

### Team invitations
```bash
curl -s -H "$H1" -H "$H2" "$BASE/team/invitations"
```

### Dashboard metrics
```bash
curl -s -H "$H1" -H "$H2" "$BASE/metrics/dashboard" | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  print('total:', d['total_leads'], '| by_status:', d['by_status'])"
```
Expected: `total: 15` with breakdown across new/contacted/qualified/converted/lost.

### Invite a member (POST)
```bash
curl -s -H "$H1" -H "$H2" -H "Content-Type: application/json" \
  -X POST "$BASE/team/invitations" \
  -d '{"email":"test@example.com","role_slug":"agent"}'
```
Expected: `{"id":"...","email":"test@example.com","role_slug":"agent","expires_at":"...","accepted_at":null}`

### Assign lead
```bash
curl -s -H "$H1" -H "$H2" -H "Content-Type: application/json" \
  -X PATCH "$BASE/leads/$LEAD_ID/assign" \
  -d '{"agent_id":"30000000-0000-0000-0000-000000000001"}'
```

### Update lead status
```bash
curl -s -H "$H1" -H "$H2" -H "Content-Type: application/json" \
  -X PATCH "$BASE/leads/$LEAD_ID/status" \
  -d '{"status":"contacted"}'
```

### Add note
```bash
curl -s -H "$H1" -H "$H2" -H "Content-Type: application/json" \
  -X POST "$BASE/leads/$LEAD_ID/notes" \
  -d '{"text":"Test note from CLI"}'
```
Expected: returns a timeline event of type `lead.note_added`.

---

## 3. Page Render Tests

```bash
# Check all main pages return HTTP 200
for page in dashboard leads team settings/integrations; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000/$page")
  echo "$page: $code"
done
```
All must return `200`.

### Verify page content

**Leads page** — check lead names and agent names appear:
```bash
curl -s "http://localhost:3000/leads" | python -c "
import sys, re
content = sys.stdin.read()
names = re.findall(r'(James Whitfield|Aisha Patel|Carlos Mendez)', content)
agents = re.findall(r'(Sarah Chen|Michael Torres|Priya Nair|Alex Johnson)', content)
print('Lead names:', set(names))
print('Agent names:', set(agents))
"
```

**Team page** — check all members appear:
```bash
curl -s "http://localhost:3000/team" | python -c "
import sys, re
content = sys.stdin.read()
names = re.findall(r'(Sarah Chen|Michael Torres|Priya Nair|Alex Johnson)', content)
print('Members found:', set(names))
if 'Application error' in content: print('ERROR: App error present')
"
```

**Dashboard page** — check metrics render:
```bash
curl -s "http://localhost:3000/dashboard" | python -c "
import sys
content = sys.stdin.read()
print('Has pipeline:', 'Pipeline' in content)
print('Has total leads:', 'Total Leads' in content or '15' in content)
print('Has error:', 'Application error' in content)
"
```

---

## 4. TypeScript Type Check

```bash
cd apps/web && npx tsc --noEmit
```
Expected: **no output** (zero errors).

---

## 5. OpenAPI Schema Validation

Verify new fields appear in the generated schema:

```bash
# Check assigned_agent_name added to LeadListItem
curl -s http://localhost:8000/openapi.json | \
  python -c "import sys,json; d=json.load(sys.stdin); \
  props=d['components']['schemas']['LeadListItem']['properties']; \
  print('assigned_agent_name' in props)"
# Expected: True
```

---

## 6. Manual UI Flows to Verify

| Feature | Steps | Expected |
|---------|-------|----------|
| Lead list | Visit `/leads` | 15 leads visible, agent names shown where assigned |
| Lead filters | Click status tabs (New, Contacted, etc.) | List filters correctly |
| Lead search | Type name in search box | Debounced filter updates list |
| Lead detail | Click any lead row | Detail page opens with contact, preferences, timeline |
| Lead status change | On detail page, click status dropdown | Status updates, timeline event added |
| Assign lead | On detail page, click agent dropdown | Agent assigned, persisted on refresh |
| Add note | On detail page, type note and submit | Note appears at top of timeline |
| Team page | Visit `/team` | 5 members listed with roles and join dates |
| Invite member | Click "Invite member", fill email + role | Invitation appears in pending list |
| Revoke invitation | Click X on pending invitation | Invitation removed |
| Change role | Click ⋯ → Change role on member row | Role updated immediately |
| Remove member | Click ⋯ → Remove member | Member removed (cannot remove self) |
| Dashboard | Visit `/dashboard` | Shows 15 total leads, pipeline breakdown, recent activity |
| Integrations | Visit `/settings/integrations` | HubSpot card shown (disconnected state) |

---

## 7. Common Failure Modes & Fixes

### Team page returns 500
**Cause:** Next.js webpack chunk staleness after file edits.
**Fix:** Stop dev server → delete `.next/cache` → restart.
```bash
rm -rf apps/web/.next/cache && cd apps/web && pnpm dev
```

### API returns stale data after code change
**Cause:** Uvicorn `--reload` sometimes misses file changes on Windows.
**Fix:** Kill all Python processes and restart.
```bash
# Find uvicorn PID
netstat -ano | grep ":8000 "
# Kill it (PowerShell)
Stop-Process -Id <PID> -Force
# Restart
cd apps/api && DATABASE_URL="postgresql+asyncpg://..." DEV_MODE=true uv run uvicorn dealflow.main:app --reload --host 0.0.0.0 --port 8000
```

### Seed script fails with "expected str, got list"
**Cause:** JSONB columns (e.g. `property_types`) need JSON-encoded strings for asyncpg.
**Fix:** Wrap lists/dicts with `json.dumps()` before passing to `db.execute()`.

### Seed script fails with UnicodeEncodeError on Windows
**Cause:** Windows cp1252 terminal can't encode unicode characters like `✓`.
**Fix:** Use ASCII alternatives in print statements (`+` instead of `✓`).

### `from __future__ import annotations` + Pydantic TypeAdapter error
**Cause:** Deferred string annotations from `__future__` conflict with Pydantic's TypeAdapter, compounded by `.pyc` bytecode caching.
**Fix:**
1. Remove `from __future__ import annotations` from the affected file.
2. Clear bytecode cache: `find apps/api -name "*.pyc" -delete`
3. Restart uvicorn.

### `assigned_agent_name` always null
**Cause:** The leads service `outerjoin(User, ...)` SQL change wasn't picked up (server didn't reload).
**Fix:** Verify OpenAPI schema: `curl -s http://localhost:8000/openapi.json | python -c "import sys,json; d=json.load(sys.stdin); print('assigned_agent_name' in d['components']['schemas']['LeadListItem']['properties'])"` — if False, restart the API.

---

## 8. Event Types Reference

The seed script creates these timeline event types. The frontend must handle all of them:

| Event type | Icon | Key data fields |
|------------|------|----------------|
| `lead.created` | UserPlus (blue) | `source` |
| `lead.scored` | Sparkles (purple) | `score`, `tier`, `method` |
| `lead.assigned` | UserCheck (indigo) | `agent_name` |
| `lead.status_changed` | RefreshCw (amber) | `from`, `to` |
| `note.added` | StickyNote (yellow) | `text` |
| `sms.sent` | MessageSquare (emerald) | `preview` |
| `lead.note_added` | StickyNote (yellow) | `text` |

---

## 9. Seed Data Reference

**4 Agents:**
- Sarah Chen — `30000000-0000-0000-0000-000000000001` — manager
- Michael Torres — `30000000-0000-0000-0000-000000000002` — agent
- Priya Nair — `30000000-0000-0000-0000-000000000003` — agent
- Alex Johnson — `30000000-0000-0000-0000-000000000004` — owner_admin

**Dev user (migration-seeded, not from seed script):**
- Local Dev — `20000000-0000-0000-0000-000000000001` — owner_admin

**15 Leads across statuses:**
- new: James Whitfield, David Kim, Omar Hassan, Ben Carlisle, Mei Zhang
- contacted: Aisha Patel, Rachel Goldstein, Fatima Al-Rashid
- qualified: Carlos Mendez, Emily Nakamura, Natalia Rivera
- converted: Sophie Laurent, Tyler Brooks
- lost: Marcus Thompson, Jordan Mitchell

**Tenant ID:** `00000000-0000-0000-0000-000000000001`
