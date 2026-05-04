import type { MockLead } from "@/lib/mock-leads";

interface LeadPreferencesProps {
  preferences: MockLead["preferences"];
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

function formatBudget(min: number, max: number) {
  const fmt = (n: number) =>
    n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : `$${(n / 1000).toFixed(0)}k`;
  return `${fmt(min)} – ${fmt(max)}`;
}

export function LeadPreferences({ preferences }: LeadPreferencesProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Preferences</h2>
      <dl className="space-y-2.5">
        <div>
          <dt className="text-xs text-gray-500 mb-1">Budget</dt>
          <dd className="text-sm font-medium text-gray-900">
            {formatBudget(preferences.budget_min, preferences.budget_max)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500 mb-1">Locations</dt>
          <dd className="flex flex-wrap gap-1">
            {preferences.locations.map((loc) => (
              <span key={loc} className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                {loc}
              </span>
            ))}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500 mb-1">Property types</dt>
          <dd className="flex flex-wrap gap-1">
            {preferences.property_types.map((pt) => (
              <span key={pt} className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
                {PROPERTY_LABELS[pt] ?? pt}
              </span>
            ))}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500 mb-1">Financing</dt>
          <dd className="text-sm text-gray-900">
            {FINANCING_LABELS[preferences.financing_status] ?? preferences.financing_status}
          </dd>
        </div>
      </dl>
    </div>
  );
}
