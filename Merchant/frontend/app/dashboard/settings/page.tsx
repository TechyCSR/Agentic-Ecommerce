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
import { useCurrentUser } from "@/lib/queries/use-current-user";
import { useUpdateMerchant } from "@/lib/queries/use-merchant";

export default function SettingsPage() {
  const { data: user, isLoading } = useCurrentUser();
  const updateMerchant = useUpdateMerchant();
  const merchant = user?.merchant;

  const [form, setForm] = useState({
    business_name: "",
    legal_name: "",
    description: "",
    email: "",
    phone: "",
    website_url: "",
  });
  const [syncedMerchantId, setSyncedMerchantId] = useState<string | null>(null);

  if (merchant && merchant.id !== syncedMerchantId) {
    setSyncedMerchantId(merchant.id);
    setForm({
      business_name: merchant.business_name,
      legal_name: merchant.legal_name ?? "",
      description: merchant.description ?? "",
      email: merchant.email ?? "",
      phone: merchant.phone ?? "",
      website_url: merchant.website_url ?? "",
    });
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    try {
      await updateMerchant.mutateAsync(form);
      toast.success("Merchant profile updated.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update merchant");
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!merchant) return null;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your merchant profile information.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Merchant Profile</CardTitle>
            <CardDescription>
              This information identifies your business across the platform.
            </CardDescription>
          </div>
          <Badge variant={merchant.status === "ACTIVE" ? "default" : "outline"}>
            {merchant.status}
          </Badge>
        </CardHeader>
        <form onSubmit={handleSave}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Business name</Label>
              <Input
                value={form.business_name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, business_name: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Legal name</Label>
              <Input
                value={form.legal_name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, legal_name: e.target.value }))
                }
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
                <Label>Email</Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, email: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label>Phone</Label>
                <Input
                  value={form.phone}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, phone: e.target.value }))
                  }
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Website</Label>
              <Input
                value={form.website_url}
                onChange={(e) =>
                  setForm((f) => ({ ...f, website_url: e.target.value }))
                }
              />
            </div>
            <Button type="submit" disabled={updateMerchant.isPending}>
              {updateMerchant.isPending && (
                <Loader2 className="size-4 animate-spin" />
              )}
              Save changes
            </Button>
          </CardContent>
        </form>
      </Card>
    </div>
  );
}
