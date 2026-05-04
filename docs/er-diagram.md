# DealFlow AI — V2 Entity Relationship Diagram

> **Revision:** V2 (addresses 10 real-world production gaps identified in V1)
> **Total tables:** 41 (P0 MVP)

---

## What Changed from V1 and Why

| V1 Flaw | Production Use Case | V2 Fix |
|---|---|---|
| `users.tenant_id` hard FK | Same Auth0 user joins 2+ brokerages | Global `users` + `tenant_memberships` junction |
| No webhook dedup | Twilio/HubSpot fires event twice | `ingestion_events` with idempotency key |
| `contacts.email` + `contacts.phone` columns | Website, HubSpot, email, WhatsApp = same person | `contact_points` child table (one row per identifier) |
| Unique constraint on phone/email | Spouses share a number; recycled phone lines | Removed unique constraints; soft dedup via `dedupe_candidates` |
| No CRM idempotency key | HubSpot sync retry creates duplicate objects | `sync_logs.idempotency_key` per CRM object type |
| Calendar only at tenant level | Each agent has their own Google/MS Calendar | `integration_connections.agent_id` nullable FK |
| No AI score/action history | Need CRM writeback + trend chart | `lead_scores` + `lead_next_actions` tables |
| `messages.provider_message_id` single value | Retry creates new Twilio SID | `message_delivery_attempts` child table |
| No transactional outbox | Lead created but job never enqueued | `outbox_events` table (publish-on-commit) |
| `audit_logs.before_state` raw JSONB | PII leaks into audit snapshots | `pii_fields_scrubbed` flag + scrubbing worker |

---

## Domain Areas

| # | Domain | Tables | Count |
|---|---|---|---|
| 1 | Tenant / Auth | tenants, users, tenant_memberships, roles, agent_profiles, tenant_invitations | 6 |
| 2 | Lead Ingestion | lead_sources, ingestion_events, contacts, contact_points, leads, lead_preferences, lead_scores, lead_next_actions, dedupe_candidates, contact_merge_events | 10 |
| 3 | Conversations | conversations, messages, message_delivery_attempts | 3 |
| 4 | AI | prompt_versions, ai_actions, human_approvals | 3 |
| 5 | Operations | lead_assignments, tasks, appointments | 3 |
| 6 | Integrations | integration_connections, crm_mappings, sync_logs | 3 |
| 7 | SLA / Consent | tenant_sla_settings, lead_sla_results, messaging_policy_settings, consent_records, opt_out_records | 5 |
| 8 | Workflow | outbox_events | 1 |
| 9 | Audit / Timeline | audit_logs, activity_timeline | 2 |
| 10 | Knowledge Base | knowledge_documents, knowledge_chunks | 2 |

**Total: 38 tables** *(3 additional tables gated behind DAI-055+: crm_object_locks, notification_preferences, webhook_endpoints)*

---

## ER Diagram (Mermaid)

