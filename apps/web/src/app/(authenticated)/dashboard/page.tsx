import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { Users, TrendingUp, ArrowUpRight, Activity, Sparkles } from "lucide-react";
import { getSession } from "@/lib/auth";
import { getDashboardMetrics } from "@/lib/api-client";
import { StatusBadge } from "@/components/leads/status-badge";

export const metadata: Metadata = { title: "Dashboard — DealFlow AI" };

const EVENT_LABELS: Record<string, string> = {
  "lead.created":       "New lead ingested",
  "lead.status_changed":"Status changed",
  "lead.assigned":      "Lead assigned",
  "lead.unassigned":    "Lead unassigned",
  "lead.note_added":    "Note added",
  "score.updated":      "Score updated",
};

const EVENT_COLORS: Record<string, string> = {
  "lead.created":       "bg-blue-500",
  "lead.status_changed":"bg-amber-500",
  "lead.assigned":      "bg-indigo-500",
  "score.updated":      "bg-purple-500",
  "lead.note_added":    "bg-yellow-400",
};

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default async function DashboardPage() {
  const [session, metrics] = await Promise.all([
    getSession(),
    getDashboardMetrics().catch(() => null),
  ]);

  const firstName = session?.user?.name?.split(" ")[0] ?? "there";
  const total = metrics?.total_leads ?? 0;
  const convRate = metrics ? `${Math.round(metrics.conversion_rate * 100)}%` : "—";
  const pipelineTotal = metrics?.by_status.reduce((s, r) => s + r.count, 0) ?? 0;

  const STATUS_ORDER = ["new", "contacted", "qualified", "converted", "lost", "archived"];

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      {/* Welcome */}
      <div>
        <h1 className="text-xl font-semibold text-gray-900 tracking-tight">
          Good morning, {firstName}
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Here&apos;s what&apos;s happening with your leads today.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Total Leads"
          value={total > 0 ? String(total) : "—"}
          icon={<Users className="w-4 h-4" />}
          iconClass="bg-blue-500"
          href="/leads"
        />
        <StatCard
          label="Converted"
          value={metrics ? String(metrics.converted_count) : "—"}
          icon={<TrendingUp className="w-4 h-4" />}
          iconClass="bg-emerald-500"
          href="/leads?status=converted"
        />
        <StatCard
          label="Conversion Rate"
          value={total > 0 ? convRate : "—"}
          icon={<Sparkles className="w-4 h-4" />}
          iconClass="bg-indigo-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline breakdown */}
        <div className="rounded-xl bg-white border border-gray-200 shadow-card p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Pipeline</h2>
              <p className="text-xs text-gray-400 mt-0.5">Leads by stage</p>
            </div>
            <Link
              href="/leads"
              className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
            >
              View all <ArrowUpRight className="w-3 h-3" />
            </Link>
          </div>
          {metrics && metrics.by_status.length > 0 ? (
            <div className="space-y-3">
              {[...metrics.by_status]
                .sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status))
                .map(({ status, count }) => {
                  const pct = pipelineTotal > 0 ? Math.round((count / pipelineTotal) * 100) : 0;
                  return (
                    <Link
                      key={status}
                      href={`/leads?status=${status}`}
                      className="block group"
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <StatusBadge status={status} />
                        <span className="text-sm font-semibold text-gray-800 tabular-nums">
                          {count}
                          <span className="text-xs font-normal text-gray-400 ml-1">({pct}%)</span>
                        </span>
                      </div>
                      <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-indigo-500 transition-all duration-500 group-hover:bg-indigo-600"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </Link>
                  );
                })}
            </div>
          ) : (
            <EmptyState message="No leads yet. Ingest some leads to see the pipeline." />
          )}
        </div>

        {/* Recent activity */}
        <div className="rounded-xl bg-white border border-gray-200 shadow-card p-5">
          <div className="mb-5">
            <h2 className="text-sm font-semibold text-gray-900">Recent Activity</h2>
            <p className="text-xs text-gray-400 mt-0.5">Latest events across all leads</p>
          </div>
          {metrics && metrics.recent_events.length > 0 ? (
            <ol className="space-y-4">
              {metrics.recent_events.map((e, i) => {
                const isLast = i === metrics.recent_events.length - 1;
                const dotColor = EVENT_COLORS[e.event_type] ?? "bg-gray-300";
                return (
                  <li key={i} className="flex gap-3">
                    <div className="flex flex-col items-center shrink-0">
                      <span className={`w-2 h-2 rounded-full mt-1 ${dotColor}`} />
                      {!isLast && <span className="w-px flex-1 bg-gray-100 mt-1.5" />}
                    </div>
                    <div className="pb-3 min-w-0 flex-1">
                      <p className="text-sm text-gray-800 leading-snug">
                        {EVENT_LABELS[e.event_type] ?? e.event_type}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <Link
                          href={`/leads/${e.lead_id}`}
                          className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
                        >
                          View lead
                        </Link>
                        <span className="text-gray-300">·</span>
                        <span className="text-xs text-gray-400">{relativeTime(e.occurred_at)}</span>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : (
            <EmptyState message="No recent activity. Activity will appear here as leads are updated." />
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  iconClass,
  href,
}: {
  label: string;
  value: string;
  icon: ReactNode;
  iconClass: string;
  href?: string;
}) {
  const inner = (
    <div className="group rounded-xl bg-white border border-gray-200 shadow-card hover:shadow-elevated transition-shadow duration-200 p-5 flex items-start gap-4">
      <div className={`flex items-center justify-center w-9 h-9 rounded-lg text-white shrink-0 ${iconClass}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-1 tabular-nums tracking-tight">{value}</p>
      </div>
      {href && (
        <ArrowUpRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-indigo-500 transition-colors ml-auto shrink-0 mt-0.5" />
      )}
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-10">
      <p className="text-xs text-gray-400 max-w-xs mx-auto leading-relaxed">{message}</p>
    </div>
  );
}
