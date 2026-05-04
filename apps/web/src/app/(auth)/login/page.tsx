import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Sign In" };

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm space-y-8 px-6">
        {/* Brand */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-600 mb-4">
            <svg
              className="w-7 h-7 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">DealFlow AI</h1>
          <p className="mt-2 text-sm text-gray-500">
            Real estate lead management, powered by AI
          </p>
        </div>

        {/* Sign-in card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 space-y-6">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-gray-900">Sign in to your account</h2>
            <p className="text-sm text-gray-500">
              Securely authenticated via Auth0
            </p>
          </div>

          <Link
            href="/api/auth/login"
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 transition-colors"
          >
            Continue with Auth0
          </Link>
        </div>

        <p className="text-center text-xs text-gray-400">
          By signing in you agree to our terms of service
        </p>
      </div>
    </div>
  );
}
