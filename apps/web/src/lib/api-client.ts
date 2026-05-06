import type { Lead, LeadListResponse, ApiLeadStatus } from "@/types/leads";
import { MOCK_LEADS, type LeadStatus as MockLeadStatus } from "@/lib/mock-leads";

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
  confidence_score: m.score !== null ? m.score / 100 : null,
  contact: {
    first_name: m.contact.first_name,
    last_name: m.contact.last_name,
    email: m.contact.email,
    phone: m.contact.phone,
  },
  source: { id: "mock-src", name: m.source.name, source_type: m.source.type },
  assigned_agent_id: m.assigned_agent ? "mock-agent" : null,
  last_activity_at: m.last_activity_at,
  created_at: m.created_at,
}));

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
        `${l.contact.first_name} ${l.contact.last_name}`.toLowerCase().includes(q) ||
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

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<LeadListResponse>;
}