```mermaid
erDiagram

    %% ════════════════════════════════════════
    %% DOMAIN 1: TENANT / AUTH
    %% ════════════════════════════════════════

    tenants {
        uuid        id              PK
        varchar     name
        varchar     slug            UK  "URL-safe e.g. acme-realty"
        varchar     timezone            "America/New_York"
        boolean     is_active
        jsonb       settings            "Feature flags, white-label config"
        timestamptz created_at
        timestamptz updated_at
    }

    users {
        uuid        id              PK
        varchar     auth0_sub       UK  "Auth0 subject — JWT → internal ID"
        varchar     email
        varchar     name
        text        avatar_url
        boolean     is_active
        timestamptz last_seen_at
        jsonb       metadata            "Extensible attributes"
        timestamptz created_at
        timestamptz updated_at
    }

    tenant_memberships {
        uuid        id              PK
        uuid        user_id         FK
        uuid        tenant_id       FK
        varchar     role_slug           "owner_admin|manager|agent|implementation_admin|auditor"
        uuid        invited_by_id   FK  "Nullable — first admin"
        timestamptz joined_at           "First accepted login under this tenant"
        boolean     is_active
        timestamptz expires_at          "Nullable — temporary access"
        timestamptz created_at
        timestamptz updated_at
    }

    roles {
        uuid        id              PK
        varchar     name            UK  "Human label"
        varchar     slug            UK  "owner_admin|manager|agent|implementation_admin|auditor"
        text        description
        jsonb       permissions         "Seeded — never written at runtime"
        timestamptz created_at
    }

    agent_profiles {
        uuid        id              PK
        uuid        user_id         FK  "1:1 with users"
        uuid        tenant_id       FK
        varchar     phone
        varchar[]   languages           "['en','es']"
        varchar[]   property_types      "['buyer','seller','rental']"
        jsonb       service_areas       "[{city,state,zip_codes[]}]"
        int         max_leads           "Routing capacity"
        boolean     is_available        "Routing toggle"
        uuid        default_calendar_connection_id FK  "Nullable — added after integrations table"
        timestamptz created_at
        timestamptz updated_at
    }

    tenant_invitations {
        uuid        id              PK
        uuid        tenant_id       FK
        varchar     email
        varchar     role_slug           "Role to assign on acceptance"
        uuid        invited_by_id   FK
        varchar     token           UK  "64-char secure random"
        timestamptz expires_at          "72h TTL"
        timestamptz accepted_at         "Null = pending"
        timestamptz created_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 2: LEAD INGESTION
    %% ════════════════════════════════════════

    lead_sources {
        uuid        id              PK
        uuid        tenant_id       FK
        varchar     type                "webhook|csv|email|hubspot|manual"
        varchar     name
        varchar     source_key      UK  "Used in /webhooks/leads/{key}"
        text        secret_hash         "HMAC-SHA256 of signing secret"
        boolean     is_active
        jsonb       config              "Source-specific settings"
        timestamptz created_at
        timestamptz updated_at
    }

    ingestion_events {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        source_id       FK
        varchar     idempotency_key UK  "Unique per (tenant_id, source_id, key)"
        varchar     event_type          "lead_created|lead_updated|contact_updated"
        varchar     status              "received|processing|processed|duplicate|failed"
        jsonb       raw_payload         "Full webhook body"
        uuid        lead_id         FK  "Null until processed"
        text        error_message
        int         error_count
        timestamptz processed_at
        timestamptz created_at
    }

    contacts {
        uuid        id              PK
        uuid        tenant_id       FK
        varchar     first_name
        varchar     last_name
        varchar     language            "ISO 639-1 detected or specified"
        boolean     is_merged           "True if this is a loser in a merge"
        uuid        merged_into_id  FK  "Nullable — points to winner contact"
        jsonb       metadata            "Extra fields from source payload"
        timestamptz created_at
        timestamptz updated_at
    }

    contact_points {
        uuid        id              PK
        uuid        contact_id      FK
        uuid        tenant_id       FK
        varchar     type                "email|phone|whatsapp|imessage|rcs"
        varchar     value_raw           "Original value as received"
        varchar     value_normalized    "E.164 for phone; lowercased for email"
        boolean     is_primary          "One primary per type per contact"
        boolean     is_verified
        varchar     source              "ingestion|manual|crm_import"
        timestamptz created_at
        timestamptz updated_at
    }

    leads {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        contact_id      FK
        uuid        source_id       FK
        uuid        ingestion_event_id FK "Nullable — links back to raw webhook"
        varchar     status              "new|qualifying|qualified|assigned|in_progress|appointment_booked|stale|escalated|closed|spam"
        varchar     lead_type           "buyer|seller|tenant|landlord|investor|vendor|spam|unknown"
        jsonb       raw_payload         "Original source payload"
        float       confidence_score    "AI classification confidence 0..1"
        uuid        assigned_agent_id FK "Quick-access; full history in lead_assignments"
        timestamptz first_response_at
        timestamptz last_activity_at
        timestamptz stale_at
        timestamptz escalated_at
        timestamptz created_at
        timestamptz updated_at
    }

    lead_preferences {
        uuid        id              PK
        uuid        lead_id         FK  "1:1 with leads"
        uuid        tenant_id       FK
        float       budget_min
        float       budget_max
        varchar     location_city
        varchar     location_state
        varchar[]   property_types      "['condo','house','commercial']"
        varchar     timeline            "immediate|1-3months|6months|exploring"
        varchar     financing_status    "cash|pre_approved|needs_financing|unknown"
        varchar     purpose             "buy|sell|rent|invest"
        boolean     appointment_preferred
        jsonb       raw_extraction      "Full AI extraction output"
        float       confidence_score
        timestamptz created_at
        timestamptz updated_at
    }

    lead_scores {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        float       score               "0..100 composite score"
        varchar     scoring_model       "v1|v2|custom"
        jsonb       factors             "Breakdown: {engagement:0.4, fit:0.3, ...}"
        uuid        ai_action_id    FK  "Nullable — links to AI computation"
        varchar     crm_score_id        "Nullable — HubSpot/Salesforce score ID"
        timestamptz created_at
    }

    lead_next_actions {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        uuid        ai_action_id    FK
        varchar     action_type         "send_message|schedule_call|send_listing|escalate|close"
        varchar     priority            "low|medium|high|urgent"
        text        description
        timestamptz due_at
        varchar     status              "pending|completed|skipped|superseded"
        varchar     crm_task_id         "Nullable — HubSpot task ID after writeback"
        timestamptz created_at
        timestamptz updated_at
    }

    dedupe_candidates {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        contact_a_id    FK
        uuid        contact_b_id    FK
        float       match_score         "0..1 similarity"
        jsonb       match_signals       "Which fields matched and how"
        varchar     status              "pending|merged|dismissed"
        uuid        reviewed_by_id  FK  "Nullable — system auto-merge if score>=0.95"
        timestamptz reviewed_at
        timestamptz created_at
    }

    contact_merge_events {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        winner_id       FK  "Surviving contact"
        uuid        loser_id        FK  "Archived contact"
        uuid        merged_by_id    FK  "Nullable — system auto-merge"
        varchar     merge_reason        "auto_high_confidence|manual|crm_dedup"
        jsonb       field_decisions     "Which source won per field"
        timestamptz merged_at
        timestamptz created_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 3: CONVERSATIONS
    %% ════════════════════════════════════════

    conversations {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        uuid        contact_id      FK
        varchar     channel             "sms|whatsapp|email|imessage|rcs"
        varchar     status              "active|closed"
        timestamptz last_message_at
        timestamptz created_at
    }

    messages {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        conversation_id FK
        uuid        lead_id         FK
        varchar     direction           "inbound|outbound"
        varchar     channel             "sms|whatsapp|email|imessage|rcs"
        text        body
        varchar     status              "queued|sent|delivered|failed|undelivered|read"
        uuid        sent_by_id      FK  "Null if AI/automated"
        boolean     is_ai_generated
        uuid        ai_action_id    FK  "Links to AI draft"
        timestamptz sent_at
        timestamptz delivered_at
        timestamptz read_at
        timestamptz created_at
    }

    message_delivery_attempts {
        uuid        id              PK
        uuid        message_id      FK
        uuid        tenant_id       FK
        varchar     provider            "twilio|sendgrid|mailgun"
        varchar     provider_message_id "Twilio SID / email provider ID per attempt"
        varchar     status              "accepted|queued|sending|sent|delivered|failed|undelivered"
        varchar     error_code
        text        error_message
        timestamptz attempted_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 4: AI
    %% ════════════════════════════════════════

    prompt_versions {
        uuid        id              PK
        varchar     name                "lead_classification|extraction|summary|draft|safety_review"
        int         version
        text        template
        jsonb       input_schema
        jsonb       output_schema
        boolean     is_active
        timestamptz created_at
    }

    ai_actions {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        varchar     action_type         "classification|extraction|summary|next_action|draft|safety_check|scoring"
        varchar     model               "claude-sonnet-4-6 etc."
        uuid        prompt_version_id FK
        text        input_ref           "Reference — never full content"
        jsonb       output_json         "Structured AI output"
        float       confidence_score
        varchar     safety_decision     "safe|approval_required|blocked|escalate"
        varchar     status              "pending|completed|failed"
        timestamptz created_at
    }

    human_approvals {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        uuid        ai_action_id    FK
        varchar     approval_type       "message_send|escalation|lead_close|score_override"
        text        draft_content       "AI-generated draft"
        varchar     status              "pending|approved|edited|rejected|taken_over|expired"
        uuid        reviewed_by_id  FK
        text        reviewed_content    "Edited version if status=edited"
        text        review_note
        timestamptz reviewed_at
        timestamptz expires_at          "Auto-expire stale approvals"
        timestamptz created_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 5: OPERATIONS
    %% ════════════════════════════════════════

    lead_assignments {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        uuid        agent_id        FK
        uuid        assigned_by_id  FK  "Null = routing engine"
        varchar     reason              "routing_rule|manual|rebalance"
        timestamptz assigned_at
        timestamptz unassigned_at       "Null = currently active"
    }

    tasks {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        uuid        assigned_to_id  FK
        uuid        created_by_id   FK  "Null = system"
        varchar     task_type           "follow_up|approval|stale_review|appointment_prep|crm_issue"
        varchar     title
        text        description
        varchar     status              "pending|in_progress|completed|overdue|cancelled"
        varchar     priority            "low|medium|high"
        timestamptz due_at
        timestamptz completed_at
        timestamptz created_at
        timestamptz updated_at
    }

    appointments {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        uuid        agent_id        FK
        uuid        task_id         FK  "Nullable — task that triggered booking"
        varchar     type                "call|site_visit|video|other"
        varchar     status              "scheduled|confirmed|cancelled|completed|no_show"
        varchar     calendar_provider   "google|microsoft"
        varchar     calendar_event_id
        timestamptz scheduled_at
        int         duration_minutes
        text        location
        text        notes
        timestamptz created_at
        timestamptz updated_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 6: INTEGRATIONS
    %% ════════════════════════════════════════

    integration_connections {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        agent_id        FK  "Nullable — per-agent calendar connections"
        varchar     provider            "hubspot|twilio|google_calendar|ms_calendar|email"
        varchar     status              "connected|disconnected|error"
        text        credentials_enc     "Fernet-encrypted OAuth tokens / API keys"
        jsonb       config              "Provider-specific config"
        timestamptz last_sync_at
        timestamptz last_error_at
        text        last_error_msg
        timestamptz created_at
        timestamptz updated_at
    }

    crm_mappings {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        connection_id   FK
        varchar     dealflow_field
        varchar     crm_field
        varchar     crm_object          "contact|deal|task|note|meeting"
        varchar     idempotency_key_field "CRM field used as idempotency key"
        boolean     is_active
        timestamptz created_at
        timestamptz updated_at
    }

    sync_logs {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        connection_id   FK
        uuid        lead_id         FK  "Nullable — some syncs are tenant-level"
        varchar     idempotency_key     "Unique per (connection_id, crm_object, crm_record_id)"
        varchar     operation           "upsert_contact|upsert_deal|create_task|create_note|create_meeting"
        varchar     status              "success|failed|retrying"
        varchar     crm_record_id       "ID returned by CRM after write"
        jsonb       request_ref         "Reference only — no secrets"
        jsonb       response_ref
        text        error_message
        int         retry_count
        timestamptz next_retry_at
        timestamptz created_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 7: SLA / CONSENT
    %% ════════════════════════════════════════

    tenant_sla_settings {
        uuid        id              PK
        uuid        tenant_id       FK  "1:1 with tenants"
        int         first_response_min
        int         agent_followup_hrs
        int         stale_lead_hrs
        int         escalation_hrs
        jsonb       custom_rules        "Priority overrides per lead type/source"
        timestamptz updated_at
    }

    lead_sla_results {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK  "1:1 with leads"
        boolean     first_response_met
        timestamptz first_response_at
        int         first_response_mins
        boolean     agent_followup_met
        boolean     is_stale
        timestamptz stale_since
        boolean     is_escalated
        timestamptz escalated_at
        timestamptz last_computed_at
    }

    messaging_policy_settings {
        uuid        id              PK
        uuid        tenant_id       FK  "1:1 with tenants"
        boolean     sms_enabled
        boolean     whatsapp_enabled
        boolean     email_enabled
        boolean     imessage_enabled
        boolean     rcs_enabled
        boolean     auto_send_sms
        boolean     auto_send_whatsapp
        boolean     auto_send_email
        jsonb       custom_rules        "Per-lead-type overrides"
        timestamptz updated_at
    }

    consent_records {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        contact_id      FK
        varchar     channel             "sms|whatsapp|email|imessage|rcs"
        varchar     status              "granted|denied|unknown"
        varchar     source              "explicit|implied|imported"
        timestamptz consented_at
        timestamptz created_at
        timestamptz updated_at
    }

    opt_out_records {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        contact_id      FK
        varchar     channel
        varchar     trigger             "stop_keyword|unsubscribe_link|manual|api"
        uuid        message_id      FK  "Message that triggered the opt-out"
        timestamptz opted_out_at
        timestamptz reinstated_at       "Null = still opted out"
        timestamptz created_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 8: WORKFLOW
    %% ════════════════════════════════════════

    outbox_events {
        uuid        id              PK
        uuid        tenant_id       FK  "Nullable — system-level events"
        varchar     aggregate_type      "lead|contact|message|sync"
        uuid        aggregate_id
        varchar     event_type          "lead.created|message.send|crm.sync|score.computed"
        jsonb       payload             "Event data for worker"
        varchar     status              "pending|processing|processed|failed|dead"
        int         attempts
        timestamptz last_attempt_at
        timestamptz next_attempt_at
        timestamptz processed_at
        text        error
        timestamptz created_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 9: AUDIT / TIMELINE
    %% ════════════════════════════════════════

    audit_logs {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        actor_id        FK  "Null = system"
        varchar     actor_type          "user|system|ai"
        varchar     action              "user.created|lead.assigned|role.granted|..."
        varchar     entity_type         "user|lead|message|approval|..."
        uuid        entity_id
        jsonb       before_state        "Snapshot — PII fields scrubbed"
        jsonb       after_state         "Snapshot — PII fields scrubbed"
        boolean     pii_fields_scrubbed "True after scrubbing worker has run"
        varchar     ip_address
        timestamptz created_at          "Immutable — never updated"
    }

    activity_timeline {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        lead_id         FK
        varchar     event_type          "message|assignment|task|ai_action|approval|appointment|sync|sla_breach|escalation"
        jsonb       event_data          "Denormalized snapshot — no raw PII"
        uuid        actor_id        FK
        varchar     actor_type          "user|system|ai|contact"
        boolean     visible_to_agent
        timestamptz occurred_at
        timestamptz created_at
    }

    %% ════════════════════════════════════════
    %% DOMAIN 10: KNOWLEDGE BASE
    %% ════════════════════════════════════════

    knowledge_documents {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        uploaded_by_id  FK
        varchar     filename
        varchar     mime_type
        bigint      file_size_bytes
        varchar     status              "processing|active|failed|archived"
        int         chunk_count
        timestamptz created_at
        timestamptz updated_at
    }

    knowledge_chunks {
        uuid        id              PK
        uuid        tenant_id       FK
        uuid        document_id     FK
        int         chunk_index
        text        content
        vector      embedding           "pgvector 1536-dim — OpenAI text-embedding-3-small"
        jsonb       metadata            "page, section, source context"
        timestamptz created_at
    }

    %% ════════════════════════════════════════
    %% RELATIONSHIPS
    %% ════════════════════════════════════════

    %% Tenant / Auth
    tenants                     ||--o{ tenant_memberships          : "has members"
    users                       ||--o{ tenant_memberships          : "belongs to"
    roles                       ||--o{ tenant_memberships          : "assigned via"
    tenants                     ||--o{ tenant_invitations          : "sends"
    users                       ||--o| agent_profiles              : "has profile"

    %% Lead Ingestion
    tenants                     ||--o{ lead_sources                : "configures"
    lead_sources                ||--o{ ingestion_events            : "receives"
    ingestion_events            o|--o| leads                       : "creates"
    tenants                     ||--o{ contacts                    : "owns"
    contacts                    ||--o{ contact_points              : "has identifiers"
    contacts                    ||--o{ leads                       : "has"
    lead_sources                ||--o{ leads                       : "generates"
    leads                       ||--o| lead_preferences            : "has"
    leads                       ||--o| lead_sla_results            : "has"
    leads                       ||--o{ lead_scores                 : "scored by"
    leads                       ||--o{ lead_next_actions           : "has actions"
    tenants                     ||--o{ dedupe_candidates           : "has"
    contacts                    ||--o{ dedupe_candidates           : "candidate_a"
    tenants                     ||--o{ contact_merge_events        : "has"

    %% Conversations
    leads                       ||--o{ conversations               : "has"
    contacts                    ||--o{ conversations               : "participates in"
    conversations               ||--o{ messages                    : "contains"
    messages                    ||--o{ message_delivery_attempts   : "has attempts"
    messages                    o|--o| ai_actions                  : "generated by"

    %% AI
    prompt_versions             ||--o{ ai_actions                  : "used in"
    leads                       ||--o{ ai_actions                  : "triggers"
    ai_actions                  ||--o{ human_approvals             : "requires"

    %% Operations
    leads                       ||--o{ lead_assignments            : "assigned via"
    users                       ||--o{ lead_assignments            : "receives"
    leads                       ||--o{ tasks                       : "has"
    leads                       ||--o{ appointments                : "books"
    users                       ||--o{ appointments                : "attends"

    %% Integrations
    tenants                     ||--o{ integration_connections     : "connects"
    integration_connections     ||--o{ crm_mappings                : "configures"
    integration_connections     ||--o{ sync_logs                   : "records"
    leads                       ||--o{ sync_logs                   : "synced via"

    %% SLA / Consent
    tenants                     ||--||  tenant_sla_settings        : "configures"
    tenants                     ||--||  messaging_policy_settings  : "configures"
    contacts                    ||--o{ consent_records             : "has"
    contacts                    ||--o{ opt_out_records             : "has"
    messages                    ||--o{ opt_out_records             : "triggers"

    %% Audit / Timeline
    leads                       ||--o{ activity_timeline           : "has"
    tenants                     ||--o{ audit_logs                  : "scoped to"
    tenants                     ||--o{ activity_timeline           : "scoped to"

    %% Knowledge Base
    tenants                     ||--o{ knowledge_documents         : "owns"
    knowledge_documents         ||--o{ knowledge_chunks            : "split into"
    users                       ||--o{ knowledge_documents         : "uploads"
```

