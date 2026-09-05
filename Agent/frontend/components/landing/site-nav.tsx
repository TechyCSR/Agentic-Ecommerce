import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";

import { Mark } from "@/components/brand/mark";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

/**
 * Resolved on the server so the nav arrives complete.
 *
 * Clerk's client-side <Show> renders nothing until auth settles, which left
 * the landing page's nav visibly missing its buttons for the first few
 * hundred milliseconds — the worst place in the product to look unfinished.
 */
export async function SiteNav() {
  const { userId } = await auth();

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          <Mark />
          <span className="font-display text-[15px] font-semibold">Agentic Commerce</span>
        </Link>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          {userId ? (
            <>
              <Button size="sm" render={<Link href="/chat">Open the agent</Link>} />
              <UserButton />
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" render={<Link href="/sign-in">Sign in</Link>} />
              <Button size="sm" render={<Link href="/sign-up">Create account</Link>} />
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
