"""
Seed the demo tenant with realistic real estate data.

Usage:
  DATABASE_URL=... uv run python scripts/seed_demo.py
"""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg

DATABASE_URL = "postgresql://dealflow:dealflow@localhost:5432/dealflow"

TENANT_ID = "00000000-0000-0000-0000-000000000001"
DEV_USER_ID = "20000000-0000-0000-0000-000000000001"

# Seeded lead sources (from migration 0007)
SRC_ZILLOW = "10000000-0000-0000-0000-000000000001"
SRC_HUBSPOT = "10000000-0000-0000-0000-000000000002"
SRC_WEBFORM = "10000000-0000-0000-0000-000000000003"

def now() -> datetime:
    return datetime.now(tz=UTC)

def ago(**kwargs) -> datetime:
    return now() - timedelta(**kwargs)

def uid() -> str:
    return str(uuid.uuid4())


# ── Agents (team members) ────────────────────────────────────────────────────

AGENTS = [
    {"id": "30000000-0000-0000-0000-000000000001", "sub": "agent|sarah", "name": "Sarah Chen", "email": "sarah@brokerage.com", "role": "manager"},
    {"id": "30000000-0000-0000-0000-000000000002", "sub": "agent|mike", "name": "Michael Torres", "email": "m.torres@brokerage.com", "role": "agent"},
    {"id": "30000000-0000-0000-0000-000000000003", "sub": "agent|priya", "name": "Priya Nair", "email": "p.nair@brokerage.com", "role": "agent"},
    {"id": "30000000-0000-0000-0000-000000000004", "sub": "agent|alex", "name": "Alex Johnson", "email": "alex@brokerage.com", "role": "owner_admin"},
]

# ── Lead data ────────────────────────────────────────────────────────────────

