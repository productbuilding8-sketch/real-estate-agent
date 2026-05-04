"use client";

import { useState } from "react";
import { Clock, X } from "lucide-react";
import { RoleBadge, type RoleSlug } from "@/components/team/role-badge";

export type PendingInvitation = {
  id: string;
  email: string;
  role_slug: RoleSlug;
  expires_at: string;
};

interface PendingInvitationsProps {
  invitations: PendingInvitation[];
}

export function PendingInvitations({ invitations: initial }: PendingInvitationsProps) {
  const [invitations, setInvitations] = useState(initial);

  if (invitations.length === 0) return null;

  function revoke(id: string) {
    if (!confirm("Revoke this invitation?")) return;
    setInvitations((prev) => prev.filter((i) => i.id !== id));
  }

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
        Pending invitations ({invitations.length})
      </h3>
      <div className="rounded-xl border border-dashed border-amber-200 bg-amber-50/50 divide-y divide-amber-100 overflow-hidden">
        {invitations.map((inv) => {
          const expiresAt = new Date(inv.expires_at);
          const hoursLeft = Math.max(
            0,
            Math.round((expiresAt.getTime() - Date.now()) / 36e5)
          );

          return (
            <div key={inv.id} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex items-center justify-center w-7 h-7 rounded-full bg-amber-100 shrink-0">
                  <Clock className="w-3.5 h-3.5 text-amber-600" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{inv.email}</p>
                  <p className="text-xs text-amber-600">
                    Expires in {hoursLeft}h
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-3">
                <RoleBadge role={inv.role_slug} />
                <button
                  onClick={() => revoke(inv.id)}
                  className="rounded-md p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                  title="Revoke invitation"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
