import { type NextRequest, NextFetchEvent, NextResponse } from "next/server";
import { withMiddlewareAuthRequired } from "@auth0/nextjs-auth0/edge";

const authMiddleware = withMiddlewareAuthRequired();

export function middleware(request: NextRequest, event: NextFetchEvent) {
  // Skip auth enforcement in mock mode — all routes are freely accessible
  if (process.env.MOCK_AUTH === "true") {
    return NextResponse.next();
  }
  return authMiddleware(request, event);
}

export const config = {
  matcher: [
    "/((?!api/auth|_next/static|_next/image|favicon.ico|login).*)",
  ],
};
