"use client";

import { useState, useTransition } from "react";
import { Check, Loader2 } from "lucide-react";
import { updateGeneralSettings } from "@/app/(authenticated)/settings/general/actions";
import type { TenantSettings } from "@/lib/api-client";
import { cn } from "@/lib/cn";

const TIMEZONES = [
  { value: "UTC",                  label: "UTC" },
  { value: "America/New_York",     label: "Eastern Time (ET)" },
  { value: "America/Chicago",      label: "Central Time (CT)" },
  { value: "America/Denver",       label: "Mountain Time (MT)" },
  { value: "America/Los_Angeles",  label: "Pacific Time (PT)" },
  { value: "America/Phoenix",      label: "Arizona (MST, no DST)" },
  { value: "America/Anchorage",    label: "Alaska Time (AKT)" },
  { value: "America/Honolulu",     label: "Hawaii Time (HST)" },
  { value: "America/Toronto",      label: "Toronto (ET)" },
  { value: "America/Vancouver",    label: "Vancouver (PT)" },
  { value: "America/Sao_Paulo",    label: "São Paulo (BRT)" },
  { value: "Europe/London",        label: "London (GMT/BST)" },
  { value: "Europe/Paris",         label: "Paris (CET/CEST)" },
  { value: "Europe/Berlin",        label: "Berlin (CET/CEST)" },
  { value: "Europe/Amsterdam",     label: "Amsterdam (CET/CEST)" },
  { value: "Europe/Istanbul",      label: "Istanbul (TRT)" },
  { value: "Asia/Dubai",           label: "Dubai (GST)" },
  { value: "Asia/Kolkata",         label: "India (IST)" },
  { value: "Asia/Singapore",       label: "Singapore (SGT)" },
  { value: "Asia/Tokyo",           label: "Tokyo (JST)" },
  { value: "Asia/Seoul",           label: "Seoul (KST)" },
  { value: "Asia/Shanghai",        label: "China (CST)" },
  { value: "Australia/Sydney",     label: "Sydney (AEST/AEDT)" },
  { value: "Australia/Melbourne",  label: "Melbourne (AEST/AEDT)" },
  { value: "Pacific/Auckland",     label: "Auckland (NZST/NZDT)" },
];

interface SectionProps {
  title: string;
  description: string;
  children: React.ReactNode;
}

function Section({ title, description, children }: SectionProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      </div>
      {children}
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 border-b border-gray-100 last:border-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-900">{label}</p>
        {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent",
          "transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1",
          checked ? "bg-indigo-600" : "bg-gray-200",
        )}
      >
        <span
          className={cn(
            "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-200",
            checked ? "translate-x-4" : "translate-x-0",
          )}
        />
      </button>
    </div>
  );
}

interface GeneralSettingsFormProps {
  initialSettings: TenantSettings;
}

export function GeneralSettingsForm({ initialSettings }: GeneralSettingsFormProps) {
  const [name, setName] = useState(initialSettings.name);
  const [timezone, setTimezone] = useState(initialSettings.timezone);
  const [notifications, setNotifications] = useState(initialSettings.notifications);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function setNotif(key: keyof typeof notifications, value: boolean) {
    setNotifications((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  function handleSave() {
    if (!name.trim()) return;
    setError(null);
    setSaved(false);
    startTransition(async () => {
      const result = await updateGeneralSettings({ name: name.trim(), timezone, notifications });
      if (result.error) {
        setError(result.error);
      } else {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    });
  }

  const nameOver = name.length > 255;
  const canSave = name.trim().length > 0 && !nameOver;

  return (
    <div className="space-y-5">
      {/* Workspace */}
      <Section title="Workspace" description="Basic information about your brokerage.">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Workspace name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => { setName(e.target.value); setSaved(false); setError(null); }}
              disabled={isPending}
              placeholder="e.g. Sunrise Realty Group"
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

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Workspace slug
            </label>
            <input
              type="text"
              value={initialSettings.slug}
              disabled
              className="w-full max-w-sm rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500 cursor-not-allowed"
            />
            <p className="text-xs text-gray-400 mt-1">Slug cannot be changed after creation.</p>
          </div>
        </div>
      </Section>

      {/* Timezone */}
      <Section title="Timezone" description="Used for scheduling, reports, and activity timestamps.">
        <select
          value={timezone}
          onChange={(e) => { setTimezone(e.target.value); setSaved(false); }}
          disabled={isPending}
          className={cn(
            "w-full max-w-sm rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900",
            "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
            "disabled:opacity-60",
          )}
        >
          {TIMEZONES.map((tz) => (
            <option key={tz.value} value={tz.value}>
              {tz.label}
            </option>
          ))}
        </select>
      </Section>

      {/* Notifications */}
      <Section
        title="Notification preferences"
        description="Control which email notifications are sent to workspace admins."
      >
        <div>
          <Toggle
            checked={notifications.new_lead_email}
            onChange={(v) => setNotif("new_lead_email", v)}
            label="New lead received"
            description="Send an email when a new lead is ingested into the workspace."
          />
          <Toggle
            checked={notifications.lead_assigned_email}
            onChange={(v) => setNotif("lead_assigned_email", v)}
            label="Lead assigned"
            description="Notify the assigned agent when a lead is assigned to them."
          />
          <Toggle
            checked={notifications.daily_summary}
            onChange={(v) => setNotif("daily_summary", v)}
            label="Daily activity summary"
            description="Receive a morning digest of new leads and pipeline changes."
          />
          <Toggle
            checked={notifications.weekly_report}
            onChange={(v) => setNotif("weekly_report", v)}
            label="Weekly performance report"
            description="Receive a Monday summary of conversion rates and team activity."
          />
        </div>
      </Section>

      {/* Save bar */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={!canSave || isPending}
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
    </div>
  );
}
