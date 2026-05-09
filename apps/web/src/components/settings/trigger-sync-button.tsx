"use client";

import { useState, useTransition } from "react";
import { RefreshCw, Loader2, CheckCircle2 } from "lucide-react";
import { triggerSync } from "@/app/(authenticated)/settings/integrations/actions";
import { cn } from "@/lib/cn";

interface TriggerSyncButtonProps {
  provider: string;
}

export function TriggerSyncButton({ provider }: TriggerSyncButtonProps) {
  const [isPending, startTransition] = useTransition();
  const [result, setResult] = useState<"idle" | "ok" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  function handleClick() {
    setResult("idle");
    setErrorMsg(null);
    startTransition(async () => {
      const res = await triggerSync(provider);
      if (res.error) {
        setResult("error");
        setErrorMsg(res.error);
      } else {
        setResult("ok");
        setTimeout(() => setResult("idle"), 3000);
      }
    });
  }

  return (
    <div className="flex items-center gap-2">
      {result === "ok" && (
        <span className="flex items-center gap-1 text-xs text-green-600">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Sync queued
        </span>
      )}
      {result === "error" && errorMsg && (
        <span className="text-xs text-red-500">{errorMsg}</span>
      )}
      <button
        onClick={handleClick}
        disabled={isPending}
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
          "border border-gray-200 bg-white text-gray-700 hover:bg-gray-50",
          "disabled:opacity-50 disabled:cursor-not-allowed",
        )}
      >
        {isPending ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <RefreshCw className="w-3.5 h-3.5" />
        )}
        {isPending ? "Syncing…" : "Sync now"}
      </button>
    </div>
  );
}
