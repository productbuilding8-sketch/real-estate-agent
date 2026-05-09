"use server";

import { revalidatePath } from "next/cache";
import { apiHeaders } from "@/lib/api-client";

export async function addNote(
  leadId: string,
  text: string,
): Promise<{ error?: string }> {
  if (!text.trim() || text.length > 2000) {
    return { error: "Note must be between 1 and 2000 characters." };
  }

  if (process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL) {
    revalidatePath(`/leads/${leadId}`);
    return {};
  }

  const res = await fetch(
    `${process.env.INTERNAL_API_URL}/api/v1/leads/${leadId}/notes`,
    {
      method: "POST",
      headers: await apiHeaders(),
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
      headers: await apiHeaders(),
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

export async function sendEmail(
  leadId: string,
  subject: string,
  body: string,
): Promise<{ error?: string }> {
  if (!subject.trim() || !body.trim()) {
    return { error: "Subject and body are required." };
  }

  if (process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL) {
    revalidatePath(`/leads/${leadId}`);
    return {};
  }

  const res = await fetch(
    `${process.env.INTERNAL_API_URL}/api/v1/leads/${leadId}/email`,
    {
      method: "POST",
      headers: await apiHeaders(),
      body: JSON.stringify({ subject: subject.trim(), body: body.trim() }),
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const data = (await res.json().catch(() => ({}))) as {
      detail?: { message?: string };
    };
    return { error: data.detail?.message ?? "Failed to send email." };
  }

  revalidatePath(`/leads/${leadId}`);
  return {};
}

export async function updateLeadStatus(
  leadId: string,
  status: string,
): Promise<{ error?: string }> {
  if (process.env.MOCK_API === "true" || !process.env.INTERNAL_API_URL) {
    revalidatePath(`/leads/${leadId}`);
    return {};
  }

  const res = await fetch(
    `${process.env.INTERNAL_API_URL}/api/v1/leads/${leadId}/status`,
    {
      method: "PATCH",
      headers: await apiHeaders(),
      body: JSON.stringify({ status }),
      cache: "no-store",
    },
  );

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      detail?: { message?: string };
    };
    return { error: body.detail?.message ?? "Failed to update status." };
  }

  revalidatePath(`/leads/${leadId}`);
  return {};
}
