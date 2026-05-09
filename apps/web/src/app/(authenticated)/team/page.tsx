import { UserPlus } from "lucide-react";
import { getTeamMembers, getTeamInvitations } from "@/lib/api-client";
import { MembersTable, type Member } from "@/components/team/members-table";
import { PendingInvitations, type PendingInvitation } from "@/components/team/pending-invitations";
import { type RoleSlug } from "@/components/team/role-badge";
import { TeamInviteButton } from "@/components/team/team-invite-button";

// Dev user sub — matches the migration-seeded user
const DEV_USER_ID = "20000000-0000-0000-0000-000000000001";

export default async function TeamPage() {
  const [apiMembers, apiInvitations] = await Promise.all([
    getTeamMembers(),
    getTeamInvitations(),
  ]);

  const members: Member[] = apiMembers.map((m) => ({
    id: m.id,
    name: m.name,
    email: m.email,
    role_slug: m.role_slug as RoleSlug,
    joined_at: m.joined_at,
    is_active: m.is_active,
    is_you: m.id === DEV_USER_ID,
  }));

  const invitations: PendingInvitation[] = apiInvitations.map((inv) => ({
    id: inv.id,
    email: inv.email,
    role_slug: inv.role_slug as RoleSlug,
    expires_at: inv.expires_at,
  }));

  const activeCount = members.filter((m) => m.is_active).length;

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight">Team</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage members and invitations for this workspace.
          </p>
        </div>
        <TeamInviteButton />
      </div>

      <div className="flex items-center gap-6 rounded-xl bg-white border border-gray-200 shadow-card px-5 py-4">
        <Stat label="Total members" value={members.length} />
        <div className="h-8 w-px bg-gray-200" />
        <Stat label="Active" value={activeCount} />
        <div className="h-8 w-px bg-gray-200" />
        <Stat label="Pending invites" value={invitations.length} highlight={invitations.length > 0} />
      </div>

      <PendingInvitations invitations={invitations} />

      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Members ({members.length})
        </h3>
        <MembersTable members={members} />
      </div>
    </div>
  );
}

function Stat({ label, value, highlight = false }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-xl font-bold ${highlight ? "text-amber-600" : "text-gray-900"}`}>{value}</p>
    </div>
  );
}
