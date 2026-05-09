export type ApiLeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "converted"
  | "lost"
  | "archived";

export interface ContactPoint {
  type: string;
  value: string;
  is_primary: boolean;
}

export interface ContactSummary {
  id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
}

export interface ContactDetail extends ContactSummary {
  contact_points: ContactPoint[];
}

export interface SourceSummary {
  id: string;
  name: string;
  type: string;
}

export interface LeadPreferences {
  budget_min: number | null;
  budget_max: number | null;
  location_city: string | null;
  location_state: string | null;
  property_types: string[] | null;
  timeline: string | null;
  financing_status: string | null;
  purpose: string | null;
  appointment_preferred: boolean | null;
}

export interface TimelineEvent {
  id: string;
  event_type: string;
  event_data: Record<string, unknown> | null;
  actor_type: string;
  occurred_at: string;
}

export interface Lead {
  id: string;
  tenant_id: string;
  status: ApiLeadStatus;
  lead_type: string;
  confidence_score: number | null;
  contact: ContactSummary;
  source: SourceSummary;
  assigned_agent_id: string | null;
  assigned_agent_name: string | null;
  last_activity_at: string | null;
  created_at: string;
}

export interface LeadDetail extends Omit<Lead, "contact"> {
  contact: ContactDetail;
  first_response_at: string | null;
  stale_at: string | null;
  preferences: LeadPreferences | null;
  timeline: TimelineEvent[];
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
  status_counts: Record<string, number>;
}
