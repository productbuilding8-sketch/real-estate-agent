import { UserMenu } from "@/components/layout/user-menu";
import { TenantSwitcher } from "@/components/layout/tenant-switcher";

export function TopNav() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6">
      <TenantSwitcher />
      <UserMenu />
    </header>
  );
}
