"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { UserCircle, ChevronRight } from "lucide-react";
import { StatusBadge } from "@/components/leads/status-badge";
import { ScoreBadge } from "@/components/leads/score-badge";
import { LeadsFilters } from "@/components/leads/leads-filters";
import { type MockLead, type LeadStatus } from "@/lib/mock-leads";
import { cn } from "@/lib/cn";

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatBudget(min: number, max: number) {
  const fmt = (n: number) =>
    n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : `$${(n / 1000).toFixed(0)}k`;
  return `${fmt(min)} – ${fmt(max)}`;
}

interface LeadsTableProps {
  leads: MockLead[];
}

export function LeadsTable({ leads: allLeads }: LeadsTableProps) {
  const [search, setSearch] = useState("");
  const [activeStatus, setActiveStatus] = useState<LeadStatus | "all">("all");

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: allLeads.length };
    for (const l of allLeads) {
      c[l.status] = (c[l.status] ?? 0) + 1;
    }
    return c;
  }, [allLeads]);

  const filtered = useMemo(() => {
    let list = allLeads;
    if (activeStatus !== "all") list = list.filter((l) => l.status === activeStatus);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (l) =>
          `${l.contact.first_name} ${l.contact.last_name}`.toLowerCase().includes(q) ||
          l.contact.email.toLowerCase().includes(q)
      );
    }
    return list;
  }, [allLeads, activeStatus, search]);

  return (
    <div className="space-y-4">
      <LeadsFilters
        search={search}
        onSearchChange={setSearch}
        activeStatus={activeStatus}
        onStatusChange={setActiveStatus}
        counts={counts}
      />

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 bg-white p-12 text-center">
          <p className="text-sm font-medium text-gray-900">No leads found</p>
          <p className="text-xs text-gray-500 mt-1">Try adjusting your search or filter.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Contact</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                <th className="hidden md:table-cell px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Budget</th>
                <th className="hidden lg:table-cell px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                <th className="hidden lg:table-cell px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Agent</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Activity</th>
                <th className="px-4 py-3 w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((lead) => (
                <tr
                  key={lead.id}
                  className="group hover:bg-gray-50/60 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3.5">
                    <Link href={`/leads/${lead.id}`} className="flex items-center gap-3">
                      <div className={cn(
                        "h-8 w-8 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 text-white",
                        ["bg-indigo-500","bg-violet-500","bg-blue-500","bg-emerald-500","bg-rose-500"]
                          [lead.contact.first_name.charCodeAt(0) % 5]
                      )}>
                        {lead.contact.first_name[0]}{lead.contact.last_name[0]}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {lead.contact.first_name} {lead.contact.last_name}
                        </p>
                        <p className="text-xs text-gray-500 truncate">{lead.contact.email}</p>
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
                      <ScoreBadge score={lead.score} />
                    </Link>
                  </td>
                  <td className="hidden md:table-cell px-4 py-3.5 text-sm text-gray-600">
                    <Link href={`/leads/${lead.id}`}>
                      {formatBudget(lead.preferences.budget_min, lead.preferences.budget_max)}
                    </Link>
                  </td>
                  <td className="hidden lg:table-cell px-4 py-3.5 text-sm text-gray-600">
                    <Link href={`/leads/${lead.id}`}>{lead.source.name}</Link>
                  </td>
                  <td className="hidden lg:table-cell px-4 py-3.5">
                    <Link href={`/leads/${lead.id}`}>
                      {lead.assigned_agent ? (
                        <span className="flex items-center gap-1.5 text-sm text-gray-700">
                          <UserCircle className="w-4 h-4 text-gray-400 shrink-0" />
                          {lead.assigned_agent.name}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400 italic">Unassigned</span>
                      )}
                    </Link>
                  </td>
                  <td className="px-4 py-3.5 text-xs text-gray-400">
                    <Link href={`/leads/${lead.id}`}>{relativeTime(lead.last_activity_at)}</Link>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <Link href={`/leads/${lead.id}`}>
                      <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-400 text-right">
        Showing {filtered.length} of {allLeads.length} leads
      </p>
    </div>
  );
}
