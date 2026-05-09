"use client";

import { useTransition } from "react";
import { Clock, X } from "lucide-react";
import { RoleBadge, type RoleSlug } from "@/components/team/role-badge";
import { revokeInvitation } from "@/app/(authenticated)/team/actions";

export type PendingInvitation = {
  id: string;
  email: string;
  role_slug: RoleSlug;
  expires_at: string;
};

interface PendingInvitationsProps {
  invitations: PendingInvitation[];
}

function RevokeButton({ id }: { id: string }) {
  const [isPending, startTransition] = useTransition();

  function handleRevoke() {
    if (!confirm("Revoke this invitation?")) return;
    startTransition(() => { void revokeInvitation(id); });
  }

  return (
    <button
      onClick={handleRevoke}
      disabled={isPending}
      className="rounded-md p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
      title="Revoke invitation"
    >
      {isPending ? (
        <span className="block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-300 border-t-red-500" />
      ) : (
        <X className="w-3.5 h-3.5" />
      )}
    </button>
  );
}

export function PendingInvitations({ invitations }: PendingInvitationsProps) {
  if (invitations.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
        Pending invitations ({invitations.length})
      </h3>
      <div className="rounded-xl border border-dashed border-amber-200 bg-amber-50/50 divide-y divide-amber-100 overflow-hidden">
        {invitations.map((inv) => {
          const expiresAt = new Date(inv.expires_at);
          const hoursLeft = Math.max(0, Math.round((expiresAt.getTime() - Date.now()) / 36e5));

          return (
            <div key={inv.id} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex items-center justify-center w-7 h-7 rounded-full bg-amber-100 shrink-0">
                  <Clock className="w-3.5 h-3.5 text-amber-600" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{inv.email}</p>
                  <p className="text-xs text-amber-600">Expires in {hoursLeft}h</p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-3">
                <RoleBadge role={inv.role_slug} />
                <RevokeButton id={inv.id} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
