"use client";

import { useRef, useState, useTransition } from "react";
import { StickyNote, Loader2 } from "lucide-react";
import { addNote } from "@/app/(authenticated)/leads/[id]/actions";
import { cn } from "@/lib/cn";

interface AddNoteFormProps {
  leadId: string;
}

export function AddNoteForm({ leadId }: AddNoteFormProps) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [isPending, startTransition] = useTransition();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed || isPending) return;

    setError(null);
    setSaved(false);
    startTransition(async () => {
      const result = await addNote(leadId, trimmed);
      if (result.error) {
        setError(result.error);
      } else {
        setText("");
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
        textareaRef.current?.focus();
      }
    });
  }

  const remaining = 2000 - text.length;
  const overLimit = remaining < 0;

  return (
    <div className="border-t border-gray-100 pt-4 mt-4 space-y-2">
      <div className="flex gap-2 items-start">
        <StickyNote className="w-4 h-4 text-gray-400 mt-2 shrink-0" />
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setError(null);
            setSaved(false);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
          }}
          placeholder="Add a note… (Ctrl+Enter to save)"
          rows={2}
          disabled={isPending}
          className={cn(
            "flex-1 rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400",
            "resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500",
            "disabled:opacity-60",
            overLimit ? "border-red-300" : "border-gray-200",
          )}
        />
      </div>

      <div className="flex items-center justify-between pl-6">
        <span
          className={cn(
            "text-xs",
            overLimit ? "text-red-500 font-medium" : "text-gray-400",
          )}
        >
          {overLimit ? `${Math.abs(remaining)} over limit` : `${remaining} remaining`}
        </span>

        <div className="flex items-center gap-2">
          {saved && <span className="text-xs text-green-600">Saved</span>}
          {error && <span className="text-xs text-red-500">{error}</span>}
          <button
            onClick={handleSubmit}
            disabled={isPending || !text.trim() || overLimit}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              "bg-indigo-600 text-white hover:bg-indigo-700",
              "disabled:opacity-50 disabled:cursor-not-allowed",
            )}
          >
            {isPending && <Loader2 className="w-3 h-3 animate-spin" />}
            {isPending ? "Saving…" : "Add note"}
          </button>
        </div>
      </div>
    </div>
  );
}
