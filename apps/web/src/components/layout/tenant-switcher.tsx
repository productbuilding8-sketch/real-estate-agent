"use client";

import { useState } from "react";
import { Building2, Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

type Tenant = { id: string; name: string; slug: string };

const MOCK_TENANTS: Tenant[] = [
  { id: "tenant-001", name: "DealFlow Demo", slug: "demo" },
];

export function TenantSwitcher() {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<Tenant>(MOCK_TENANTS[0]);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm hover:bg-gray-100 transition-colors"
      >
        <div className="h-6 w-6 rounded-md bg-indigo-100 flex items-center justify-center shrink-0">
          <Building2 className="w-3.5 h-3.5 text-indigo-600" />
        </div>
        <span className="font-medium text-gray-700 max-w-[140px] truncate">{active.name}</span>
        <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full mt-1 z-20 w-56 rounded-xl bg-white shadow-lg ring-1 ring-gray-200 py-1">
            <p className="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
              Workspaces
            </p>
            {MOCK_TENANTS.map((t) => (
              <button
                key={t.id}
                onClick={() => { setActive(t); setOpen(false); }}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left hover:bg-gray-50 transition-colors",
                  active.id === t.id ? "text-gray-900" : "text-gray-600"
                )}
              >
                <div className="h-6 w-6 rounded-md bg-indigo-100 flex items-center justify-center shrink-0">
                  <Building2 className="w-3.5 h-3.5 text-indigo-600" />
                </div>
                <span className="flex-1 truncate">{t.name}</span>
                {active.id === t.id && <Check className="w-3.5 h-3.5 text-indigo-600 shrink-0" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
