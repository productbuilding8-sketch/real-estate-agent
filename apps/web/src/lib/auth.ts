/**
 * Auth abstraction layer.
 *
 * MOCK_AUTH=true  — returns a hardcoded session + "dev-token" access token.
 *                   API must have DEV_MODE=true to accept dev-token.
 * MOCK_AUTH=false — reads the real Auth0 session via @auth0/nextjs-auth0 and
 *                   forwards the JWT access token to the API.
 *                   Requires AUTH0_AUDIENCE to be set so Auth0 issues a signed JWT.
 */

export type AppSession = {
  user: {
    sub: string;
    name: string;
    email: string;
    email_verified: boolean;
    picture: string | null;
  };
  /** JWT access token forwarded to the API as Authorization: Bearer <token>. */
  accessToken: string;
};

export const MOCK_USER = {
  sub: "mock|demo_agent_001",
  name: "Demo Agent",
  email: "demo@dealflow.dev",
  email_verified: true,
  picture: null,
} as const;

const MOCK_SESSION: AppSession = {
  user: MOCK_USER,
  accessToken: "dev-token",
};

export function isMockAuth(): boolean {
  return process.env.MOCK_AUTH === "true";
}

/**
 * Server-component session access.
 * Returns null when unauthenticated (real Auth0 only).
 * Always returns the mock session when MOCK_AUTH=true.
 */
export async function getSession(): Promise<AppSession | null> {
  if (isMockAuth()) return MOCK_SESSION;

  const { getSession: auth0Session } = await import("@auth0/nextjs-auth0");
  const raw = await auth0Session();
  if (!raw) return null;

  return {
    user: {
      sub: raw.user.sub ?? "",
      name: raw.user.name ?? "",
      email: raw.user.email ?? "",
      email_verified: raw.user.email_verified ?? false,
      picture: raw.user.picture ?? null,
    },
    // accessToken is a signed JWT when AUTH0_AUDIENCE is configured.
    // Falls back to "dev-token" so local runs without Auth0 still work.
    accessToken: (raw.accessToken as string | undefined) ?? "dev-token",
  };
}

/**
 * Returns the Bearer token to include in API requests.
 * Safe to call from server components and server actions.
 */
export async function getAccessToken(): Promise<string> {
  const session = await getSession();
  return session?.accessToken ?? "dev-token";
}