---

## Entity Details

### Domain 1: Tenant / Auth

| Entity | Use Case |
|---|---|
| **tenants** | Workspace isolation boundary. Every business query filters by `tenant_id`. `settings` JSONB holds feature flags and white-label config. |
| **users** | Global — one record per Auth0 identity. A user can be a member of multiple tenants via `tenant_memberships`. `is_active` = soft delete. |
| **tenant_memberships** | Replaces V1 `user_roles` as the primary join. One row per (user, tenant) pair. `role_slug` is a lightweight reference into the seeded `roles` table. `expires_at` supports temporary elevated access. |
| **roles** | 5 seeded system roles: `owner_admin`, `manager`, `agent`, `implementation_admin`, `auditor`. Never written at runtime — `permissions` JSONB is read-only. |
| **agent_profiles** | Created when `role_slug = 'agent'`. Drives lead routing: `languages`, `property_types`, `service_areas`, `max_leads`, `is_available`. `default_calendar_connection_id` FK added in migration 0005 (after `integration_connections` exists). |
| **tenant_invitations** | Admin invites by email → secure token → user clicks → `tenant_memberships` row created. `accepted_at` set; `expires_at` enforces 72h TTL. |

---

### Domain 2: Lead Ingestion

| Entity | Use Case |
|---|---|
| **lead_sources** | One per ingestion channel per tenant. `source_key` used in webhook URL `/webhooks/leads/{key}`. `secret_hash` stores HMAC-SHA256 of signing secret for payload verification. |
| **ingestion_events** | **New in V2.** Created immediately on webhook receipt before any processing. `idempotency_key` (unique per `tenant_id + source_id + key`) prevents double-processing when Twilio/HubSpot fires the same event twice. Status transitions: `received → processing → processed/duplicate/failed`. |
| **contacts** | Deduplicated person record. No `email`/`phone` columns — those live in `contact_points`. `is_merged` + `merged_into_id` supports soft-archive of loser contacts after merging. |
| **contact_points** | **New in V2.** One row per identifier per contact. Supports same person having email + phone + WhatsApp. No unique constraint on `value_normalized` — spouses/families can share a number. `is_primary` marks the preferred identifier per type. |
| **leads** | Core workflow record. `ingestion_event_id` links back to the raw webhook for full traceability. `assigned_agent_id` is quick-access (full history in `lead_assignments`). |
| **lead_preferences** | AI-extracted qualification. Written once after classification; updated if re-extraction runs. `raw_extraction` stores the complete AI output for debugging and re-processing. |
| **lead_scores** | **New in V2.** Append-only history — one row per scoring run. Enables trend charts on lead detail page and CRM writeback of score via `crm_score_id`. |
| **lead_next_actions** | **New in V2.** AI-recommended actions per lead. `crm_task_id` stores the HubSpot task ID after writeback. `status = superseded` when a newer action replaces this one. |
| **dedupe_candidates** | **New in V2.** Written by the dedup worker when two contacts share ≥1 identifier. `match_score ≥ 0.95` → auto-merge; lower → queued for human review. |
| **contact_merge_events** | **New in V2.** Immutable record of every merge. `field_decisions` JSONB records which contact's value won per field. `loser_id` contact is soft-archived. |