LEADS = [
    {
        "first": "James", "last": "Whitfield",
        "email": "j.whitfield@gmail.com", "phone": "+14155559001",
        "status": "new", "lead_type": "buyer", "score": 0.82,
        "source": SRC_ZILLOW, "agent": None,
        "prefs": {"budget_min": 650000, "budget_max": 850000, "city": "San Francisco", "state": "CA",
                  "types": ["condo", "townhouse"], "timeline": "3_months", "financing": "pre_approved"},
        "created": ago(hours=2),
        "events": [
            {"type": "lead.created", "data": {"source": "zillow_inquiry"}, "actor": "system", "at": ago(hours=2)},
            {"type": "lead.scored", "data": {"score": 0.82, "tier": "hot", "method": "heuristic"}, "actor": "system", "at": ago(hours=2, minutes=1)},
        ]
    },
    {
        "first": "Aisha", "last": "Patel",
        "email": "aisha.patel@outlook.com", "phone": "+16505558422",
        "status": "contacted", "lead_type": "buyer", "score": 0.71,
        "source": SRC_HUBSPOT, "agent": "30000000-0000-0000-0000-000000000002",
        "prefs": {"budget_min": 1200000, "budget_max": 1800000, "city": "Palo Alto", "state": "CA",
                  "types": ["single_family"], "timeline": "6_months", "financing": "cash"},
        "created": ago(days=1, hours=4),
        "events": [
            {"type": "lead.created", "data": {"source": "hubspot_sync"}, "actor": "system", "at": ago(days=1, hours=4)},
            {"type": "lead.scored", "data": {"score": 0.71, "tier": "warm"}, "actor": "system", "at": ago(days=1, hours=4, minutes=2)},
            {"type": "lead.assigned", "data": {"agent_name": "Michael Torres"}, "actor": "user", "at": ago(days=1, hours=3)},
            {"type": "sms.sent", "data": {"message": "Hi Aisha, this is Michael from Bay Realty. Let me know a good time to connect!"}, "actor": "user", "at": ago(days=1, hours=3)},
        ]
    },
    {
        "first": "Carlos", "last": "Mendez",
        "email": "c.mendez@company.io", "phone": "+13105557823",
        "status": "qualified", "lead_type": "buyer", "score": 0.91,
        "source": SRC_WEBFORM, "agent": "30000000-0000-0000-0000-000000000001",
        "prefs": {"budget_min": 2000000, "budget_max": 3500000, "city": "Beverly Hills", "state": "CA",
                  "types": ["single_family", "luxury"], "timeline": "immediate", "financing": "pre_approved"},
        "created": ago(days=3),
        "events": [
            {"type": "lead.created", "data": {"source": "web_form"}, "actor": "system", "at": ago(days=3)},
            {"type": "lead.scored", "data": {"score": 0.91, "tier": "hot"}, "actor": "system", "at": ago(days=3, minutes=1)},
            {"type": "lead.assigned", "data": {"agent_name": "Sarah Chen"}, "actor": "user", "at": ago(days=3)},
            {"type": "sms.sent", "data": {"message": "Hi Carlos, I have 3 properties that match your criteria perfectly."}, "actor": "user", "at": ago(days=2, hours=23)},
            {"type": "note.added", "data": {"text": "Very motivated buyer. Ready to make offer on the right property. Prefers modern architecture."}, "actor": "user", "at": ago(days=2, hours=22)},
            {"type": "lead.status_changed", "data": {"from": "contacted", "to": "qualified"}, "actor": "user", "at": ago(days=2)},
        ]
    },
    {
        "first": "Emily", "last": "Nakamura",
        "email": "emily.n@gmail.com", "phone": "+14085554219",
        "status": "qualified", "lead_type": "seller", "score": 0.65,
        "source": SRC_ZILLOW, "agent": "30000000-0000-0000-0000-000000000002",
        "prefs": {"budget_min": None, "budget_max": None, "city": "San Jose", "state": "CA",
                  "types": ["single_family"], "timeline": "3_months", "financing": None},
        "created": ago(days=5),
        "events": [
            {"type": "lead.created", "data": {"source": "zillow_seller_inquiry"}, "actor": "system", "at": ago(days=5)},
            {"type": "lead.scored", "data": {"score": 0.65, "tier": "warm"}, "actor": "system", "at": ago(days=5, minutes=1)},
            {"type": "lead.assigned", "data": {"agent_name": "Michael Torres"}, "actor": "user", "at": ago(days=5)},
            {"type": "note.added", "data": {"text": "Seller — wants to list 4BR home. Expects $1.4M. Will need CMA before listing."}, "actor": "user", "at": ago(days=4, hours=20)},
        ]
    },
    {
        "first": "David", "last": "Kim",
        "email": "dkim.realty@gmail.com", "phone": "+12125556677",
        "status": "new", "lead_type": "investor", "score": 0.55,
        "source": SRC_WEBFORM, "agent": None,
        "prefs": {"budget_min": 500000, "budget_max": 1500000, "city": "Austin", "state": "TX",
                  "types": ["multi_family", "commercial"], "timeline": "flexible", "financing": "portfolio_loan"},
        "created": ago(hours=8),
        "events": [
            {"type": "lead.created", "data": {"source": "web_form", "campaign": "investor_q2"}, "actor": "system", "at": ago(hours=8)},
            {"type": "lead.scored", "data": {"score": 0.55, "tier": "warm"}, "actor": "system", "at": ago(hours=8, minutes=1)},
        ]
    },
    {
        "first": "Sophie", "last": "Laurent",
        "email": "sophie.laurent@gmail.com", "phone": "+14154443322",
        "status": "converted", "lead_type": "buyer", "score": 0.88,
        "source": SRC_HUBSPOT, "agent": "30000000-0000-0000-0000-000000000001",
        "prefs": {"budget_min": 900000, "budget_max": 1200000, "city": "Marin County", "state": "CA",
                  "types": ["single_family"], "timeline": "immediate", "financing": "pre_approved"},
        "created": ago(days=30),
        "events": [
            {"type": "lead.created", "data": {"source": "hubspot_sync"}, "actor": "system", "at": ago(days=30)},
            {"type": "lead.scored", "data": {"score": 0.88, "tier": "hot"}, "actor": "system", "at": ago(days=30, minutes=1)},
            {"type": "lead.assigned", "data": {"agent_name": "Sarah Chen"}, "actor": "user", "at": ago(days=30)},
            {"type": "sms.sent", "data": {"message": "Hi Sophie, welcome to Bay Realty!"}, "actor": "user", "at": ago(days=29, hours=23)},
            {"type": "note.added", "data": {"text": "Interested in 4 Birch Lane — scheduled showing for Saturday."}, "actor": "user", "at": ago(days=25)},
            {"type": "lead.status_changed", "data": {"from": "qualified", "to": "converted"}, "actor": "user", "at": ago(days=18)},
            {"type": "note.added", "data": {"text": "Offer accepted at $1,075,000. Closing in 30 days."}, "actor": "user", "at": ago(days=18)},
        ]
    },
    {
        "first": "Marcus", "last": "Thompson",
        "email": "m.thompson@email.com", "phone": "+17025557890",
        "status": "lost", "lead_type": "buyer", "score": 0.32,
        "source": SRC_ZILLOW, "agent": "30000000-0000-0000-0000-000000000003",
        "prefs": {"budget_min": 400000, "budget_max": 550000, "city": "Las Vegas", "state": "NV",
                  "types": ["condo"], "timeline": "flexible", "financing": "mortgage"},
        "created": ago(days=45),
        "events": [
            {"type": "lead.created", "data": {"source": "zillow_inquiry"}, "actor": "system", "at": ago(days=45)},
            {"type": "lead.scored", "data": {"score": 0.32, "tier": "cold"}, "actor": "system", "at": ago(days=45, minutes=1)},
            {"type": "lead.assigned", "data": {"agent_name": "Priya Nair"}, "actor": "user", "at": ago(days=44)},
            {"type": "note.added", "data": {"text": "Not responding to follow-up calls. Marked as lost after 3 attempts."}, "actor": "user", "at": ago(days=30)},
            {"type": "lead.status_changed", "data": {"from": "contacted", "to": "lost"}, "actor": "user", "at": ago(days=30)},
        ]
    },
    {
        "first": "Rachel", "last": "Goldstein",
        "email": "rachg@yahoo.com", "phone": "+13235551234",
        "status": "contacted", "lead_type": "buyer", "score": 0.76,
        "source": SRC_WEBFORM, "agent": "30000000-0000-0000-0000-000000000004",
        "prefs": {"budget_min": 750000, "budget_max": 1100000, "city": "Santa Monica", "state": "CA",
                  "types": ["condo", "townhouse"], "timeline": "6_months", "financing": "pre_approved"},
        "created": ago(days=2),
        "events": [
            {"type": "lead.created", "data": {"source": "web_form"}, "actor": "system", "at": ago(days=2)},
            {"type": "lead.scored", "data": {"score": 0.76, "tier": "hot"}, "actor": "system", "at": ago(days=2, minutes=1)},
            {"type": "lead.assigned", "data": {"agent_name": "Alex Johnson"}, "actor": "user", "at": ago(days=2)},
            {"type": "sms.sent", "data": {"message": "Hi Rachel, Alex here from Bay Realty. Looking forward to helping you find your new home!"}, "actor": "user", "at": ago(days=1, hours=22)},
        ]
    },
    {
        "first": "Omar", "last": "Hassan",
        "email": "omar.hassan@proton.me", "phone": "+12025558834",
        "status": "new", "lead_type": "buyer", "score": 0.43,
        "source": SRC_ZILLOW, "agent": None,
        "prefs": {"budget_min": 300000, "budget_max": 450000, "city": "Phoenix", "state": "AZ",
                  "types": ["single_family"], "timeline": "12_months", "financing": "fha"},
        "created": ago(hours=14),
        "events": [
            {"type": "lead.created", "data": {"source": "zillow_inquiry"}, "actor": "system", "at": ago(hours=14)},
            {"type": "lead.scored", "data": {"score": 0.43, "tier": "warm"}, "actor": "system", "at": ago(hours=14, minutes=1)},
        ]
    },
    {
        "first": "Natalia", "last": "Rivera",
        "email": "natalia.r@gmail.com", "phone": "+17135556611",
        "status": "qualified", "lead_type": "buyer", "score": 0.84,
        "source": SRC_HUBSPOT, "agent": "30000000-0000-0000-0000-000000000003",
        "prefs": {"budget_min": 550000, "budget_max": 700000, "city": "Houston", "state": "TX",
                  "types": ["single_family", "townhouse"], "timeline": "3_months", "financing": "conventional"},
        "created": ago(days=7),
        "events": [
            {"type": "lead.created", "data": {"source": "hubspot_sync"}, "actor": "system", "at": ago(days=7)},
            {"type": "lead.scored", "data": {"score": 0.84, "tier": "hot"}, "actor": "system", "at": ago(days=7, minutes=1)},
            {"type": "lead.assigned", "data": {"agent_name": "Priya Nair"}, "actor": "user", "at": ago(days=7)},
            {"type": "sms.sent", "data": {"message": "Hi Natalia! I have 5 listings that match your budget and neighborhood preferences."}, "actor": "user", "at": ago(days=6, hours=20)},
            {"type": "note.added", "data": {"text": "Toured 3 properties. Liked 2214 Maple Drive the most. Following up to schedule second visit."}, "actor": "user", "at": ago(days=4)},
            {"type": "lead.status_changed", "data": {"from": "contacted", "to": "qualified"}, "actor": "user", "at": ago(days=4)},
        ]
    },
    {
        "first": "Ben", "last": "Carlisle",
        "email": "bcarlisle@hotmail.com", "phone": "+13125554455",
        "status": "new", "lead_type": "buyer", "score": 0.61,
        "source": SRC_WEBFORM, "agent": None,
        "prefs": {"budget_min": 450000, "budget_max": 600000, "city": "Chicago", "state": "IL",
                  "types": ["condo"], "timeline": "6_months", "financing": "pre_approved"},
        "created": ago(hours=30),
        "events": [
            {"type": "lead.created", "data": {"source": "web_form"}, "actor": "system", "at": ago(hours=30)},
            {"type": "lead.scored", "data": {"score": 0.61, "tier": "warm"}, "actor": "system", "at": ago(hours=30, minutes=1)},
        ]
    },
    {
        "first": "Fatima", "last": "Al-Rashid",
        "email": "fatima.alr@gmail.com", "phone": "+14695553399",
        "status": "contacted", "lead_type": "buyer", "score": 0.79,
        "source": SRC_ZILLOW, "agent": "30000000-0000-0000-0000-000000000002",
        "prefs": {"budget_min": 800000, "budget_max": 1200000, "city": "Dallas", "state": "TX",
                  "types": ["single_family"], "timeline": "3_months", "financing": "cash"},
        "created": ago(days=4),
        "events": [
            {"type": "lead.created", "data": {"source": "zillow_inquiry"}, "actor": "system", "at": ago(days=4)},
            {"type": "lead.scored", "data": {"score": 0.79, "tier": "hot"}, "actor": "system", "at": ago(days=4, minutes=1)},
            {"type": "lead.assigned", "data": {"agent_name": "Michael Torres"}, "actor": "user", "at": ago(days=4)},
            {"type": "sms.sent", "data": {"message": "Hello Fatima, I'd love to show you some of our newest listings in Preston Hollow."}, "actor": "user", "at": ago(days=3, hours=22)},
        ]
    },
    {
        "first": "Tyler", "last": "Brooks",
        "email": "tylerb2024@icloud.com", "phone": "+13035558877",
        "status": "converted", "lead_type": "buyer", "score": 0.93,
        "source": SRC_WEBFORM, "agent": "30000000-0000-0000-0000-000000000004",
        "prefs": {"budget_min": 1500000, "budget_max": 2200000, "city": "Denver", "state": "CO",
                  "types": ["single_family"], "timeline": "immediate", "financing": "pre_approved"},
        "created": ago(days=60),
        "events": [
            {"type": "lead.created", "data": {"source": "web_form"}, "actor": "system", "at": ago(days=60)},
            {"type": "lead.scored", "data": {"score": 0.93, "tier": "hot"}, "actor": "system", "at": ago(days=60, minutes=1)},
            {"type": "lead.assigned", "data": {"agent_name": "Alex Johnson"}, "actor": "user", "at": ago(days=60)},
            {"type": "note.added", "data": {"text": "Closing scheduled for March 15. Commission $52,000."}, "actor": "user", "at": ago(days=20)},
            {"type": "lead.status_changed", "data": {"from": "qualified", "to": "converted"}, "actor": "user", "at": ago(days=20)},
        ]
    },
    {
        "first": "Mei", "last": "Zhang",
        "email": "mei.zhang88@gmail.com", "phone": "+14085551188",
        "status": "new", "lead_type": "buyer", "score": 0.58,
        "source": SRC_ZILLOW, "agent": None,
        "prefs": {"budget_min": 900000, "budget_max": 1400000, "city": "Cupertino", "state": "CA",
                  "types": ["single_family"], "timeline": "6_months", "financing": "mortgage"},
        "created": ago(hours=4),
        "events": [
            {"type": "lead.created", "data": {"source": "zillow_inquiry"}, "actor": "system", "at": ago(hours=4)},
            {"type": "lead.scored", "data": {"score": 0.58, "tier": "warm"}, "actor": "system", "at": ago(hours=4, minutes=1)},
        ]
    },
    {
        "first": "Jordan", "last": "Mitchell",
        "email": "jordan.m@gmail.com", "phone": "+16175552233",
        "status": "lost", "lead_type": "seller", "score": 0.28,
        "source": SRC_HUBSPOT, "agent": "30000000-0000-0000-0000-000000000003",
        "prefs": {"budget_min": None, "budget_max": None, "city": "Boston", "state": "MA",
                  "types": ["condo"], "timeline": "flexible", "financing": None},
        "created": ago(days=90),
        "events": [
            {"type": "lead.created", "data": {"source": "hubspot_sync"}, "actor": "system", "at": ago(days=90)},
            {"type": "lead.assigned", "data": {"agent_name": "Priya Nair"}, "actor": "user", "at": ago(days=89)},
            {"type": "note.added", "data": {"text": "Owner decided not to sell. Will reconnect in 6 months."}, "actor": "user", "at": ago(days=75)},
            {"type": "lead.status_changed", "data": {"from": "contacted", "to": "lost"}, "actor": "user", "at": ago(days=75)},
        ]
    },
]


