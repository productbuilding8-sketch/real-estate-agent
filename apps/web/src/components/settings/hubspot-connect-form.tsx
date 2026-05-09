"use client";

import { useState, useTransition } from "react";
import { Loader2, Eye, EyeOff } from "lucide-react";
import {
  connectIntegration,
  disconnectIntegration,
} from "@/app/(authenticated)/settings/integrations/actions";
import { cn } from "@/lib/cn";

interface HubSpotConnectFormProps {
  isConnected: boolean;
}

export function HubSpotConnectForm({ isConnected }: HubSpotConnectFormProps) {
  const [open, setOpen] = useState(!isConnected);
  const [accessToken, setAccessToken] = useState("");
  const [portalId, setPortalId] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleConnect(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    startTransition(async () => {
      const res = await connectIntegration("hubspot", accessToken, portalId || undefined);
      if (res.error) {
        setError(res.error);
      } else {
        setOpen(false);
        setAccessToken("");
        setPortalId("");
      }
    });
  }

  function handleDisconnect() {
    setError(null);
    startTransition(async () => {
      const res = await disconnectIntegration("hubspot");
      if (res.error) setError(res.error);
    });
  }

  if (isConnected && !open) {
    return (
      <div className="flex items-center gap-2">
        <button
          onClick={handleDisconnect}
          disabled={isPending}
          className={cn(
            "text-xs text-red-600 hover:text-red-700 hover:underline transition-colors",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
        >
          {isPending ? "Disconnecting…" : "Disconnect"}
        </button>
        <span className="text-gray-300">|</span>
        <button
          onClick={() => setOpen(true)}
          className="text-xs text-indigo-600 hover:underline"
        >
          Update token
        </button>
        {error && <span className="text-xs text-red-500 ml-1">{error}</span>}
      </div>
    );
  }

  return (
    <form onSubmit={handleConnect} className="mt-4 space-y-3">
      <div className="space-y-1">
        <label className="block text-xs font-medium text-gray-700">
          Private App Access Token
          <span className="text-red-500 ml-0.5">*</span>
        </label>
        <div className="relative">
          <input
            type={showToken ? "text" : "password"}
            value={accessToken}
            onChange={(e) => setAccessToken(e.target.value)}
            placeholder="pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            required
            disabled={isPending}
            className={cn(
              "w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900",
              "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500",
              "disabled:opacity-60 pr-9",
            )}
          />
          <button
            type="button"
            onClick={() => setShowToken((v) => !v)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-xs text-gray-400">
          Found in HubSpot → Settings → Integrations → Private Apps.
        </p>
      </div>

      <div className="space-y-1">
        <label className="block text-xs font-medium text-gray-700">
          Portal ID <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <input
          type="text"
          value={portalId}
          onChange={(e) => setPortalId(e.target.value)}
          placeholder="12345678"
          disabled={isPending}
          className={cn(
            "w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900",
            "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500",
            "disabled:opacity-60",
          )}
        />
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={isPending || !accessToken.trim()}
          className={cn(
            "inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium",
            "bg-indigo-600 text-white hover:bg-indigo-700 transition-colors",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
        >
          {isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          {isPending ? "Connecting…" : "Connect HubSpot"}
        </button>
        {(isConnected || open) && !isPending && (
          <button
            type="button"
            onClick={() => { setOpen(false); setError(null); }}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
