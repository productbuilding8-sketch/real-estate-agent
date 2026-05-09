import type { Metadata } from "next";
import { getTenantSettings } from "@/lib/api-client";
import { GeneralSettingsForm } from "@/components/settings/general-settings-form";

export const metadata: Metadata = { title: "General Settings" };

export default async function GeneralSettingsPage() {
  const settings = await getTenantSettings();
  return <GeneralSettingsForm initialSettings={settings} />;
}
