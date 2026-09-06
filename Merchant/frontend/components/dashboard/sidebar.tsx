"use client";

import { UserButton } from "@clerk/nextjs";
import { BookOpen, CreditCard, LayoutDashboard, Package, Settings, ShoppingBag, Store } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/products", label: "Products", icon: Package },
  { href: "/dashboard/orders", label: "Orders", icon: ShoppingBag },
  { href: "/dashboard/payments", label: "Payments", icon: CreditCard },
  { href: "/dashboard/store", label: "Store", icon: Store },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
  { href: "/docs", label: "Agent API Docs", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 flex-col border-r border-border/60 bg-sidebar md:flex">
      <div className="flex h-16 items-center border-b border-border/60 px-6">
        <Logo markClassName="size-7" textClassName="text-[15px]" />
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150",
                isActive
                  ? "bg-[color-mix(in_oklch,var(--agent-1),transparent_88%)] text-foreground"
                  : "text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground"
              )}
            >
              <item.icon
                className={cn("size-4", isActive && "text-[var(--agent-1)]")}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="flex items-center gap-3 border-t border-border/60 p-4">
        <UserButton />
        <span className="flex-1 text-sm text-muted-foreground">Account</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}
