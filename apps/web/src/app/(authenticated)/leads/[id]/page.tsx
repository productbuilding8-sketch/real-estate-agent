import { notFound } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Mail, Phone, Globe, UserCircle } from "lucide-react";
import { getLead } from "@/lib/api-client";
import { ScoreBadge } from "@/components/leads/score-badge";
import { LeadTimeline } from "@/components/leads/lead-timeline";
import { LeadPreferences } from "@/components/leads/lead-preferences";
import { LeadStatusControl } from "@/components/leads/lead-status-control";
import { AddNoteForm } from "@/components/leads/add-note-form";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props) {
  const { id } = await params;
  const lead = await getLead(id);
  if (!lead) return { title: "Lead not found" };
  return { title: `${lead.contact.full_name ?? "Lead"} — DealFlow AI` };
}

const AVATAR_COLORS = [
  "bg-indigo-500",
  "bg-violet-500",
  "bg-blue-500",
  "bg-emerald-500",
  "bg-rose-500",
];

function getInitials(fullName: string | null): string {
  const parts = (fullName ?? "?").trim().split(/\s+/);
  if (parts.length >= 2) return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  return (parts[0]?.[0] ?? "?").toUpperCase();
}

function InfoRow({ label, value, href }: { label: string; value: string | null; href?: string }) {
  if (!value) return null;
  return (
    <div className="flex gap-2">
      <dt className="text-xs text-gray-500 w-16 shrink-0 pt-0.5">{label}</dt>
      <dd className="text-sm text-gray-900 break-all min-w-0">
        {href ? (
          <a href={href} className="hover:underline text-indigo-600">
            {value}
          </a>
        ) : (
          value
        )}
      </dd>
    </div>
  );
}

export default async function LeadDetailPage({ params }: Props) {
  const { id } = await params;
  const lead = await getLead(id);
  if (!lead) notFound();

  const score =
    lead.confidence_score !== null ? Math.round(lead.confidence_score * 100) : null;
  const avatarColor = AVATAR_COLORS[(lead.contact.full_name?.charCodeAt(0) ?? 0) % 5];

  const sourceTypeBadge: Record<string, string> = {
    webhook: "Webhook",
    crm: "CRM",
    manual: "Manual",
    api: "API",
  };

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
          <div
            className={`h-12 w-12 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0 ${avatarColor}`}
          >
            {getInitials(lead.contact.full_name)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-semibold text-gray-900">
                {lead.contact.full_name ?? "Unknown"}
              </h1>
              <LeadStatusControl leadId={lead.id} initialStatus={lead.status} />
              <ScoreBadge score={score} />
            </div>
            <p className="text-sm text-gray-500 mt-0.5">{lead.contact.email}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-1 space-y-4">
          {/* Contact card */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Contact
            </h2>
            <dl className="space-y-2">
              <InfoRow
                label="Email"
                value={lead.contact.email}
                href={lead.contact.email ? `mailto:${lead.contact.email}` : undefined}
              />
              <InfoRow
                label="Phone"
                value={lead.contact.phone}
                href={lead.contact.phone ? `tel:${lead.contact.phone}` : undefined}
              />
              <InfoRow label="Source" value={lead.source.name} />
              <InfoRow
                label="Type"
                value={sourceTypeBadge[lead.source.type] ?? lead.source.type}
              />
              <InfoRow
                label="Agent"
                value={lead.assigned_agent_id ? "Assigned" : "Unassigned"}
              />
              <InfoRow label="Lead type" value={lead.lead_type} />
            </dl>

            {/* Additional contact points beyond primary email/phone */}
            {lead.contact.contact_points.filter(
              (cp) =>
                !((cp.type === "email" || cp.type === "phone") && cp.is_primary),
            ).length > 0 && (
              <div className="border-t border-gray-100 pt-3 space-y-1.5">
                <p className="text-xs text-gray-500 font-medium">Other contacts</p>
                {lead.contact.contact_points
                  .filter((cp) => !cp.is_primary || (cp.type !== "email" && cp.type !== "phone"))
                  .map((cp, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                      {cp.type === "email" ? (
                        <Mail className="w-3 h-3 text-gray-400 shrink-0" />
                      ) : cp.type === "phone" ? (
                        <Phone className="w-3 h-3 text-gray-400 shrink-0" />
                      ) : (
                        <Globe className="w-3 h-3 text-gray-400 shrink-0" />
                      )}
                      <span className="truncate">{cp.value}</span>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Preferences */}
          {lead.preferences && <LeadPreferences preferences={lead.preferences} />}
        </div>

        {/* Right column: timeline */}
        <div className="lg:col-span-2">
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Activity Timeline
              </h2>
              {lead.assigned_agent_id && (
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <UserCircle className="w-3.5 h-3.5" />
                  Assigned
                </span>
              )}
            </div>
            <LeadTimeline events={lead.timeline} />
            <AddNoteForm leadId={lead.id} />
          </div>
        </div>
      </div>
    </div>
  );
}
