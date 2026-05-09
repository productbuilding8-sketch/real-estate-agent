import type { ComponentType } from "react";
import type { TimelineEvent } from "@/types/leads";
import {
  UserPlus,
  Sparkles,
  UserCheck,
  UserMinus,
  MessageSquare,
  Mail,
  RefreshCw,
  StickyNote,
  Calendar,
  Activity,
} from "lucide-react";

interface LeadTimelineProps {
  events: TimelineEvent[];
}

const EVENT_CONFIG: Record<
  string,
  { label: string; icon: ComponentType<{ className?: string }>; iconClass: string }
> = {
  "lead.created":       { label: "Lead created",      icon: UserPlus,      iconClass: "bg-blue-100    text-blue-600"    },
  "lead.scored":        { label: "Score calculated",  icon: Sparkles,      iconClass: "bg-purple-100  text-purple-600"  },
  "score.updated":      { label: "Score calculated",  icon: Sparkles,      iconClass: "bg-purple-100  text-purple-600"  },
  "lead.assigned":      { label: "Agent assigned",    icon: UserCheck,     iconClass: "bg-indigo-100  text-indigo-600"  },
  "lead.unassigned":    { label: "Agent unassigned",  icon: UserMinus,     iconClass: "bg-gray-100    text-gray-500"    },
  "lead.status_changed":{ label: "Status changed",    icon: RefreshCw,     iconClass: "bg-amber-100   text-amber-600"   },
  "lead.note_added":    { label: "Note added",        icon: StickyNote,    iconClass: "bg-yellow-100  text-yellow-600"  },
  "sms.sent":           { label: "SMS sent",          icon: MessageSquare, iconClass: "bg-emerald-100 text-emerald-600" },
  "message.sent":       { label: "Message sent",      icon: MessageSquare, iconClass: "bg-emerald-100 text-emerald-600" },
  "email.sent":         { label: "Email sent",        icon: Mail,          iconClass: "bg-sky-100     text-sky-600"     },
  "status.changed":     { label: "Status changed",    icon: RefreshCw,     iconClass: "bg-amber-100   text-amber-600"   },
  "note.added":         { label: "Note added",        icon: StickyNote,    iconClass: "bg-yellow-100  text-yellow-600"  },
  "appointment.scheduled": { label: "Appointment scheduled", icon: Calendar, iconClass: "bg-rose-100 text-rose-600"    },
};

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function str(v: unknown): string {
  return typeof v === "string" ? v : String(v ?? "");
}

function EventDetail({
  event_type,
  event_data,
}: {
  event_type: string;
  event_data: Record<string, unknown> | null;
}) {
  const d = event_data ?? {};
  if (event_type === "lead.created") {
    const src = str(d.source ?? d.source_id ?? "");
    return src ? <span className="text-xs text-gray-500">Source: {src}</span> : null;
  }
  if (event_type === "lead.scored" || event_type === "score.updated") {
    const scoreVal = d.score !== undefined ? Math.round(Number(d.score) * 100) : null;
    const by = str(d.method ?? d.model ?? "");
    return (
      <span className="text-xs text-gray-500">
        {scoreVal !== null ? <>Score: <strong>{scoreVal}</strong></> : null}
        {d.tier ? <> &middot; {str(d.tier)}</> : null}
        {by ? ` via ${by}` : ""}
      </span>
    );
  }
  if (event_type === "lead.assigned") {
    const agentName = str(d.agent_name ?? "");
    return <span className="text-xs text-gray-500">{agentName ? `Assigned to ${agentName}` : "Agent assigned"}</span>;
  }
  if (event_type === "lead.unassigned") {
    return <span className="text-xs text-gray-500">Agent removed</span>;
  }
  if (event_type === "lead.status_changed" || event_type === "status.changed") {
    return (
      <span className="text-xs text-gray-500">
        <span className="font-medium capitalize">{str(d.from)}</span>
        {" → "}
        <span className="font-medium capitalize">{str(d.to)}</span>
      </span>
    );
  }
  if (event_type === "lead.note_added" || event_type === "note.added") {
    const text = str(d.text ?? d.note ?? "");
    return <span className="text-xs text-gray-500 italic">&ldquo;{text}&rdquo;</span>;
  }
  if (event_type === "sms.sent" || event_type === "message.sent") {
    const preview = str(d.preview ?? d.body ?? "");
    return preview ? <span className="text-xs text-gray-500 italic">&ldquo;{preview}&rdquo;</span> : null;
  }
  if (event_type === "email.sent") {
    const subject = str(d.subject ?? "");
    return subject ? <span className="text-xs text-gray-500">Subject: <em>{subject}</em></span> : null;
  }
  if (event_type === "appointment.scheduled") {
    return (
      <span className="text-xs text-gray-500">
        {str(d.type)} on {str(d.date)}
      </span>
    );
  }
  return null;
}

export function LeadTimeline({ events }: LeadTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="text-center py-8">
        <Activity className="w-6 h-6 text-gray-300 mx-auto mb-2" />
        <p className="text-sm text-gray-400">No activity yet</p>
      </div>
    );
  }

  const sorted = [...events].sort(
    (a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime(),
  );

  return (
    <ol className="space-y-4">
      {sorted.map((event, idx) => {
        const config = EVENT_CONFIG[event.event_type] ?? {
          label: event.event_type,
          icon: Activity,
          iconClass: "bg-gray-100 text-gray-500",
        };
        const Icon = config.icon;
        const isLast = idx === sorted.length - 1;

        return (
          <li key={event.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${config.iconClass}`}
              >
                <Icon className="w-3.5 h-3.5" />
              </div>
              {!isLast && <div className="w-px flex-1 bg-gray-100 mt-1" />}
            </div>
            <div className="pb-4 min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-medium text-gray-800">{config.label}</span>
                <span className="text-xs text-gray-400 shrink-0">
                  {relativeTime(event.occurred_at)}
                </span>
              </div>
              <EventDetail event_type={event.event_type} event_data={event.event_data} />
              <p className="text-[11px] text-gray-400 mt-0.5 capitalize">{event.actor_type}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
