/**
 * Auth abstraction layer.
 *
 * When MOCK_AUTH=true (local dev without Auth0 credentials), returns a
 * hardcoded session so the rest of the app works identically to production.
 * Switch to real Auth0 by removing MOCK_AUTH or setting it to "false".
 *
 * TODO: Remove mock path once Auth0 tenant is provisioned.
 */

export type MockSession = {
  user: {
    sub: string;
    name: string;
    email: string;
    email_verified: boolean;
    picture: string | null;
  };
};

export const MOCK_USER = {
  sub: "mock|demo_agent_001",
  name: "Demo Agent",
  email: "demo@dealflow.dev",
  email_verified: true,
  picture: null,
} as const;

const MOCK_SESSION: MockSession = { user: MOCK_USER };

export function isMockAuth(): boolean {
  return process.env.MOCK_AUTH === "true";
}

/**
 * Server-component session access.
 * Returns null when unauthenticated (real Auth0) or always returns mock session.
 */
export async function getSession(): Promise<MockSession | null> {
  if (isMockAuth()) return MOCK_SESSION;

  const { getSession: getAuth0Session } = await import("@auth0/nextjs-auth0");
  return (getAuth0Session() as Promise<MockSession | null>);
}
