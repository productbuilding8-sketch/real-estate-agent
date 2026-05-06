import { cn } from "@/lib/cn";

export type LeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "converted"
  | "lost"
  | "archived";

const STATUS_CONFIG: Record<LeadStatus, { label: string; className: string }> = {
  new:       { label: "New",       className: "bg-blue-100    text-blue-700    ring-blue-200"    },
  contacted: { label: "Contacted", className: "bg-indigo-100  text-indigo-700  ring-indigo-200"  },
  qualified: { label: "Qualified", className: "bg-emerald-100 text-emerald-700 ring-emerald-200" },
  converted: { label: "Converted", className: "bg-green-100   text-green-700   ring-green-200"   },
  lost:      { label: "Lost",      className: "bg-red-100     text-red-700     ring-red-200"     },
  archived:  { label: "Archived",  className: "bg-gray-50     text-gray-400    ring-gray-100"    },
};

const FALLBACK = { label: "Unknown", className: "bg-gray-100 text-gray-500 ring-gray-200" };

export const ALL_STATUSES = Object.keys(STATUS_CONFIG) as LeadStatus[];

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status as LeadStatus] ?? FALLBACK;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        config.className,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
