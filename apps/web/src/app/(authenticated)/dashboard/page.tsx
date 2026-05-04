import type { Metadata } from "next";
import { getSession } from "@/lib/auth";
import { Users, CheckSquare, TrendingUp, Clock } from "lucide-react";

export const metadata: Metadata = { title: "Dashboard" };

const stats = [
  { label: "Total Leads", value: "—", icon: Users, color: "bg-blue-50 text-blue-600" },
  { label: "Open Tasks", value: "—", icon: CheckSquare, color: "bg-amber-50 text-amber-600" },
  { label: "Conversion Rate", value: "—", icon: TrendingUp, color: "bg-green-50 text-green-600" },
  { label: "Avg Response Time", value: "—", icon: Clock, color: "bg-purple-50 text-purple-600" },
];

export default async function DashboardPage() {
  const session = await getSession();
  const firstName = session?.user?.name?.split(" ")[0] ?? "there";

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      {/* Welcome */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">
          Good morning, {firstName}
        </h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Here&apos;s what&apos;s happening with your leads today.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div
            key={label}
            className="rounded-xl bg-white border border-gray-200 p-5 flex items-start gap-4"
          >
            <div className={`rounded-lg p-2.5 ${color}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500">{label}</p>
              <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Coming soon placeholder */}
      <div className="rounded-xl bg-white border border-gray-200 border-dashed p-12 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gray-100 mb-4">
          <TrendingUp className="w-6 h-6 text-gray-400" />
        </div>
        <h3 className="text-sm font-semibold text-gray-900">Activity feed coming soon</h3>
        <p className="text-xs text-gray-500 mt-1 max-w-xs mx-auto">
          Real-time lead activity and AI qualification results will appear here.
        </p>
      </div>
    </div>
  );
}
