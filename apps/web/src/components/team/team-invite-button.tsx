"use client";

import { useState } from "react";
import { UserPlus } from "lucide-react";
import { InviteModal } from "@/components/team/invite-modal";

export function TeamInviteButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors shadow-sm"
      >
        <UserPlus className="w-4 h-4" />
        Invite member
      </button>
      <InviteModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
