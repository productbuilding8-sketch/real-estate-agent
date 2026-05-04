"use client";

import type React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  UserCog,
  CheckSquare,
  Settings,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/cn";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
};

const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/team", label: "Team", icon: UserCog },
  { href: "/tasks", label: "Tasks", icon: CheckSquare, disabled: true },
  { href: "/settings", label: "Settings", icon: Settings, disabled: true },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-60 flex-col bg-gray-900">
      {/* Brand */}
      <div className="flex h-16 items-center gap-2.5 px-5 border-b border-gray-800">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-semibold text-white">DealFlow AI</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon, disabled }) => {
          const isActive = !disabled && (pathname === href || pathname.startsWith(`${href}/`));
          const itemClass = cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            isActive
              ? "bg-indigo-600 text-white"
              : "text-gray-400 hover:bg-gray-800 hover:text-white",
            disabled && "opacity-40 cursor-not-allowed"
          );
          const children = (
            <>
              <Icon className="w-4 h-4 shrink-0" />
              {label}
              {disabled && (
                <span className="ml-auto text-[10px] font-normal text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded">
                  soon
                </span>
              )}
            </>
          );

          return disabled ? (
            <span key={href} className={itemClass}>
              {children}
            </span>
          ) : (
            <Link key={href} href={href} className={itemClass}>
              {children}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-gray-800">
        <p className="px-3 text-[10px] text-gray-600 uppercase tracking-wider">
          v0.1.0 — alpha
        </p>
      </div>
    </aside>
  );
}
