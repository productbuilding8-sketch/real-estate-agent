import { cn } from "@/lib/cn";

export type LeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "converted"
  | "lost"
  | "archived";

const STATUS_CONFIG: Record<
  LeadStatus,
  { label: string; badgeClass: string; dotClass: string }
> = {
  new:       { label: "New",       badgeClass: "bg-blue-50    text-blue-700    ring-blue-200/60",    dotClass: "bg-blue-500"    },
  contacted: { label: "Contacted", badgeClass: "bg-indigo-50  text-indigo-700  ring-indigo-200/60",  dotClass: "bg-indigo-500"  },
  qualified: { label: "Qualified", badgeClass: "bg-emerald-50 text-emerald-700 ring-emerald-200/60", dotClass: "bg-emerald-500" },
  converted: { label: "Converted", badgeClass: "bg-green-50   text-green-700   ring-green-200/60",   dotClass: "bg-green-500"   },
  lost:      { label: "Lost",      badgeClass: "bg-red-50     text-red-700     ring-red-200/60",     dotClass: "bg-red-400"     },
  archived:  { label: "Archived",  badgeClass: "bg-gray-100   text-gray-500    ring-gray-200/60",    dotClass: "bg-gray-400"    },
};

const FALLBACK = {
  label: "Unknown",
  badgeClass: "bg-gray-100 text-gray-500 ring-gray-200/60",
  dotClass: "bg-gray-400",
};

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
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        config.badgeClass,
        className,
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", config.dotClass)} />
      {config.label}
    </span>
  );
}
