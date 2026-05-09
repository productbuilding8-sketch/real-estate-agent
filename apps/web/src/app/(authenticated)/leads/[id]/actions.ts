"use server";

import { revalidatePath } from "next/cache";

export async function addNote(
  leadId: string,
  text: string,
): Promise<{ error?: string }> {
  if (!text.trim() || text.length > 2000) {
    return { error: "Note must be between 1 and 2000 characters." };
  }

  if (process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL) {
    // Mock mode — no persistent store, just revalidate so the page re-renders
    revalidatePath(`/leads/${leadId}`);
    return {};
  }

  const res = await fetch(
    `${process.env.INTERNAL_API_URL}/api/v1/leads/${leadId}/notes`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.trim() }),
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      detail?: { message?: string };
    };
    return { error: body.detail?.message ?? "Failed to save note." };
  }

  revalidatePath(`/leads/${leadId}`);
  return {};
}

export async function assignLead(
  leadId: string,
  agentId: string | null,
): Promise<{ error?: string }> {
  if (process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL) {
    revalidatePath(`/leads/${leadId}`);
    return {};
  }

  const res = await fetch(
    `${process.env.INTERNAL_API_URL}/api/v1/leads/${leadId}/assign`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: agentId }),
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      detail?: { message?: string };
    };
    return { error: body.detail?.message ?? "Failed to assign lead." };
  }

  revalidatePath(`/leads/${leadId}`);
  return {};
}
