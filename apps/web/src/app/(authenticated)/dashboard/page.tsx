import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { Users, TrendingUp, ArrowRight, Activity } from "lucide-react";
import { getSession } from "@/lib/auth";
import { getDashboardMetrics } from "@/lib/api-client";
import { StatusBadge } from "@/components/leads/status-badge";

export const metadata: Metadata = { title: "Dashboard — DealFlow AI" };

const EVENT_LABELS: Record<string, string> = {
  "lead.created": "New lead ingested",
  "lead.status_changed": "Status changed",
  "lead.assigned": "Lead assigned",
  "lead.unassigned": "Lead unassigned",
  "lead.note_added": "Note added",
  "score.updated": "Score updated",
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

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      {/* Welcome */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Good morning, {firstName}</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Here&apos;s what&apos;s happening with your leads today.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Total Leads"
          value={total > 0 ? String(total) : "—"}
          icon={<Users className="w-5 h-5" />}
          color="bg-blue-50 text-blue-600"
          href="/leads"
        />
        <StatCard
          label="Converted"
          value={metrics ? String(metrics.converted_count) : "—"}
          icon={<TrendingUp className="w-5 h-5" />}
          color="bg-green-50 text-green-600"
          href="/leads?status=converted"
        />
        <StatCard
          label="Conversion Rate"
          value={total > 0 ? convRate : "—"}
          icon={<Activity className="w-5 h-5" />}
          color="bg-purple-50 text-purple-600"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline breakdown */}
        <div className="rounded-xl bg-white border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900">Pipeline</h3>
            <Link href="/leads" className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {metrics && metrics.by_status.length > 0 ? (
            <div className="space-y-2">
              {metrics.by_status
                .sort((a, b) => {
                  const order = ["new", "contacted", "qualified", "converted", "lost", "archived"];
                  return order.indexOf(a.status) - order.indexOf(b.status);
                })
                .map(({ status, count }) => (
                  <Link
                    key={status}
                    href={`/leads?status=${status}`}
                    className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <StatusBadge status={status} />
                    <span className="text-sm font-semibold text-gray-900">{count}</span>
                  </Link>
                ))}
            </div>
          ) : (
            <EmptyState message="No leads yet. Ingest some leads to see the pipeline." />
          )}
        </div>

        {/* Recent activity */}
        <div className="rounded-xl bg-white border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Recent Activity</h3>
          {metrics && metrics.recent_events.length > 0 ? (
            <ol className="space-y-3">
              {metrics.recent_events.map((e, i) => (
                <li key={i} className="flex items-start gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-gray-800">
                      {EVENT_LABELS[e.event_type] ?? e.event_type}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Link
                        href={`/leads/${e.lead_id}`}
                        className="text-xs text-indigo-600 hover:underline truncate"
                      >
                        View lead
                      </Link>
                      <span className="text-xs text-gray-400">{relativeTime(e.occurred_at)}</span>
                    </div>
                  </div>
                </li>
              ))}
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
  color,
  href,
}: {
  label: string;
  value: string;
  icon: ReactNode;
  color: string;
  href?: string;
}) {
  const inner = (
    <div className="rounded-xl bg-white border border-gray-200 p-5 flex items-start gap-4">
      <div className={`rounded-lg p-2.5 ${color}`}>{icon}</div>
      <div>
        <p className="text-xs font-medium text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
      </div>
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-8">
      <p className="text-xs text-gray-400 max-w-xs mx-auto">{message}</p>
    </div>
  );
}
