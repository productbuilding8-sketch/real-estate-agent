export type LeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "proposal"
  | "closed_won"
  | "closed_lost"
  | "disqualified";

export type MockLead = {
  id: string;
  contact: {
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
  };
  source: { name: string; type: string };
  status: LeadStatus;
  score: number | null;
  assigned_agent: { name: string } | null;
  last_activity_at: string;
  created_at: string;
  preferences: {
    budget_min: number;
    budget_max: number;
    property_types: string[];
    financing_status: string;
    locations: string[];
  };
};

export type TimelineEvent = {
  id: string;
  event_type: string;
  event_data: Record<string, string>;
  actor_name: string;
  occurred_at: string;
};

export const MOCK_LEADS: MockLead[] = [
  {
    id: "lead-001",
    contact: { first_name: "Jennifer", last_name: "Walsh", email: "j.walsh@email.com", phone: "+1 (555) 234-5678" },
    source: { name: "Zillow", type: "webhook" },
    status: "qualified",
    score: 91,
    assigned_agent: { name: "Demo Agent" },
    last_activity_at: "2026-05-03T10:15:00Z",
    created_at: "2026-05-01T09:00:00Z",
    preferences: { budget_min: 450000, budget_max: 650000, property_types: ["single_family"], financing_status: "pre_approved", locations: ["Austin, TX"] },
  },
  {
    id: "lead-002",
    contact: { first_name: "Marcus", last_name: "Rivera", email: "m.rivera@gmail.com", phone: "+1 (555) 876-5432" },
    source: { name: "HubSpot", type: "crm" },
    status: "new",
    score: 62,
    assigned_agent: null,
    last_activity_at: "2026-05-03T08:45:00Z",
    created_at: "2026-05-03T08:40:00Z",
    preferences: { budget_min: 300000, budget_max: 420000, property_types: ["condo", "townhouse"], financing_status: "exploring", locations: ["Denver, CO"] },
  },
  {
    id: "lead-003",
    contact: { first_name: "Priya", last_name: "Kapoor", email: "priya.k@outlook.com", phone: "+1 (555) 456-7890" },
    source: { name: "Website Form", type: "manual" },
    status: "contacted",
    score: 74,
    assigned_agent: { name: "Sarah Chen" },
    last_activity_at: "2026-05-02T16:30:00Z",
    created_at: "2026-04-30T14:00:00Z",
    preferences: { budget_min: 550000, budget_max: 800000, property_types: ["single_family"], financing_status: "pre_approved", locations: ["Seattle, WA"] },
  },
  {
    id: "lead-004",
    contact: { first_name: "David", last_name: "Kim", email: "dkim@company.com", phone: "+1 (555) 321-0987" },
    source: { name: "Zillow", type: "webhook" },
    status: "proposal",
    score: 88,
    assigned_agent: { name: "Demo Agent" },
    last_activity_at: "2026-05-02T11:00:00Z",
    created_at: "2026-04-28T10:00:00Z",
    preferences: { budget_min: 700000, budget_max: 950000, property_types: ["single_family", "luxury"], financing_status: "cash", locations: ["Austin, TX"] },
  },
  {
    id: "lead-005",
    contact: { first_name: "Aaliya", last_name: "Hassan", email: "aaliya.h@email.com", phone: "+1 (555) 654-3210" },
    source: { name: "Referral", type: "manual" },
    status: "new",
    score: null,
    assigned_agent: null,
    last_activity_at: "2026-05-03T07:20:00Z",
    created_at: "2026-05-03T07:20:00Z",
    preferences: { budget_min: 200000, budget_max: 320000, property_types: ["condo"], financing_status: "pre_approved", locations: ["Phoenix, AZ"] },
  },
  {
    id: "lead-006",
    contact: { first_name: "Tom", last_name: "Brandt", email: "t.brandt@email.com", phone: "+1 (555) 789-0123" },
    source: { name: "HubSpot", type: "crm" },
    status: "disqualified",
    score: 18,
    assigned_agent: { name: "Michael Torres" },
    last_activity_at: "2026-05-01T09:00:00Z",
    created_at: "2026-04-25T12:00:00Z",
    preferences: { budget_min: 100000, budget_max: 150000, property_types: ["condo"], financing_status: "exploring", locations: ["Dallas, TX"] },
  },
  {
    id: "lead-007",
    contact: { first_name: "Rachel", last_name: "Nguyen", email: "r.nguyen@gmail.com", phone: "+1 (555) 111-2222" },
    source: { name: "Zillow", type: "webhook" },
    status: "closed_won",
    score: 95,
    assigned_agent: { name: "Demo Agent" },
    last_activity_at: "2026-04-29T15:00:00Z",
    created_at: "2026-04-10T08:00:00Z",
    preferences: { budget_min: 480000, budget_max: 580000, property_types: ["single_family"], financing_status: "pre_approved", locations: ["Austin, TX"] },
  },
];

export const MOCK_TIMELINE: Record<string, TimelineEvent[]> = {
  "lead-001": [
    { id: "tl-1", event_type: "lead.created", event_data: { source: "Zillow" }, actor_name: "System", occurred_at: "2026-05-01T09:00:00Z" },
    { id: "tl-2", event_type: "score.updated", event_data: { score: "91", model: "gpt-4o" }, actor_name: "AI", occurred_at: "2026-05-01T09:01:00Z" },
    { id: "tl-3", event_type: "lead.assigned", event_data: { agent: "Demo Agent" }, actor_name: "System", occurred_at: "2026-05-01T09:02:00Z" },
    { id: "tl-4", event_type: "message.sent", event_data: { channel: "sms", preview: "Hi Jennifer, this is Demo from..." }, actor_name: "Demo Agent", occurred_at: "2026-05-01T10:00:00Z" },
    { id: "tl-5", event_type: "status.changed", event_data: { from: "new", to: "contacted" }, actor_name: "Demo Agent", occurred_at: "2026-05-01T10:01:00Z" },
    { id: "tl-6", event_type: "note.added", event_data: { note: "Spoke on the phone. Very motivated buyer, pre-approved for $620k." }, actor_name: "Demo Agent", occurred_at: "2026-05-02T14:30:00Z" },
    { id: "tl-7", event_type: "status.changed", event_data: { from: "contacted", to: "qualified" }, actor_name: "Demo Agent", occurred_at: "2026-05-02T14:31:00Z" },
    { id: "tl-8", event_type: "appointment.scheduled", event_data: { date: "May 7, 2026", type: "Property showing" }, actor_name: "Demo Agent", occurred_at: "2026-05-03T10:15:00Z" },
  ],
};
