import { getLeads } from "@/lib/api-client";
import { LeadsTable } from "@/components/leads/leads-table";

export const metadata = { title: "Leads — DealFlow AI" };

interface Props {
  searchParams: Promise<{ q?: string; status?: string; page?: string }>;
}

export default async function LeadsPage({ searchParams }: Props) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? 1));
  const { items, total, page_size, status_counts } = await getLeads({
    search: params.q,
    status: params.status !== "all" ? params.status : undefined,
    page,
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 tracking-tight">Leads</h1>
        <p className="text-sm text-gray-500 mt-0.5">Track and manage your inbound prospects</p>
      </div>

      <LeadsTable leads={items} total={total} page={page} pageSize={page_size} statusCounts={status_counts} />
    </div>
  );
}
