"use client";

import { Search, X } from "lucide-react";
import { StatusBadge, ALL_STATUSES } from "@/components/leads/status-badge";
import type { LeadStatus } from "@/lib/mock-leads";
import { cn } from "@/lib/cn";

interface LeadsFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  activeStatus: LeadStatus | "all";
  onStatusChange: (s: LeadStatus | "all") => void;
  counts: Record<string, number>;
}

export function LeadsFilters({
  search, onSearchChange,
  activeStatus, onStatusChange,
  counts,
}: LeadsFiltersProps) {
  const tabs: { value: LeadStatus | "all"; label: string }[] = [
    { value: "all", label: "All" },
    ...ALL_STATUSES.map((s) => ({ value: s, label: s.replace("_", " ") })),
  ];

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by name or email…"
          className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-9 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
        {search && (
          <button
            onClick={() => onSearchChange("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Status tabs */}
      <div className="flex items-center gap-1 flex-wrap">
        {tabs.map(({ value }) => {
          const count = counts[value] ?? 0;
          const isActive = activeStatus === value;
          if (value !== "all" && count === 0) return null;
          return (
            <button
              key={value}
              onClick={() => onStatusChange(value)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                isActive
                  ? "bg-gray-900 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
              )}
            >
              {value === "all" ? "All" : <StatusBadge status={value as LeadStatus} />}
              <span className={cn(
                "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                isActive ? "bg-white/20 text-white" : "bg-gray-100 text-gray-500"
              )}>
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
