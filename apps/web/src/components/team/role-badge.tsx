import { cn } from "@/lib/cn";

export type RoleSlug =
  | "owner_admin"
  | "manager"
  | "agent"
  | "implementation_admin"
  | "auditor";

const ROLE_CONFIG: Record<RoleSlug, { label: string; className: string }> = {
  owner_admin: {
    label: "Owner / Admin",
    className: "bg-purple-100 text-purple-700 ring-purple-200",
  },
  manager: {
    label: "Manager",
    className: "bg-blue-100 text-blue-700 ring-blue-200",
  },
  agent: {
    label: "Agent",
    className: "bg-green-100 text-green-700 ring-green-200",
  },
  implementation_admin: {
    label: "Implementation",
    className: "bg-amber-100 text-amber-700 ring-amber-200",
  },
  auditor: {
    label: "Auditor",
    className: "bg-gray-100 text-gray-600 ring-gray-200",
  },
};

interface RoleBadgeProps {
  role: RoleSlug;
  className?: string;
}

export function RoleBadge({ role, className }: RoleBadgeProps) {
  const config = ROLE_CONFIG[role] ?? {
    label: role,
    className: "bg-gray-100 text-gray-600 ring-gray-200",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}

export const ROLE_OPTIONS: { value: RoleSlug; label: string }[] = [
  { value: "owner_admin", label: "Owner / Admin" },
  { value: "manager", label: "Manager" },
  { value: "agent", label: "Agent" },
  { value: "implementation_admin", label: "Implementation Admin" },
  { value: "auditor", label: "Auditor" },
];
