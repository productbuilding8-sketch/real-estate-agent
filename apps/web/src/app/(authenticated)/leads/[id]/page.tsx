import { notFound } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { MOCK_LEADS, MOCK_TIMELINE } from "@/lib/mock-leads";
import { StatusBadge } from "@/components/leads/status-badge";
import { ScoreBadge } from "@/components/leads/score-badge";
import { LeadTimeline } from "@/components/leads/lead-timeline";
import { LeadPreferences } from "@/components/leads/lead-preferences";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props) {
  const { id } = await params;
  const lead = MOCK_LEADS.find((l) => l.id === id);
  if (!lead) return { title: "Lead not found" };
  return { title: `${lead.contact.first_name} ${lead.contact.last_name} — DealFlow AI` };
}

export default async function LeadDetailPage({ params }: Props) {
  const { id } = await params;
  const lead = MOCK_LEADS.find((l) => l.id === id);
  if (!lead) notFound();

  const timeline = MOCK_TIMELINE[lead.id] ?? [];

  const avatarColors = ["bg-indigo-500", "bg-violet-500", "bg-blue-500", "bg-emerald-500", "bg-rose-500"];
  const avatarColor = avatarColors[lead.contact.first_name.charCodeAt(0) % 5];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Back + header */}
      <div>
        <Link
          href="/leads"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Leads
        </Link>

        <div className="flex items-start gap-4">
          <div className={`h-12 w-12 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0 ${avatarColor}`}>
            {lead.contact.first_name[0]}{lead.contact.last_name[0]}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-semibold text-gray-900">
                {lead.contact.first_name} {lead.contact.last_name}
              </h1>
              <StatusBadge status={lead.status} />
              <ScoreBadge score={lead.score} />
            </div>
            <p className="text-sm text-gray-500 mt-0.5">{lead.contact.email}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: contact + preferences */}
        <div className="lg:col-span-1 space-y-4">
          {/* Contact card */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Contact</h2>
            <dl className="space-y-2">
              <InfoRow label="Email" value={lead.contact.email} />
              <InfoRow label="Phone" value={lead.contact.phone} />
              <InfoRow label="Source" value={lead.source.name} />
              <InfoRow label="Agent" value={lead.assigned_agent?.name ?? "Unassigned"} />
            </dl>
          </div>

          {/* Preferences */}
          <LeadPreferences preferences={lead.preferences} />
        </div>

        {/* Right column: timeline */}
        <div className="lg:col-span-2">
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">Activity Timeline</h2>
            <LeadTimeline events={timeline} />
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="text-xs text-gray-500 w-16 shrink-0 pt-0.5">{label}</dt>
      <dd className="text-sm text-gray-900 break-all">{value}</dd>
    </div>
  );
}
