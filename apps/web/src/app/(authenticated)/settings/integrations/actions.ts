"use server";

import { revalidatePath } from "next/cache";

const REVALIDATE = "/settings/integrations";

function apiUrl(path: string) {
  return `${process.env.INTERNAL_API_URL}/api/v1${path}`;
}

const isMock = process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL;

export async function connectIntegration(
  provider: string,
  accessToken: string,
  portalId?: string,
): Promise<{ error?: string }> {
  if (!accessToken.trim()) return { error: "Access token is required." };

  if (isMock) {
    revalidatePath(REVALIDATE);
    return {};
  }

  const res = await fetch(apiUrl("/integrations/connect"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, access_token: accessToken, portal_id: portalId || null }),
    cache: "no-store",
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: { message?: string } };
    return { error: body.detail?.message ?? "Failed to connect integration." };
  }

  revalidatePath(REVALIDATE);
  return {};
}

export async function disconnectIntegration(provider: string): Promise<{ error?: string }> {
  if (isMock) {
    revalidatePath(REVALIDATE);
    return {};
  }

  const res = await fetch(apiUrl(`/integrations/${provider}`), {
    method: "DELETE",
    cache: "no-store",
  });

  if (!res.ok && res.status !== 404) {
    return { error: "Failed to disconnect integration." };
  }

  revalidatePath(REVALIDATE);
  return {};
}

export async function triggerSync(provider: string): Promise<{ error?: string; jobId?: string }> {
  if (isMock) {
    return { jobId: "mock-job-id" };
  }

  const res = await fetch(apiUrl(`/integrations/${provider}/sync`), {
    method: "POST",
    cache: "no-store",
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: { message?: string } };
    return { error: body.detail?.message ?? "Failed to trigger sync." };
  }

  const data = (await res.json()) as { queued: boolean; job_id?: string };
  revalidatePath(REVALIDATE);
  return { jobId: data.job_id };
}
