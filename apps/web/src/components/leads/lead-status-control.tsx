"use client";

import { useState, useRef, useEffect, useTransition } from "react";
import { ChevronDown } from "lucide-react";
import { StatusBadge } from "@/components/leads/status-badge";
import { updateLeadStatus } from "@/app/(authenticated)/leads/[id]/actions";
import { cn } from "@/lib/cn";

const TRANSITIONS: Record<string, string[]> = {
  new:       ["contacted", "qualified", "lost", "archived"],
  contacted: ["qualified", "lost", "archived"],
  qualified: ["converted", "lost", "archived"],
  converted: ["archived"],
  lost:      ["new", "archived"],
  archived:  [],
};

interface LeadStatusControlProps {
  leadId: string;
  initialStatus: string;
}

export function LeadStatusControl({ leadId, initialStatus }: LeadStatusControlProps) {
  const [status, setStatus] = useState(initialStatus);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const allowed = TRANSITIONS[status] ?? [];
  if (allowed.length === 0) {
    return <StatusBadge status={status} />;
  }

  function changeStatus(newStatus: string) {
    setOpen(false);
    setError(null);
    const prev = status;
    setStatus(newStatus); // optimistic
    startTransition(async () => {
      const result = await updateLeadStatus(leadId, newStatus);
      if (result.error) {
        setStatus(prev);
        setError(result.error);
      }
    });
  }

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={isPending}
        className={cn(
          "inline-flex items-center gap-1 rounded-full transition-opacity",
          isPending && "opacity-50 cursor-wait",
        )}
        aria-label="Change status"
      >
        <StatusBadge status={status} />
        <ChevronDown className="w-3 h-3 text-gray-400" />
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 z-20 min-w-[140px] rounded-lg border border-gray-200 bg-white shadow-lg py-1">
          {allowed.map((s) => (
            <button
              key={s}
              onClick={() => changeStatus(s)}
              className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 text-left"
            >
              <StatusBadge status={s} />
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}
