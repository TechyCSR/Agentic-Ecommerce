"use client";

import { AlertTriangle, Boxes, CheckCircle2, Package } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import { useProducts } from "@/lib/queries/use-products";
import { useCurrentUser } from "@/lib/queries/use-current-user";

export default function DashboardPage() {
  const { data: user } = useCurrentUser();
  const { data, isLoading } = useProducts({ limit: 100 });

  const products = data?.data ?? [];
  const totalProducts = data?.meta?.total ?? products.length;
  const activeProducts = products.filter((p) => p.status === "ACTIVE").length;
  const outOfStockProducts = products.filter(
    (p) => p.total_stock === 0
  ).length;
  const totalInventory = products.reduce((sum, p) => sum + p.total_stock, 0);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome back{user?.first_name ? `, ${user.first_name}` : ""}
          </h1>
          <p className="text-muted-foreground">
            Here&apos;s what&apos;s happening with{" "}
            {user?.merchant?.business_name ?? "your store"} today.
          </p>
        </div>
        <Button render={<Link href="/dashboard/products/new" />}>
          Add Product
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Total Products" value={totalProducts} icon={Package} />
          <StatCard
            title="Active Products"
            value={activeProducts}
            icon={CheckCircle2}
          />
          <StatCard
            title="Out of Stock"
            value={outOfStockProducts}
            icon={AlertTriangle}
          />
          <StatCard title="Total Inventory" value={totalInventory} icon={Boxes} />
        </div>
      )}
    </div>
  );
}