---

### Domain 3: Conversations

| Entity | Use Case |
|---|---|
| **conversations** | One per contact per channel per lead. An SMS thread and a WhatsApp thread with the same contact are separate records. `last_message_at` drives SLA computation. |
| **messages** | Individual messages. `is_ai_generated` + `ai_action_id` provides AI audit trail. No `provider_message_id` column — moved to `message_delivery_attempts`. |
| **message_delivery_attempts** | **New in V2.** One row per provider send attempt. Solves the multiple-Twilio-SID problem: each retry creates a new attempt row with its own `provider_message_id`. `status` updated via Twilio callback. |

---

### Domain 4: AI

| Entity | Use Case |
|---|---|
| **prompt_versions** | Registry. Every AI call logs `prompt_version_id`. Safe to update active version — old logs still point to the version actually used. |
| **ai_actions** | Immutable log of every LLM invocation. `input_ref` is a pointer (S3 key, conversation ID) — never the full prompt text to avoid bloating the table. |
| **human_approvals** | Queue for AI drafts requiring review. `draft_content` = AI output; `reviewed_content` = agent edit. `expires_at` auto-expires stale queued items. |

---

### Domain 5: Operations

| Entity | Use Case |
|---|---|
| **lead_assignments** | Full history. `unassigned_at NULL` = currently active. Supports reassignment reporting and workload balancing. |
| **tasks** | System-created (stale scan, AI next-action) or manual. Linked to HubSpot tasks via `sync_logs`. `overdue` status set by worker scan. |
| **appointments** | Booked via calendar integration. `calendar_event_id` links to Google/MS event. Status: `scheduled → confirmed → completed` or `cancelled/no_show`. |

