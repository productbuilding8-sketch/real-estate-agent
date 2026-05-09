"use client";

import { useState, useTransition } from "react";
import { Check, Loader2, User, Mail, Shield, LogOut, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { updateProfile } from "@/app/(authenticated)/profile/actions";
import { cn } from "@/lib/cn";

const ROLE_LABELS: Record<string, { label: string; color: string }> = {
  owner_admin: { label: "Owner / Admin",  color: "bg-violet-100 text-violet-700 ring-violet-200" },
  manager:     { label: "Manager",         color: "bg-blue-100 text-blue-700 ring-blue-200" },
  agent:       { label: "Agent",           color: "bg-emerald-100 text-emerald-700 ring-emerald-200" },
  viewer:      { label: "Viewer",          color: "bg-gray-100 text-gray-600 ring-gray-200" },
};

interface ProfileFormProps {
  user: {
    sub: string;
    name: string;
    email: string;
    picture: string | null;
    email_verified: boolean;
  };
  roleSlug?: string;
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-card p-6">
      <div className="mb-5">
        <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
        {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
      </div>
      {children}
    </div>
  );
}

function ReadonlyField({ label, value, icon: Icon }: { label: string; value: string; icon?: React.ElementType }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      <div className="flex items-center gap-2 w-full max-w-sm rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
        {Icon && <Icon className="w-3.5 h-3.5 text-gray-400 shrink-0" />}
        <span className="text-sm text-gray-700 truncate">{value}</span>
      </div>
    </div>
  );
}

export function ProfileForm({ user, roleSlug }: ProfileFormProps) {
  const [name, setName] = useState(user.name);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const initials = name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase() || "?";

  const role = roleSlug ? ROLE_LABELS[roleSlug] : null;
  const nameChanged = name.trim() !== user.name;
  const nameOver = name.length > 255;

  function handleSave() {
    if (!name.trim() || nameOver) return;
    setError(null);
    setSaved(false);
    startTransition(async () => {
      const result = await updateProfile({ name: name.trim() });
      if (result.error) {
        setError(result.error);
      } else {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    });
  }

  return (
    <div className="space-y-5">
      {/* Avatar + identity header */}
      <div className="rounded-xl border border-gray-200 bg-white shadow-card p-6">
        <div className="flex items-center gap-5">
          {user.picture ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={user.picture}
              alt={user.name}
              className="h-16 w-16 rounded-full object-cover ring-2 ring-gray-100"
            />
          ) : (
            <div className="h-16 w-16 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-xl font-bold ring-2 ring-gray-100 shrink-0">
              {initials}
            </div>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-base font-semibold text-gray-900 truncate">{user.name}</h1>
              {role && (
                <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", role.color)}>
                  {role.label}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 truncate mt-0.5">{user.email}</p>
            {user.email_verified && (
              <p className="flex items-center gap-1 text-xs text-emerald-600 mt-1">
                <Shield className="w-3 h-3" />
                Email verified
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Personal information */}
      <Section
        title="Personal information"
        description="Your display name is shown to teammates and in lead activity."
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Display name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); setSaved(false); setError(null); }}
              disabled={isPending}
              placeholder="Your full name"
              className={cn(
                "w-full max-w-sm rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400",
                "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
                "disabled:opacity-60",
                nameOver ? "border-red-300" : "border-gray-300",
              )}
            />
            {nameOver && (
              <p className="text-xs text-red-500 mt-1">{name.length - 255} chars over limit</p>
            )}
          </div>

          <ReadonlyField label="Email address" value={user.email} icon={Mail} />
          <p className="text-xs text-gray-400 -mt-2">
            Email is managed by your identity provider and cannot be changed here.
          </p>
        </div>

        {(nameChanged || saved || error) && (
          <div className="mt-5 flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={!nameChanged || nameOver || isPending}
              className={cn(
                "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors",
                saved
                  ? "bg-green-600 text-white"
                  : "bg-indigo-600 text-white hover:bg-indigo-500",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            >
              {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {!isPending && saved && <Check className="w-4 h-4" />}
              {saved ? "Saved!" : isPending ? "Saving…" : "Save changes"}
            </button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        )}
      </Section>

      {/* Account */}
      <Section title="Account" description="Your Auth0 identity and workspace membership.">
        <div className="space-y-4">
          <ReadonlyField label="User ID" value={user.sub} icon={User} />
          {role && (
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Workspace role</label>
              <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset", role.color)}>
                {role.label}
              </span>
            </div>
          )}
        </div>
      </Section>

      {/* Security */}
      <Section title="Security" description="Manage your password and authentication settings.">
        <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 flex items-start gap-3">
          <Shield className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-700">Password &amp; 2FA</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Authentication is managed by Auth0. Visit your Auth0 account to change your password or enable two-factor authentication.
            </p>
          </div>
        </div>
      </Section>

      {/* Sign out */}
      <Section title="Session">
        <div className="flex items-center gap-3">
          <Link
            href="/api/auth/logout"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-200 bg-red-50 text-sm font-medium text-red-600 hover:bg-red-100 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </Link>
          <p className="text-xs text-gray-400">You will be redirected to the login page.</p>
        </div>
      </Section>

      {/* Danger zone */}
      <Section title="Danger zone">
        <div className="rounded-lg border border-red-100 bg-red-50/50 px-4 py-3 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-700">Leave workspace</p>
            <p className="text-xs text-red-500 mt-0.5">
              Removing yourself from the workspace is permanent. Contact an admin to rejoin.
            </p>
            <button
              disabled
              className="mt-3 inline-flex items-center px-3 py-1.5 rounded-lg border border-red-200 text-xs font-medium text-red-600 bg-white hover:bg-red-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Leave workspace
            </button>
          </div>
        </div>
      </Section>
    </div>
  );
}
