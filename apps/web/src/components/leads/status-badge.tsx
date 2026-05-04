import { cn } from "@/lib/cn";
import type { LeadStatus } from "@/lib/mock-leads";

const STATUS_CONFIG: Record<LeadStatus, { label: string; className: string }> = {
  new:          { label: "New",           className: "bg-blue-100   text-blue-700   ring-blue-200" },
  contacted:    { label: "Contacted",     className: "bg-indigo-100 text-indigo-700 ring-indigo-200" },
  qualified:    { label: "Qualified",     className: "bg-emerald-100 text-emerald-700 ring-emerald-200" },
  proposal:     { label: "Proposal",      className: "bg-purple-100 text-purple-700 ring-purple-200" },
  closed_won:   { label: "Closed Won",    className: "bg-green-100  text-green-700  ring-green-200" },
  closed_lost:  { label: "Closed Lost",   className: "bg-red-100    text-red-700    ring-red-200" },
  disqualified: { label: "Disqualified",  className: "bg-gray-100   text-gray-500   ring-gray-200" },
};

export const ALL_STATUSES = Object.keys(STATUS_CONFIG) as LeadStatus[];

interface StatusBadgeProps {
  status: LeadStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
      config.className,
      className,
    )}>
      {config.label}
    </span>
  );
}