---

### Domain 6: Integrations

| Entity | Use Case |
|---|---|
| **integration_connections** | One row per provider per tenant (or per agent for calendar). `agent_id` is nullable — set for Google Calendar / MS Calendar connections that are per-agent. `credentials_enc` is Fernet-encrypted — decryption key stored in Vault/Secrets Manager, never in DB. |
| **crm_mappings** | Field mapping: DealFlow field → CRM property per object type. `idempotency_key_field` identifies which CRM field to use as the dedup key on upserts (e.g., `email` for contacts, `hs_deal_id` for deals). |
| **sync_logs** | Every CRM write attempt. `idempotency_key` unique per `(connection_id, crm_object, crm_record_id)` prevents duplicate HubSpot object creation on retry. `retry_count + next_retry_at` drives the retry worker. |

---

### Domain 7: SLA / Consent

| Entity | Use Case |
|---|---|
| **tenant_sla_settings** | 1:1 with tenant. `custom_rules` JSONB allows per-source or per-lead-type SLA overrides (e.g., Zillow leads get 5-min SLA). |
| **lead_sla_results** | Computed by stale-scan worker. Dashboard reads this for SLA breach metrics without recomputing on every load. |
| **messaging_policy_settings** | Policy engine checks this before every outbound send. `auto_send_*` false = always require human approval for that channel. |
| **consent_records** | Per contact per channel. Updated when consent is (re)obtained. Policy engine reads this before sending. |
| **opt_out_records** | `reinstated_at NULL` = still opted out. Policy engine blocks auto-send if an active opt-out exists. |

