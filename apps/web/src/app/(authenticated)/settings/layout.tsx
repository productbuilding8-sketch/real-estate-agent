import type { ReactNode } from "react";
import Link from "next/link";
import { Puzzle, SlidersHorizontal } from "lucide-react";

const settingsSections = [
  { href: "/settings/general", label: "General", icon: SlidersHorizontal },
  { href: "/settings/integrations", label: "Integrations", icon: Puzzle },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-0.5">Manage your workspace configuration</p>
      </div>

      <div className="flex gap-6">
        {/* Settings sub-nav */}
        <nav className="w-48 shrink-0 space-y-0.5">
          {settingsSections.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors"
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0">{children}</div>
      </div>
    </div>
  );
}
