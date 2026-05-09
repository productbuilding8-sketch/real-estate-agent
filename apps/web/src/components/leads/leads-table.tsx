import Link from "next/link";
import { UserCircle, ChevronRight } from "lucide-react";
import { StatusBadge } from "@/components/leads/status-badge";
import { ScoreBadge } from "@/components/leads/score-badge";
import { LeadsFilters } from "@/components/leads/leads-filters";
import { LeadsPagination } from "@/components/leads/leads-pagination";
import type { Lead } from "@/types/leads";
import { cn } from "@/lib/cn";

const AVATAR_PALETTE = [
  "bg-indigo-500",
  "bg-violet-500",
  "bg-blue-500",
  "bg-emerald-500",
  "bg-rose-500",
];

function initials(fullName: string | null): string {
  const parts = (fullName ?? "?").trim().split(/\s+/);
  if (parts.length >= 2) return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  return (parts[0]?.[0] ?? "?").toUpperCase();
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

interface LeadsTableProps {
  leads: Lead[];
  total: number;
  page: number;
  pageSize: number;
  statusCounts: Record<string, number>;
}

const TH = "px-4 py-3 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider";

export function LeadsTable({ leads, total, page, pageSize, statusCounts }: LeadsTableProps) {
  const allTotal = Object.values(statusCounts).reduce((s, n) => s + n, 0);
  const counts: Record<string, number> = { all: allTotal, ...statusCounts };

  return (
    <div className="space-y-4">
      <LeadsFilters counts={counts} />

      {leads.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 bg-white p-16 text-center shadow-card">
          <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-3">
            <UserCircle className="w-5 h-5 text-gray-400" />
          </div>
          <p className="text-sm font-medium text-gray-700">No leads found</p>
          <p className="text-xs text-gray-400 mt-1">Try adjusting your search or filter.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white shadow-card overflow-hidden">
          <table className="min-w-full divide-y divide-gray-100">
            <thead>
              <tr className="bg-gray-50/80">
                <th className={TH}>Contact</th>
                <th className={TH}>Status</th>
                <th className={TH}>Score</th>
                <th className={cn(TH, "hidden lg:table-cell")}>Source</th>
                <th className={cn(TH, "hidden lg:table-cell")}>Agent</th>
                <th className={TH}>Activity</th>
                <th className="px-4 py-3 w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100/80">
              {leads.map((lead) => {
                const score =
                  lead.confidence_score !== null
                    ? Math.round(lead.confidence_score * 100)
                    : null;
                const avatarColor =
                  AVATAR_PALETTE[(lead.contact.full_name?.charCodeAt(0) ?? 0) % AVATAR_PALETTE.length];

                return (
                  <tr
                    key={lead.id}
                    className="group hover:bg-indigo-50/30 transition-colors duration-100 cursor-pointer"
                  >
                    <td className="px-4 py-3.5">
                      <Link href={`/leads/${lead.id}`} className="flex items-center gap-3">
                        <div
                          className={cn(
                            "h-8 w-8 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 text-white",
                            avatarColor,
                          )}
                        >
                          {initials(lead.contact.full_name)}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate leading-tight">
                            {lead.contact.full_name ?? "—"}
                          </p>
                          <p className="text-xs text-gray-400 truncate mt-0.5">{lead.contact.email}</p>
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-3.5">
                      <Link href={`/leads/${lead.id}`}>
                        <StatusBadge status={lead.status} />
                      </Link>
                    </td>
                    <td className="px-4 py-3.5">
                      <Link href={`/leads/${lead.id}`}>
                        <ScoreBadge score={score} />
                      </Link>
                    </td>
                    <td className="hidden lg:table-cell px-4 py-3.5">
                      <Link href={`/leads/${lead.id}`}>
                        <span className="text-sm text-gray-600">{lead.source?.name ?? "—"}</span>
                      </Link>
                    </td>
                    <td className="hidden lg:table-cell px-4 py-3.5">
                      <Link href={`/leads/${lead.id}`}>
                        {lead.assigned_agent_name ? (
                          <span className="flex items-center gap-1.5 text-sm text-gray-700">
                            <UserCircle className="w-4 h-4 text-gray-300 shrink-0" />
                            {lead.assigned_agent_name}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400 italic">Unassigned</span>
                        )}
                      </Link>
                    </td>
                    <td className="px-4 py-3.5">
                      <Link href={`/leads/${lead.id}`}>
                        <span className="text-xs text-gray-400 tabular-nums">
                          {lead.last_activity_at ? relativeTime(lead.last_activity_at) : "—"}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <Link href={`/leads/${lead.id}`}>
                        <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-indigo-400 transition-colors" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <LeadsPagination page={page} pageSize={pageSize} total={total} />
    </div>
  );
}
