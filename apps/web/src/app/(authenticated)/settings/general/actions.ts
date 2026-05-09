"use server";

import { revalidatePath } from "next/cache";
import { apiHeaders } from "@/lib/api-client";
import type { NotificationPreferences } from "@/lib/api-client";

export async function updateGeneralSettings(payload: {
  name?: string;
  timezone?: string;
  notifications?: NotificationPreferences;
}): Promise<{ error?: string }> {
  if (process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL) {
    revalidatePath("/settings/general");
    return {};
  }

  const res = await fetch(
    `${process.env.INTERNAL_API_URL}/api/v1/settings/general`,
    {
      method: "PATCH",
      headers: apiHeaders(),
      body: JSON.stringify(payload),
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      detail?: { message?: string };
    };
    return { error: body.detail?.message ?? "Failed to save settings." };
  }

  revalidatePath("/settings/general");
  return {};
}
