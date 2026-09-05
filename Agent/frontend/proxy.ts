import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// The landing page is the pitch — it has to be readable before anyone has
// an account. Everything else still requires one.
const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    // Send signed-out visitors to sign-in. Without unauthenticatedUrl,
    // auth.protect() answers a bare 404 on non-API routes, so the landing
    // page looked broken to anyone not already signed in.
    await auth.protect({
      unauthenticatedUrl: new URL("/sign-in", req.url).toString(),
    });
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