async def seed(db: asyncpg.Connection) -> None:
    # ── Wipe existing demo data ───────────────────────────────────────────────
    print("Clearing existing demo data...")
    await db.execute("DELETE FROM activity_timeline WHERE tenant_id = $1", TENANT_ID)
    await db.execute("DELETE FROM lead_preferences WHERE tenant_id = $1", TENANT_ID)
    await db.execute("DELETE FROM leads WHERE tenant_id = $1", TENANT_ID)
    await db.execute("DELETE FROM contacts WHERE tenant_id = $1", TENANT_ID)
    # Remove demo agents (not the migration-seeded dev user)
    for agent in AGENTS:
        await db.execute(
            "DELETE FROM tenant_memberships WHERE user_id = $1 AND tenant_id = $2",
            agent["id"], TENANT_ID,
        )
        await db.execute("DELETE FROM users WHERE id = $1 AND id != $2", agent["id"], DEV_USER_ID)

    # ── Agents ────────────────────────────────────────────────────────────────
    print("Seeding agents...")
    for agent in AGENTS:
        await db.execute("""
            INSERT INTO users (id, auth0_sub, email, name, is_active)
            VALUES ($1, $2, $3, $4, true)
            ON CONFLICT (auth0_sub) DO NOTHING
        """, agent["id"], agent["sub"], agent["email"], agent["name"])

        mem_id = str(uuid.uuid4())
        await db.execute("""
            INSERT INTO tenant_memberships (id, user_id, tenant_id, role_slug, is_active, joined_at)
            VALUES ($1, $2, $3, $4, true, now())
            ON CONFLICT (user_id, tenant_id) DO NOTHING
        """, mem_id, agent["id"], TENANT_ID, agent["role"])

    print(f"  {len(AGENTS)} agents seeded")

    # ── Leads ─────────────────────────────────────────────────────────────────
    print("Seeding leads...")
    for lead_data in LEADS:
        contact_id = uid()
        lead_id = uid()

        # Contact
        await db.execute("""
            INSERT INTO contacts (id, tenant_id, first_name, last_name)
            VALUES ($1, $2, $3, $4)
        """, contact_id, TENANT_ID, lead_data["first"], lead_data["last"])

        # Email contact point
        await db.execute("""
            INSERT INTO contact_points (id, contact_id, tenant_id, type, value_raw, value_normalized, is_primary, is_verified)
            VALUES ($1, $2, $3, 'email', $4, $4, true, true)
        """, uid(), contact_id, TENANT_ID, lead_data["email"])

        # Phone contact point
        if lead_data.get("phone"):
            await db.execute("""
                INSERT INTO contact_points (id, contact_id, tenant_id, type, value_raw, value_normalized, is_primary, is_verified)
                VALUES ($1, $2, $3, 'phone', $4, $4, true, false)
            """, uid(), contact_id, TENANT_ID, lead_data["phone"])

        # Lead
        await db.execute("""
            INSERT INTO leads (
                id, tenant_id, contact_id, source_id, status, lead_type,
                confidence_score, assigned_agent_id, last_activity_at, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10)
        """,
            lead_id, TENANT_ID, contact_id, lead_data["source"],
            lead_data["status"], lead_data["lead_type"],
            lead_data.get("score"),
            lead_data.get("agent"),
            lead_data["created"],
            lead_data["created"],
        )

        # Preferences
        prefs = lead_data.get("prefs", {})
        if prefs:
            await db.execute("""
                INSERT INTO lead_preferences (
                    id, lead_id, tenant_id,
                    budget_min, budget_max, location_city, location_state,
                    property_types, timeline, financing_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                uid(), lead_id, TENANT_ID,
                prefs.get("budget_min"), prefs.get("budget_max"),
                prefs.get("city"), prefs.get("state"),
                json.dumps(prefs.get("types")) if prefs.get("types") is not None else None,
                prefs.get("timeline"),
                prefs.get("financing"),
            )

        # Timeline events
        for evt in lead_data.get("events", []):
            await db.execute("""
                INSERT INTO activity_timeline (id, tenant_id, lead_id, event_type, event_data, actor_type, occurred_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                uid(), TENANT_ID, lead_id,
                evt["type"], json.dumps(evt["data"]),
                evt["actor"], evt["at"],
            )

        # Update last_activity_at to most recent event
        if lead_data.get("events"):
            latest = max(e["at"] for e in lead_data["events"])
            await db.execute(
                "UPDATE leads SET last_activity_at = $1 WHERE id = $2",
                latest, lead_id
            )

        name = f"{lead_data['first']} {lead_data['last']}"
        print(f"  + {name} ({lead_data['status']}, score={lead_data.get('score', 'n/a')})")

    print(f"\nDone! Seeded {len(AGENTS)} agents + {len(LEADS)} leads.")


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await seed(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
