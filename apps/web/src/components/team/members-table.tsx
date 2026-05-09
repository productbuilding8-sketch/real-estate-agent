"use client";

import { useState, useTransition } from "react";
import { MoreHorizontal, ShieldCheck, Trash2 } from "lucide-react";
import { RoleBadge, ROLE_OPTIONS, type RoleSlug } from "@/components/team/role-badge";
import { removeMember, changeMemberRole } from "@/app/(authenticated)/team/actions";
import { cn } from "@/lib/cn";

export type Member = {
  id: string;
  name: string;
  email: string;
  role_slug: RoleSlug;
  joined_at: string | null;
  is_active: boolean;
  is_you?: boolean;
};

function Avatar({ name }: { name: string }) {
  const initials = name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase();
  const colors = ["bg-indigo-500","bg-violet-500","bg-blue-500","bg-emerald-500","bg-rose-500","bg-amber-500"];
  const color = colors[name.charCodeAt(0) % colors.length];
  return (
    <div className={cn("h-8 w-8 rounded-full flex items-center justify-center text-white text-xs font-semibold shrink-0", color)}>
      {initials}
    </div>
  );
}

function ChangeRoleModal({
  member,
  onClose,
}: {
  member: Member;
  onClose: () => void;
}) {
  const [role, setRole] = useState<RoleSlug>(member.role_slug);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState("");

  function handleSave() {
    setError("");
    startTransition(async () => {
      const result = await changeMemberRole(member.id, role);
      if (result.error) { setError(result.error); return; }
      onClose();
    });
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-sm rounded-2xl bg-white shadow-xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-gray-900">Change role — {member.name}</h2>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as RoleSlug)}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {ROLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex justify-end gap-3">
            <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100">Cancel</button>
            <button
              onClick={handleSave}
              disabled={isPending || role === member.role_slug}
              className="rounded-lg px-3 py-1.5 text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {isPending ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function ActionMenu({ member }: { member: Member }) {
  const [open, setOpen] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [isPending, startTransition] = useTransition();

  if (member.is_you) return null;

  function handleRemove() {
    setOpen(false);
    if (!confirm(`Remove ${member.name} from the team?`)) return;
    startTransition(() => { void removeMember(member.id); });
  }

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setOpen((o) => !o)}
          disabled={isPending}
          className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors disabled:opacity-40"
        >
          <MoreHorizontal className="w-4 h-4" />
        </button>

        {open && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
            <div className="absolute right-0 top-full mt-1 z-20 w-44 rounded-xl bg-white shadow-lg ring-1 ring-gray-200 py-1">
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                onClick={() => { setOpen(false); setShowRoleModal(true); }}
              >
                <ShieldCheck className="w-3.5 h-3.5 text-gray-400" />
                Change role
              </button>
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                onClick={handleRemove}
              >
                <Trash2 className="w-3.5 h-3.5" />
                Remove member
              </button>
            </div>
          </>
        )}
      </div>

      {showRoleModal && (
        <ChangeRoleModal member={member} onClose={() => setShowRoleModal(false)} />
      )}
    </>
  );
}

interface MembersTableProps {
  members: Member[];
}

export function MembersTable({ members }: MembersTableProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <table className="min-w-full divide-y divide-gray-100">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Member</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
            <th className="hidden sm:table-cell px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Joined</th>
            <th className="hidden sm:table-cell px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
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
                      {member.is_you && <span className="ml-1.5 text-xs font-normal text-gray-400">(you)</span>}
                    </p>
                    <p className="text-xs text-gray-500 truncate">{member.email}</p>
                  </div>
                </div>
              </td>
              <td className="px-4 py-3.5">
                <RoleBadge role={member.role_slug} />
              </td>
              <td className="hidden sm:table-cell px-4 py-3.5 text-sm text-gray-500">
                {member.joined_at
                  ? new Date(member.joined_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
                  : "—"}
              </td>
              <td className="hidden sm:table-cell px-4 py-3.5">
                <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", member.is_active ? "text-green-600" : "text-gray-400")}>
                  <span className={cn("h-1.5 w-1.5 rounded-full", member.is_active ? "bg-green-500" : "bg-gray-300")} />
                  {member.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td className="px-4 py-3.5 text-right">
                <ActionMenu member={member} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
