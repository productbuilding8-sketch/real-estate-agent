"use server";

import { revalidatePath } from "next/cache";
import { apiHeaders } from "@/lib/api-client";

const BASE = () => `${process.env.INTERNAL_API_URL}/api/v1/team`;
const isMock = process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL;

export async function inviteTeamMember(
  email: string,
  roleSlug: string,
): Promise<{ error?: string }> {
  if (isMock) {
    revalidatePath("/team");
    return {};
  }

  const res = await fetch(`${BASE()}/invitations`, {
    method: "POST",
    headers: await apiHeaders(),
    body: JSON.stringify({ email, role_slug: roleSlug }),
    cache: "no-store",
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: { message?: string } };
    return { error: body.detail?.message ?? "Failed to send invitation." };
  }

  revalidatePath("/team");
  return {};
}

export async function revokeInvitation(id: string): Promise<{ error?: string }> {
  if (isMock) {
    revalidatePath("/team");
    return {};
  }

  const res = await fetch(`${BASE()}/invitations/${id}`, {
    method: "DELETE",
    headers: await apiHeaders(),
    cache: "no-store",
  });

  if (!res.ok && res.status !== 404) {
    return { error: "Failed to revoke invitation." };
  }

  revalidatePath("/team");
  return {};
}

export async function removeMember(userId: string): Promise<{ error?: string }> {
  if (isMock) {
    revalidatePath("/team");
    return {};
  }

  const res = await fetch(`${BASE()}/members/${userId}`, {
    method: "DELETE",
    headers: await apiHeaders(),
    cache: "no-store",
  });

  if (!res.ok && res.status !== 404) {
    const body = (await res.json().catch(() => ({}))) as { detail?: { message?: string } };
    return { error: body.detail?.message ?? "Failed to remove member." };
  }

  revalidatePath("/team");
  return {};
}

export async function changeMemberRole(
  userId: string,
  roleSlug: string,
): Promise<{ error?: string }> {
  if (isMock) {
    revalidatePath("/team");
    return {};
  }

  const res = await fetch(`${BASE()}/members/${userId}/role`, {
    method: "PATCH",
    headers: await apiHeaders(),
    body: JSON.stringify({ role_slug: roleSlug }),
    cache: "no-store",
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: { message?: string } };
    return { error: body.detail?.message ?? "Failed to change role." };
  }

  revalidatePath("/team");
  return {};
}
