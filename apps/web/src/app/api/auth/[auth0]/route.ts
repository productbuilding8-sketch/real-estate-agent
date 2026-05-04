import { NextRequest, NextResponse } from "next/server";
import { isMockAuth, MOCK_USER } from "@/lib/auth";

// Mock handler: login → /dashboard, logout → /login, me → mock user JSON
function mockHandler(request: NextRequest): NextResponse {
  const { pathname } = new URL(request.url);
  const action = pathname.split("/").pop(); // login | logout | callback | me

  if (action === "login" || action === "callback") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  if (action === "logout") {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (action === "me") {
    return NextResponse.json(MOCK_USER);
  }
  return new NextResponse(null, { status: 404 });
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  if (isMockAuth()) return mockHandler(request);

  const { handleAuth } = await import("@auth0/nextjs-auth0");
  return handleAuth()(request) as Promise<NextResponse>;
}
