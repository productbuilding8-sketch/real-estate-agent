"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { UserCircle, ChevronDown, Loader2, X, Check } from "lucide-react";
import { assignLead } from "@/app/(authenticated)/leads/[id]/actions";
import type { TeamMember } from "@/lib/api-client";
import { cn } from "@/lib/cn";

interface AssignLeadControlProps {
  leadId: string;
  initialAgentId: string | null;
  agents: TeamMember[];
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  return (parts[0]?.[0] ?? "?").toUpperCase();
}

const AVATAR_COLORS = [
  "bg-violet-500",
  "bg-blue-500",
  "bg-emerald-500",
  "bg-rose-500",
  "bg-amber-500",
  "bg-indigo-500",
];

function agentColor(id: string): string {
  const code = id.charCodeAt(0) + id.charCodeAt(id.length - 1);
  return AVATAR_COLORS[code % AVATAR_COLORS.length]!;
}

export function AssignLeadControl({
  leadId,
  initialAgentId,
  agents,
}: AssignLeadControlProps) {
  const [agentId, setAgentId] = useState<string | null>(initialAgentId);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const assigned = agents.find((a) => a.id === agentId) ?? null;

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  function select(newAgentId: string | null) {
    setOpen(false);
    if (newAgentId === agentId) return;
    const prev = agentId;
    setAgentId(newAgentId); // optimistic
    setError(null);
    startTransition(async () => {
      const result = await assignLead(leadId, newAgentId);
      if (result.error) {
        setAgentId(prev); // revert
        setError(result.error);
      }
    });
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => { setOpen((v) => !v); setError(null); }}
        disabled={isPending}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors",
          "border border-gray-200 bg-white text-gray-700 hover:bg-gray-50",
          "disabled:opacity-60 disabled:cursor-not-allowed",
        )}
      >
        {isPending ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-400" />
        ) : assigned ? (
          <div
            className={cn(
              "w-4 h-4 rounded-full flex items-center justify-center text-white",
              "text-[9px] font-bold shrink-0",
              agentColor(assigned.id),
            )}
          >
            {getInitials(assigned.name)}
          </div>
        ) : (
          <UserCircle className="w-3.5 h-3.5 text-gray-400" />
        )}
        <span>{assigned ? assigned.name : "Unassigned"}</span>
        <ChevronDown className="w-3 h-3 text-gray-400" />
      </button>

      {error && (
        <p className="absolute top-full left-0 mt-1 text-xs text-red-500 whitespace-nowrap">
          {error}
        </p>
      )}

      {open && (
        <div className="absolute top-full left-0 mt-1 z-20 w-56 rounded-xl border border-gray-200 bg-white shadow-lg py-1">
          {/* Unassign option */}
          {agentId && (
            <button
              onClick={() => select(null)}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50"
            >
              <X className="w-3.5 h-3.5" />
              Unassign
            </button>
          )}
          {agentId && agents.length > 0 && (
            <div className="my-1 border-t border-gray-100" />
          )}
          {agents.map((agent) => (
            <button
              key={agent.id}
              onClick={() => select(agent.id)}
              className="flex w-full items-center gap-2.5 px-3 py-1.5 text-xs hover:bg-gray-50 text-left"
            >
              <div
                className={cn(
                  "w-5 h-5 rounded-full flex items-center justify-center text-white",
                  "text-[9px] font-bold shrink-0",
                  agentColor(agent.id),
                )}
              >
                {getInitials(agent.name)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-gray-900 font-medium truncate">{agent.name}</p>
                <p className="text-gray-400 truncate">{agent.email}</p>
              </div>
              {agent.id === agentId && (
                <Check className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              )}
            </button>
          ))}
          {agents.length === 0 && (
            <p className="px-3 py-2 text-xs text-gray-400">No agents found</p>
          )}
        </div>
      )}
    </div>
  );
}
