import type { Metadata } from "next";
import { CheckSquare, Clock, Zap } from "lucide-react";

export const metadata: Metadata = { title: "Tasks — DealFlow AI" };

export default function TasksPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-gray-900 tracking-tight">Tasks</h1>
        <p className="text-sm text-gray-500 mt-0.5">Manage follow-ups and action items for your leads</p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white shadow-card p-12 text-center">
        <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-50 mx-auto mb-4">
          <CheckSquare className="w-6 h-6 text-indigo-500" />
        </div>
        <h2 className="text-base font-semibold text-gray-900 mb-1">Tasks coming soon</h2>
        <p className="text-sm text-gray-500 max-w-sm mx-auto mb-6">
          Task management with due dates, assignments, and priority queues is in development.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-lg mx-auto text-left">
          {[
            { icon: CheckSquare, label: "Follow-up tasks", desc: "Per-lead action items with due dates" },
            { icon: Clock,       label: "Priority queue",  desc: "Auto-sorted by urgency and SLA" },
            { icon: Zap,         label: "AI suggestions",  desc: "Recommended next actions per lead" },
          ].map(({ icon: Icon, label, desc }) => (
            <div key={label} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
              <Icon className="w-4 h-4 text-indigo-400 mb-2" />
              <p className="text-xs font-semibold text-gray-700">{label}</p>
              <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
