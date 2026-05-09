"use server";

import { revalidatePath } from "next/cache";
import { apiHeaders } from "@/lib/api-client";

export async function updateProfile(payload: {
  name?: string;
}): Promise<{ error?: string }> {
  if (process.env.MOCK_AUTH === "true" || !process.env.INTERNAL_API_URL) {
    revalidatePath("/profile");
    return {};
  }

  const res = await fetch(`${process.env.INTERNAL_API_URL}/api/v1/auth/profile`, {
    method: "PATCH",
    headers: await apiHeaders(),
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: { message?: string } };
    return { error: body.detail?.message ?? "Failed to update profile." };
  }

  revalidatePath("/profile");
  return {};
}
