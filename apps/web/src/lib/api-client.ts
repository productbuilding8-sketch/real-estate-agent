import type {
  Lead,
  LeadDetail,
  LeadListResponse,
  ApiLeadStatus,
  TimelineEvent,
} from "@/types/leads";
import { MOCK_LEADS, MOCK_TIMELINE, type LeadStatus as MockLeadStatus } from "@/lib/mock-leads";

const MOCK_STATUS_MAP: Record<MockLeadStatus, ApiLeadStatus> = {
  new: "new",
  contacted: "contacted",
  qualified: "qualified",
  proposal: "qualified",
  closed_won: "converted",
  closed_lost: "lost",
  disqualified: "lost",
};

const MOCK_API_LEADS: Lead[] = MOCK_LEADS.map((m) => ({
  id: m.id,
  tenant_id: "mock-tenant",
  status: MOCK_STATUS_MAP[m.status],
  lead_type: "buyer",
  confidence_score: m.score !== null ? m.score / 100 : null,
  contact: {
    id: `contact-${m.id}`,
    full_name: `${m.contact.first_name} ${m.contact.last_name}`,
    email: m.contact.email,
    phone: m.contact.phone,
  },
  source: { id: "mock-src", name: m.source.name, type: m.source.type },
  assigned_agent_id: m.assigned_agent ? "mock-agent" : null,
  last_activity_at: m.last_activity_at,
  created_at: m.created_at,
}));

// ── List ──────────────────────────────────────────────────────────────────────

export interface GetLeadsParams {
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

const PAGE_SIZE = 25;

export async function getLeads(params: GetLeadsParams = {}): Promise<LeadListResponse> {
  if (process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL) {
    return getMockLeads(params);
  }
  return fetchLeads(params);
}

function getMockLeads({
  search,
  status,
  page = 1,
  page_size = PAGE_SIZE,
}: GetLeadsParams): LeadListResponse {
  let items = MOCK_API_LEADS;
  if (status && status !== "all") {
    items = items.filter((l) => l.status === status);
  }
  if (search?.trim()) {
    const q = search.toLowerCase();
    items = items.filter(
      (l) =>
        (l.contact.full_name?.toLowerCase().includes(q) ?? false) ||
        (l.contact.email?.toLowerCase().includes(q) ?? false),
    );
  }
  const total = items.length;
  const offset = (page - 1) * page_size;
  return { items: items.slice(offset, offset + page_size), total, page, page_size };
}

async function fetchLeads({
  search,
  status,
  page = 1,
  page_size = PAGE_SIZE,
}: GetLeadsParams): Promise<LeadListResponse> {
  const url = new URL(`${process.env.INTERNAL_API_URL}/api/v1/leads`);
  if (search) url.searchParams.set("search", search);
  if (status && status !== "all") url.searchParams.set("status", status);
  url.searchParams.set("page", String(page));
  url.searchParams.set("page_size", String(page_size));

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  const data = (await res.json()) as { items: Lead[]; total: number; page: number };
  return { items: data.items, total: data.total, page: data.page, page_size };
}

// ── Detail ────────────────────────────────────────────────────────────────────

export async function getLead(id: string): Promise<LeadDetail | null> {
  if (process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL) {
    return getMockLead(id);
  }
  return fetchLead(id);
}

function getMockLead(id: string): LeadDetail | null {
  const m = MOCK_LEADS.find((l) => l.id === id);
  if (!m) return null;

  const [city, state] = (m.preferences.locations[0] ?? "").split(",").map((s) => s.trim());
  const mockEvents = MOCK_TIMELINE[id] ?? [];

  const timeline: TimelineEvent[] = mockEvents.map((e) => ({
    id: e.id,
    event_type: e.event_type,
    event_data: e.event_data as Record<string, unknown>,
    actor_type: e.actor_name === "System" || e.actor_name === "AI" ? "system" : "user",
    occurred_at: e.occurred_at,
  }));

  return {
    id: m.id,
    tenant_id: "mock-tenant",
    status: MOCK_STATUS_MAP[m.status],
    lead_type: "buyer",
    confidence_score: m.score !== null ? m.score / 100 : null,
    contact: {
      id: `contact-${m.id}`,
      full_name: `${m.contact.first_name} ${m.contact.last_name}`,
      email: m.contact.email,
      phone: m.contact.phone,
      contact_points: [
        { type: "email", value: m.contact.email, is_primary: true },
        { type: "phone", value: m.contact.phone, is_primary: true },
      ],
    },
    source: { id: "mock-src", name: m.source.name, type: m.source.type },
    assigned_agent_id: m.assigned_agent ? "mock-agent" : null,
    last_activity_at: m.last_activity_at,
    created_at: m.created_at,
    first_response_at: null,
    stale_at: null,
    preferences: {
      budget_min: m.preferences.budget_min,
      budget_max: m.preferences.budget_max,
      location_city: city ?? null,
      location_state: state ?? null,
      property_types: m.preferences.property_types,
      financing_status: m.preferences.financing_status,
      timeline: null,
      purpose: null,
      appointment_preferred: null,
    },
    timeline,
  };
}

async function fetchLead(id: string): Promise<LeadDetail | null> {
  const res = await fetch(`${process.env.INTERNAL_API_URL}/api/v1/leads/${id}`, {
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<LeadDetail>;
}
