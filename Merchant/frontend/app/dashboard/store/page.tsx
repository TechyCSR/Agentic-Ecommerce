"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useStores, useUpdateStore } from "@/lib/queries/use-stores";

export default function StorePage() {
  const { data: stores, isLoading } = useStores();
  const updateStore = useUpdateStore();
  const store = stores?.[0];

  const [form, setForm] = useState({
    name: "",
    description: "",
    currency: "",
    country: "",
  });
  const [syncedStoreId, setSyncedStoreId] = useState<string | null>(null);

  if (store && store.id !== syncedStoreId) {
    setSyncedStoreId(store.id);
    setForm({
      name: store.name,
      description: store.description ?? "",
      currency: store.currency,
      country: store.country ?? "",
    });
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!store) return;
    try {
      await updateStore.mutateAsync({ storeId: store.id, payload: form });
      toast.success("Store updated.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update store");
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!store) {
    return <p className="text-muted-foreground">No store found.</p>;
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Store</h1>
        <p className="text-muted-foreground">
          Manage your store details. Slug:{" "}
          <span className="font-mono">{store.slug}</span>
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Store Details</CardTitle>
            <CardDescription>
              Visible to customers and used in the agent-readable catalog.
            </CardDescription>
          </div>
          <Badge variant={store.status === "ACTIVE" ? "default" : "outline"}>
            {store.status}
          </Badge>
        </CardHeader>
        <form onSubmit={handleSave}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Store name</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Textarea
                rows={3}
                value={form.description}
                onChange={(e) =>
                  setForm((f) => ({ ...f, description: e.target.value }))
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Currency</Label>
                <Input
                  value={form.currency}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, currency: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label>Country</Label>
                <Input
                  value={form.country}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, country: e.target.value }))
                  }
                />
              </div>
            </div>
            <Button type="submit" disabled={updateStore.isPending}>
              {updateStore.isPending && <Loader2 className="size-4 animate-spin" />}
              Save changes
            </Button>
          </CardContent>
        </form>
      </Card>
    </div>
  );
}
