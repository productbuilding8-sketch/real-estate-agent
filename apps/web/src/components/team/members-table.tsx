"use client";

import { useState } from "react";
import { MoreHorizontal, ShieldCheck, Trash2 } from "lucide-react";
import { RoleBadge, type RoleSlug } from "@/components/team/role-badge";
import { cn } from "@/lib/cn";

export type Member = {
  id: string;
  name: string;
  email: string;
  role_slug: RoleSlug;
  joined_at: string;
  is_active: boolean;
  is_you?: boolean;
};

function Avatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const colors = [
    "bg-indigo-500", "bg-violet-500", "bg-blue-500",
    "bg-emerald-500", "bg-rose-500", "bg-amber-500",
  ];
  const color = colors[name.charCodeAt(0) % colors.length];

  return (
    <div className={cn("h-8 w-8 rounded-full flex items-center justify-center text-white text-xs font-semibold shrink-0", color)}>
      {initials}
    </div>
  );
}

function ActionMenu({ member, onRemove }: { member: Member; onRemove: (id: string) => void }) {
  const [open, setOpen] = useState(false);

  if (member.is_you) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
      >
        <MoreHorizontal className="w-4 h-4" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 w-44 rounded-xl bg-white shadow-lg ring-1 ring-gray-200 py-1">
            <button
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              onClick={() => { setOpen(false); alert("Role change — API coming soon"); }}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-gray-400" />
              Change role
            </button>
            <button
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              onClick={() => { setOpen(false); onRemove(member.id); }}
            >
              <Trash2 className="w-3.5 h-3.5" />
              Remove member
            </button>
          </div>
        </>
      )}
    </div>
  );
}

interface MembersTableProps {
  members: Member[];
}

export function MembersTable({ members: initial }: MembersTableProps) {
  const [members, setMembers] = useState(initial);

  function handleRemove(id: string) {
    if (!confirm("Remove this member from the team?")) return;
    setMembers((prev) => prev.filter((m) => m.id !== id));
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <table className="min-w-full divide-y divide-gray-100">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Member
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Role
            </th>
            <th className="hidden sm:table-cell px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Joined
            </th>
            <th className="hidden sm:table-cell px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-4 py-3 w-12" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {members.map((member) => (
            <tr key={member.id} className="hover:bg-gray-50/50 transition-colors">
              <td className="px-4 py-3.5">
                <div className="flex items-center gap-3">
                  <Avatar name={member.name} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {member.name}
                      {member.is_you && (
                        <span className="ml-1.5 text-xs font-normal text-gray-400">(you)</span>
                      )}
                    </p>
                    <p className="text-xs text-gray-500 truncate">{member.email}</p>
                  </div>
                </div>
              </td>
              <td className="px-4 py-3.5">
                <RoleBadge role={member.role_slug} />
              </td>
              <td className="hidden sm:table-cell px-4 py-3.5 text-sm text-gray-500">
                {new Date(member.joined_at).toLocaleDateString("en-US", {
                  month: "short", day: "numeric", year: "numeric",
                })}
              </td>
              <td className="hidden sm:table-cell px-4 py-3.5">
                <span className={cn(
                  "inline-flex items-center gap-1.5 text-xs font-medium",
                  member.is_active ? "text-green-600" : "text-gray-400"
                )}>
                  <span className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    member.is_active ? "bg-green-500" : "bg-gray-300"
                  )} />
                  {member.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td className="px-4 py-3.5 text-right">
                <ActionMenu member={member} onRemove={handleRemove} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