---

### Domain 8: Workflow

| Entity | Use Case |
|---|---|
| **outbox_events** | **New in V2.** Written in the same DB transaction as the business record (lead, message, sync). Worker polls for `status = pending` rows and dispatches to ARQ/Redis. Solves the "lead created but job never enqueued" problem when Redis is temporarily unavailable. `status = dead` after max retry exhaustion → alerts. |

---

### Domain 9: Audit / Timeline

| Entity | Use Case |
|---|---|
| **audit_logs** | Append-only compliance log. Every create/update/delete writes before/after JSONB. `pii_fields_scrubbed` is `false` on insert; a scrubbing worker redacts sensitive fields (email, phone, body) within 1h and sets this to `true`. |
| **activity_timeline** | Denormalized, lead-scoped feed for the lead detail UI. `event_data` avoids JOINs. `visible_to_agent` hides internal system events from agent views. |

---

### Domain 10: Knowledge Base

| Entity | Use Case |
|---|---|
| **knowledge_documents** | Uploaded PDFs/DOCX/TXT. `status` tracks the processing pipeline: `processing → active` or `failed`. |
| **knowledge_chunks** | ~500-token chunks with pgvector `vector(1536)` embeddings. RAG retriever uses cosine similarity (`<=>`) to find relevant chunks before AI drafts a message. |

