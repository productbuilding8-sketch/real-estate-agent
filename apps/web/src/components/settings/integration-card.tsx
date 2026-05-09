import { CheckCircle2, XCircle, AlertCircle, Clock } from "lucide-react";
import type { IntegrationConnection } from "@/lib/api-client";
import { HubSpotConnectForm } from "@/components/settings/hubspot-connect-form";
import { TriggerSyncButton } from "@/components/settings/trigger-sync-button";
import { cn } from "@/lib/cn";

interface IntegrationCardProps {
  provider: string;
  name: string;
  description: string;
  logo: string;
  connection: IntegrationConnection | null;
}

function StatusPill({ status }: { status: IntegrationConnection["status"] | "disconnected" }) {
  const map = {
    connected: {
      icon: CheckCircle2,
      label: "Connected",
      className: "bg-green-50 text-green-700 ring-1 ring-green-200",
    },
    disconnected: {
      icon: XCircle,
      label: "Not connected",
      className: "bg-gray-50 text-gray-500 ring-1 ring-gray-200",
    },
    error: {
      icon: AlertCircle,
      label: "Error",
      className: "bg-red-50 text-red-600 ring-1 ring-red-200",
    },
  } as const;

  const { icon: Icon, label, className } = map[status] ?? map.disconnected;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        className,
      )}
    >
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}

function formatRelative(iso: string | null): string | null {
  if (!iso) return null;
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const CONNECT_FORMS: Record<string, React.ComponentType<{ isConnected: boolean }>> = {
  hubspot: HubSpotConnectForm,
};

export function IntegrationCard({
  provider,
  name,
  description,
  logo,
  connection,
}: IntegrationCardProps) {
  const status = connection?.status ?? "disconnected";
  const isConnected = status === "connected";
  const ConnectForm = CONNECT_FORMS[provider];
  const lastSync = formatRelative(connection?.last_sync_at ?? null);
  const lastError = formatRelative(connection?.last_error_at ?? null);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      {/* Header row */}
      <div className="flex items-start gap-4">
        {/* Logo */}
        <div className="h-10 w-10 rounded-lg bg-orange-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
          {logo}
        </div>

        {/* Name + description */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-900">{name}</span>
            <StatusPill status={status} />
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{description}</p>
        </div>

        {/* Actions */}
        {isConnected && (
          <div className="shrink-0">
            <TriggerSyncButton provider={provider} />
          </div>
        )}
      </div>

      {/* Last sync / error info */}
      {isConnected && (lastSync || lastError) && (
        <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
          {lastSync && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Last sync: {lastSync}
            </span>
          )}
          {lastError && connection?.last_error_msg && (
            <span className="flex items-center gap-1 text-red-500">
              <AlertCircle className="w-3 h-3" />
              Error: {connection.last_error_msg.slice(0, 80)}
            </span>
          )}
        </div>
      )}

      {/* Connect form */}
      {ConnectForm && (
        <div className={cn(isConnected && "mt-3 pt-3 border-t border-gray-100")}>
          {isConnected ? (
            <div className="flex justify-end">
              <ConnectForm isConnected={isConnected} />
            </div>
          ) : (
            <ConnectForm isConnected={isConnected} />
          )}
        </div>
      )}
    </div>
  );
}
