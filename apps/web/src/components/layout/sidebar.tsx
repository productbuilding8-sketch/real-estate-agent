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
  { href: "/leads",     label: "Leads",     icon: Users },
  { href: "/team",      label: "Team",      icon: UserCog },
  { href: "/tasks",     label: "Tasks",     icon: CheckSquare },
  { href: "/settings",  label: "Settings",  icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-56 flex-col bg-gray-950 border-r border-white/5">
      {/* Brand */}
      <div className="flex h-14 items-center gap-2.5 px-4 border-b border-white/5">
        <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-indigo-600 shadow-lg shadow-indigo-900/50">
          <Zap className="w-3.5 h-3.5 text-white" strokeWidth={2.5} />
        </div>
        <span className="text-[13px] font-semibold text-white tracking-tight">DealFlow AI</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2.5 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon, disabled }) => {
          const isActive = !disabled && (pathname === href || pathname.startsWith(`${href}/`));
          const itemClass = cn(
            "relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium transition-all duration-150",
            isActive
              ? "bg-white/10 text-white"
              : "text-gray-400 hover:bg-white/5 hover:text-gray-200",
            disabled && "opacity-40 cursor-not-allowed pointer-events-none"
          );

          const inner = (
            <>
              {isActive && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r-full bg-indigo-400" />
              )}
              <Icon className="w-4 h-4 shrink-0" />
              {label}
              {disabled && (
                <span className="ml-auto text-[10px] font-normal text-gray-600 bg-white/5 px-1.5 py-0.5 rounded-sm">
                  soon
                </span>
              )}
            </>
          );

          return disabled ? (
            <span key={href} className={itemClass}>{inner}</span>
          ) : (
            <Link key={href} href={href} className={itemClass}>{inner}</Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/5">
        <p className="text-[10px] text-gray-600 tracking-widest uppercase font-medium">v0.1 alpha</p>
      </div>
    </aside>
  );
}