---

## Constraints & Indexes

### Critical Unique Constraints

| Table | Constraint | Notes |
|---|---|---|
| `users` | `UNIQUE (auth0_sub)` | JWT → internal ID mapping |
| `tenants` | `UNIQUE (slug)` | URL-safe identifier |
| `tenant_memberships` | `UNIQUE (user_id, tenant_id)` | One membership per user per tenant |
| `roles` | `UNIQUE (slug)` | Seeded reference table |
| `lead_sources` | `UNIQUE (source_key)` | Webhook URL uniqueness |
| `ingestion_events` | `UNIQUE (tenant_id, source_id, idempotency_key)` | Dedup webhook events |
| `tenant_invitations` | `UNIQUE (token)` | Single-use invite tokens |
| `sync_logs` | `UNIQUE (connection_id, idempotency_key)` | Dedup CRM writes |
| `conversations` | `UNIQUE (lead_id, contact_id, channel)` | One thread per channel per lead |

### Performance Indexes

| Table | Index | Purpose |
|---|---|---|
| `leads` | `(tenant_id, status)` | Lead list + status filter queries |
| `leads` | `(tenant_id, assigned_agent_id)` | Agent workload queries |
| `leads` | `(tenant_id, created_at DESC)` | Lead list pagination |
| `messages` | `(conversation_id, created_at DESC)` | Conversation thread pagination |
| `ingestion_events` | `(source_id, status)` | Processing queue queries |
| `outbox_events` | `(status, next_attempt_at)` WHERE status != 'processed' | Worker polling (partial index) |
| `audit_logs` | `(tenant_id, entity_id, created_at DESC)` | Entity audit trail |
| `sync_logs` | `(connection_id, status, next_retry_at)` | Retry worker queries |
| `contact_points` | `(tenant_id, type, value_normalized)` | Dedup matching lookups |
| `knowledge_chunks` | `HNSW (embedding vector_cosine_ops)` | pgvector approximate nearest neighbor |

