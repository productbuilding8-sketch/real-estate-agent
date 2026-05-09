import type { Metadata } from "next";
import { getSession } from "@/lib/auth";
import { ProfileForm } from "@/components/profile/profile-form";
import { redirect } from "next/navigation";

export const metadata: Metadata = { title: "Profile" };

export default async function ProfilePage() {
  const session = await getSession();
  if (!session) redirect("/login");

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-gray-900">Profile</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Manage your personal information and account settings.
        </p>
      </div>

      <ProfileForm user={session.user} />
    </div>
  );
}
