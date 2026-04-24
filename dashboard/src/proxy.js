// src/middleware.ts
import { NextResponse } from "next/server";

// Define public and protected routes
const protectedRoutes = ["/dashboard", "/profile", "/settings"];
const publicRoutes = ["/login", "/signup", "/"];

export default async function middleware(req) {
  // 2. Check if the current route is protected or public
  const path = req.nextUrl.pathname;
  const isProtectedRoute = protectedRoutes.some((route) =>
    path.startsWith(route),
  );
  const isPublicRoute = publicRoutes.includes(path);

  // Decrypt/Verify the session from the cookie
  // provide a helper to get the session here.
  const cookie = req.cookies.get("session")?.value;
  const session = cookie ? /* verifySession(cookie) */ true : null;

  // Redirect to /login if the user is not authenticated
  if (isProtectedRoute && !session) {
    return NextResponse.redirect(new URL("/login", req.nextUrl));
  }

  // 5. Redirect to /dashboard if the user is authenticated
  if (isPublicRoute && session && !path.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/dashboard", req.nextUrl));
  }

  return NextResponse.next();
}

// Routes Middleware should not run on
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|.*\\.png$).*)"],
};
