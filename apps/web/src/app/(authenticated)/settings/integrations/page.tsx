import { getIntegrations } from "@/lib/api-client";
import { IntegrationCard } from "@/components/settings/integration-card";

export const metadata = { title: "Integrations — DealFlow AI" };

const PROVIDER_META: Record<string, { name: string; description: string; logo: string }> = {
  hubspot: {
    name: "HubSpot",
    description: "Sync contacts from your HubSpot CRM into DealFlow leads automatically.",
    logo: "HS",
  },
};

export default async function IntegrationsPage() {
  const connections = await getIntegrations().catch(() => []);

  const connectedMap = Object.fromEntries(connections.map((c) => [c.provider, c]));

  const providers = Object.keys(PROVIDER_META);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-900">CRM &amp; Data Sources</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          Connect external platforms to automatically import and sync leads.
        </p>
      </div>

      <div className="space-y-3">
        {providers.map((provider) => {
          const meta = PROVIDER_META[provider]!;
          const conn = connectedMap[provider] ?? null;
          return (
            <IntegrationCard
              key={provider}
              provider={provider}
              name={meta.name}
              description={meta.description}
              logo={meta.logo}
              connection={conn}
            />
          );
        })}
      </div>
    </div>
  );
}
