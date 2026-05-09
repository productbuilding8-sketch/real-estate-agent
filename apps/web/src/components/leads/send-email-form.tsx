"use client";

import { useState, useTransition } from "react";
import { Mail, X, Loader2, Send } from "lucide-react";
import { sendEmail } from "@/app/(authenticated)/leads/[id]/actions";
import { cn } from "@/lib/cn";

interface SendEmailFormProps {
  leadId: string;
  leadEmail: string | null;
}

export function SendEmailForm({ leadId, leadEmail }: SendEmailFormProps) {
  const [open, setOpen] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [isPending, startTransition] = useTransition();

  function handleOpen() {
    setSubject("");
    setBody("");
    setError(null);
    setSent(false);
    setOpen(true);
  }

  function handleClose() {
    if (isPending) return;
    setOpen(false);
  }

  function handleSend() {
    if (!subject.trim() || !body.trim() || isPending) return;
    setError(null);
    startTransition(async () => {
      const result = await sendEmail(leadId, subject, body);
      if (result.error) {
        setError(result.error);
      } else {
        setSent(true);
        setTimeout(() => {
          setOpen(false);
          setSent(false);
        }, 1500);
      }
    });
  }

  const subjectOver = subject.length > 200;
  const bodyOver = body.length > 5000;
  const canSend = subject.trim().length > 0 && body.trim().length > 0 && !subjectOver && !bodyOver;

  return (
    <>
      <button
        onClick={handleOpen}
        disabled={!leadEmail}
        title={leadEmail ? "Send email" : "No email address on file"}
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
          "border border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300",
          "disabled:opacity-40 disabled:cursor-not-allowed",
        )}
      >
        <Mail className="w-3.5 h-3.5" />
        Send email
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40 bg-black/30" onClick={handleClose} />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4 text-indigo-500" />
                  <h2 className="text-sm font-semibold text-gray-900">Send email</h2>
                </div>
                <button
                  onClick={handleClose}
                  disabled={isPending}
                  className="rounded-md p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-40"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Body */}
              <div className="px-5 py-4 space-y-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">To</p>
                  <p className="text-sm text-gray-700 font-medium">{leadEmail}</p>
                </div>

                <div>
                  <label className="text-xs text-gray-500 block mb-1">Subject</label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => { setSubject(e.target.value); setError(null); }}
                    disabled={isPending || sent}
                    placeholder="e.g. Following up on your property inquiry"
                    className={cn(
                      "w-full rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400",
                      "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
                      "disabled:opacity-60",
                      subjectOver ? "border-red-300" : "border-gray-200",
                    )}
                  />
                  {subjectOver && (
                    <p className="text-xs text-red-500 mt-1">{subject.length - 200} chars over limit</p>
                  )}
                </div>

                <div>
                  <label className="text-xs text-gray-500 block mb-1">Message</label>
                  <textarea
                    value={body}
                    onChange={(e) => { setBody(e.target.value); setError(null); }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && canSend) handleSend();
                    }}
                    disabled={isPending || sent}
                    placeholder="Write your message… (Ctrl+Enter to send)"
                    rows={6}
                    className={cn(
                      "w-full rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400",
                      "resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
                      "disabled:opacity-60",
                      bodyOver ? "border-red-300" : "border-gray-200",
                    )}
                  />
                  <p className={cn("text-xs mt-1", bodyOver ? "text-red-500" : "text-gray-400")}>
                    {bodyOver ? `${body.length - 5000} chars over limit` : `${5000 - body.length} remaining`}
                  </p>
                </div>

                {error && <p className="text-xs text-red-600">{error}</p>}
              </div>

              {/* Footer */}
              <div className="px-5 py-4 border-t border-gray-100 flex justify-end gap-3">
                <button
                  onClick={handleClose}
                  disabled={isPending}
                  className="rounded-lg px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSend}
                  disabled={!canSend || isPending || sent}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-sm font-semibold transition-colors",
                    sent
                      ? "bg-green-600 text-white"
                      : "bg-indigo-600 text-white hover:bg-indigo-500",
                    "disabled:opacity-50 disabled:cursor-not-allowed",
                  )}
                >
                  {isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {!isPending && !sent && <Send className="w-3.5 h-3.5" />}
                  {sent ? "Sent!" : isPending ? "Sending…" : "Send"}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
