export type ApiLeadStatus = "new" | "contacted" | "qualified" | "converted" | "lost";

export interface ContactSummary {
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
}

export interface SourceSummary {
  id: string;
  name: string;
  source_type: string;
}

export interface Lead {
  id: string;
  tenant_id: string;
  status: ApiLeadStatus;
  confidence_score: number | null; // 0.0–1.0
  contact: ContactSummary;
  source: SourceSummary | null;
  assigned_agent_id: string | null;
  last_activity_at: string | null;
  created_at: string;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
}
