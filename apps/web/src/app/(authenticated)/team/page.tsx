"use client";

import { useState } from "react";
import { UserPlus } from "lucide-react";
import { MembersTable, type Member } from "@/components/team/members-table";
import { PendingInvitations, type PendingInvitation } from "@/components/team/pending-invitations";
import { InviteModal } from "@/components/team/invite-modal";
import { type RoleSlug } from "@/components/team/role-badge";

// TODO: Replace with real API data once POST /api/v1/tenants/invitations is ready
const MOCK_MEMBERS: Member[] = [
  {
    id: "u-001",
    name: "Alex Johnson",
    email: "alex@brokerage.com",
    role_slug: "owner_admin",
    joined_at: "2025-01-15",
    is_active: true,
  },
  {
    id: "u-002",
    name: "Sarah Chen",
    email: "sarah@brokerage.com",
    role_slug: "manager",
    joined_at: "2025-02-20",
    is_active: true,
  },
  {
    id: "u-003",
    name: "Demo Agent",
    email: "demo@dealflow.dev",
    role_slug: "agent",
    joined_at: "2026-03-01",
    is_active: true,
    is_you: true,
  },
  {
    id: "u-004",
    name: "Michael Torres",
    email: "m.torres@brokerage.com",
    role_slug: "agent",
    joined_at: "2025-11-10",
    is_active: true,
  },
  {
    id: "u-005",
    name: "Priya Nair",
    email: "p.nair@brokerage.com",
    role_slug: "auditor",
    joined_at: "2025-09-05",
    is_active: false,
  },
];

const MOCK_INVITATIONS: PendingInvitation[] = [
  {
    id: "inv-001",
    email: "newagent@brokerage.com",
    role_slug: "agent",
    expires_at: new Date(Date.now() + 58 * 60 * 60 * 1000).toISOString(), // 58h from now
  },
];

export default function TeamPage() {
  const [inviteOpen, setInviteOpen] = useState(false);
  const [invitations, setInvitations] = useState<PendingInvitation[]>(MOCK_INVITATIONS);

  function handleInvited(email: string, role: RoleSlug) {
    setInvitations((prev) => [
      ...prev,
      {
        id: `inv-${Date.now()}`,
        email,
        role_slug: role,
        expires_at: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
      },
    ]);
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Team</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage members and invitations for this workspace.
          </p>
        </div>
        <button
          onClick={() => setInviteOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors shadow-sm"
        >
          <UserPlus className="w-4 h-4" />
          Invite member
        </button>
      </div>

      {/* Stat strip */}
      <div className="flex items-center gap-6 rounded-xl bg-white border border-gray-200 px-5 py-4">
        <Stat label="Total members" value={MOCK_MEMBERS.length} />
        <div className="h-8 w-px bg-gray-200" />
        <Stat label="Active" value={MOCK_MEMBERS.filter((m) => m.is_active).length} />
        <div className="h-8 w-px bg-gray-200" />
        <Stat label="Pending invites" value={invitations.length} highlight={invitations.length > 0} />
      </div>

      {/* Pending invitations */}
      <PendingInvitations invitations={invitations} />

      {/* Members table */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Members ({MOCK_MEMBERS.length})
        </h3>
        <MembersTable members={MOCK_MEMBERS} />
      </div>

      {/* Invite modal */}
      <InviteModal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onInvited={handleInvited}
      />
    </div>
  );
}

function Stat({
  label, value, highlight = false,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-xl font-bold ${highlight ? "text-amber-600" : "text-gray-900"}`}>
        {value}
      </p>
    </div>
  );
}
