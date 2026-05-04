import { MOCK_LEADS } from "@/lib/mock-leads";
import { LeadsTable } from "@/components/leads/leads-table";

export const metadata = { title: "Leads — DealFlow AI" };

export default function LeadsPage() {
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Leads</h1>
          <p className="text-sm text-gray-500 mt-0.5">Track and manage your inbound prospects</p>
        </div>
      </div>

      <LeadsTable leads={MOCK_LEADS} />
    </div>
  );
}
