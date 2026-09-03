"use client";

import { AlertTriangle, Boxes, CheckCircle2, IndianRupee, Package, ShoppingBag, Truck } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import { formatMoney } from "@/lib/money";
import { useOrderStats } from "@/lib/queries/use-orders";
import { useProductStats } from "@/lib/queries/use-product-stats";
import { useCurrentUser } from "@/lib/queries/use-current-user";

export default function DashboardPage() {
  const { data: user } = useCurrentUser();
  const { data: stats, isLoading } = useProductStats();
  const { data: orderStats } = useOrderStats();

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
          <StatCard
            title="Total Products"
            value={stats?.total_products ?? 0}
            icon={Package}
          />
          <StatCard
            title="Active Products"
            value={stats?.active_products ?? 0}
            icon={CheckCircle2}
          />
          <StatCard
            title="Out of Stock"
            value={stats?.out_of_stock_products ?? 0}
            icon={AlertTriangle}
          />
          <StatCard
            title="Total Inventory"
            value={stats?.total_inventory ?? 0}
            icon={Boxes}
          />
        </div>
      )}

      <div>
        <h2 className="mb-4 text-lg font-semibold tracking-tight">Sales</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Revenue"
            value={formatMoney(
              orderStats?.revenue_amount ?? 0,
              orderStats?.currency ?? "INR"
            )}
            icon={IndianRupee}
            hint="From paid orders"
          />
          <StatCard
            title="Orders Received"
            value={orderStats?.total_orders ?? 0}
            icon={ShoppingBag}
          />
          <StatCard
            title="Awaiting Fulfillment"
            value={orderStats?.awaiting_fulfillment ?? 0}
            icon={Truck}
          />
          <StatCard
            title="Delivered"
            value={orderStats?.delivered ?? 0}
            icon={CheckCircle2}
          />
        </div>
      </div>
    </div>
  );
}
