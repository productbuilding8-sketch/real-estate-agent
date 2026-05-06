import type { LeadPreferences } from "@/types/leads";

interface LeadPreferencesProps {
  preferences: LeadPreferences;
}

const FINANCING_LABELS: Record<string, string> = {
  pre_approved: "Pre-approved",
  exploring: "Exploring options",
  cash: "Cash buyer",
  not_started: "Not started",
};

const PROPERTY_LABELS: Record<string, string> = {
  single_family: "Single family",
  condo: "Condo",
  townhouse: "Townhouse",
  luxury: "Luxury",
  multi_family: "Multi-family",
};

function formatBudget(min: number | null, max: number | null): string | null {
  if (min === null && max === null) return null;
  const fmt = (n: number) =>
    n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : `$${(n / 1000).toFixed(0)}k`;
  if (min !== null && max !== null) return `${fmt(min)} – ${fmt(max)}`;
  if (min !== null) return `From ${fmt(min)}`;
  return `Up to ${fmt(max!)}`;
}

export function LeadPreferences({ preferences: p }: LeadPreferencesProps) {
  const budget = formatBudget(p.budget_min, p.budget_max);
  const location =
    p.location_city && p.location_state
      ? `${p.location_city}, ${p.location_state}`
      : (p.location_city ?? p.location_state ?? null);
  const hasContent =
    budget || location || p.property_types?.length || p.financing_status || p.purpose || p.timeline;

  if (!hasContent) return null;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Preferences</h2>
      <dl className="space-y-2.5">
        {budget && (
          <div>
            <dt className="text-xs text-gray-500 mb-1">Budget</dt>
            <dd className="text-sm font-medium text-gray-900">{budget}</dd>
          </div>
        )}
        {location && (
          <div>
            <dt className="text-xs text-gray-500 mb-1">Location</dt>
            <dd className="text-sm text-gray-900">{location}</dd>
          </div>
        )}
        {p.property_types && p.property_types.length > 0 && (
          <div>
            <dt className="text-xs text-gray-500 mb-1">Property types</dt>
            <dd className="flex flex-wrap gap-1">
              {p.property_types.map((pt) => (
                <span
                  key={pt}
                  className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700"
                >
                  {PROPERTY_LABELS[pt] ?? pt}
                </span>
              ))}
            </dd>
          </div>
        )}
        {p.financing_status && (
          <div>
            <dt className="text-xs text-gray-500 mb-1">Financing</dt>
            <dd className="text-sm text-gray-900">
              {FINANCING_LABELS[p.financing_status] ?? p.financing_status}
            </dd>
          </div>
        )}
        {p.purpose && (
          <div>
            <dt className="text-xs text-gray-500 mb-1">Purpose</dt>
            <dd className="text-sm text-gray-900 capitalize">{p.purpose}</dd>
          </div>
        )}
        {p.timeline && (
          <div>
            <dt className="text-xs text-gray-500 mb-1">Timeline</dt>
            <dd className="text-sm text-gray-900">{p.timeline}</dd>
          </div>
        )}
        {p.appointment_preferred !== null && p.appointment_preferred !== undefined && (
          <div>
            <dt className="text-xs text-gray-500 mb-1">Appointment</dt>
            <dd className="text-sm text-gray-900">
              {p.appointment_preferred ? "Prefers appointment" : "No preference"}
            </dd>
          </div>
        )}
      </dl>
    </div>
  );
}
