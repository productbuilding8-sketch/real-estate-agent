"use client";

import { useRef, useState, useEffect } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { Search, X } from "lucide-react";
import { StatusBadge, ALL_STATUSES } from "@/components/leads/status-badge";
import { cn } from "@/lib/cn";

interface LeadsFiltersProps {
  counts: Record<string, number>;
}

export function LeadsFilters({ counts }: LeadsFiltersProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const activeStatus = searchParams.get("status") ?? "all";
  const urlSearch = searchParams.get("q") ?? "";
  const [inputValue, setInputValue] = useState(urlSearch);

  useEffect(() => {
    setInputValue(urlSearch);
  }, [urlSearch]);

  function updateParam(key: string, value: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (!value) params.delete(key);
    else params.set(key, value);
    params.delete("page");
    router.push(`${pathname}?${params.toString()}`);
  }

  function handleSearchChange(v: string) {
    setInputValue(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => updateParam("q", v || null), 300);
  }

  const tabs = ["all", ...ALL_STATUSES];

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        <input
          type="text"
          value={inputValue}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Search by name or email…"
          className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-9 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        />
        {inputValue && (
          <button
            onClick={() => handleSearchChange("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <div className="flex items-center gap-1 flex-wrap">
        {tabs.map((value) => {
          const count = counts[value] ?? 0;
          const isActive = activeStatus === value;
          if (value !== "all" && count === 0) return null;
          return (
            <button
              key={value}
              onClick={() => updateParam("status", value === "all" ? null : value)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                isActive
                  ? "bg-gray-900 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50",
              )}
            >
              {value === "all" ? "All" : <StatusBadge status={value} />}
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                  isActive ? "bg-white/20 text-white" : "bg-gray-100 text-gray-500",
                )}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