---

## PII Handling Rules

| Field | Location | Rule |
|---|---|---|
| `email`, `phone` | `contact_points.value_raw`, `contact_points.value_normalized` | Encrypted at rest (column-level). Scrubbing worker redacts from `audit_logs` within 1h. |
| `body` | `messages.body` | Encrypted at rest. Not stored in `activity_timeline.event_data`. |
| `draft_content`, `reviewed_content` | `human_approvals` | PII allowed (agent must see content). Not mirrored to audit logs. |
| `before_state`, `after_state` | `audit_logs` | Written with PII initially. Scrubbing worker sets `pii_fields_scrubbed = true` after redaction. |
| `raw_payload` | `leads`, `ingestion_events` | Stored for debugging. Access gated to `implementation_admin` and `auditor` roles. |
| `credentials_enc` | `integration_connections` | Fernet-encrypted. Decryption key in Vault — never in DB. |

---

## Tenant Isolation Summary

```
Tables WITH tenant_id (35):
  tenant_memberships, tenant_invitations, agent_profiles,
  lead_sources, ingestion_events, contacts, contact_points,
  leads, lead_preferences, lead_scores, lead_next_actions,
  dedupe_candidates, contact_merge_events,
  conversations, messages, message_delivery_attempts,
  ai_actions, human_approvals,
  lead_assignments, tasks, appointments,
  integration_connections, crm_mappings, sync_logs,
  tenant_sla_settings (1:1 = IS the tenant scope),
  lead_sla_results, messaging_policy_settings (1:1),
  consent_records, opt_out_records,
  outbox_events (nullable — system events have null),
  audit_logs, activity_timeline,
  knowledge_documents, knowledge_chunks

Tables WITHOUT tenant_id (global reference / system):
  roles             — global seeded reference
  prompt_versions   — global AI prompt registry
```

Repository base class enforces `tenant_id` filter on every query.
Direct DB access without tenant filter = security violation.

---

## MVP Build Cutline (P0)

**Must ship before beta:**
All 38 tables above are P0.

**Post-beta (P1):**
- `crm_object_locks` — optimistic locking for concurrent HubSpot writes
- `notification_preferences` — per-user notification channel settings
- `webhook_endpoints` — allow tenants to register outbound webhooks
- `lead_custom_fields` — tenant-defined schema extensions
- `conversation_summaries` — AI-generated summary cache per conversation
