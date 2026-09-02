"use client";

import { Loader2, Store as StoreIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCurrentUser } from "@/lib/queries/use-current-user";
import { useCreateMerchant } from "@/lib/queries/use-merchant";
import { useCreateStore } from "@/lib/queries/use-stores";

export default function OnboardingPage() {
  const router = useRouter();
  const { data: user, isLoading } = useCurrentUser();
  const createMerchant = useCreateMerchant();
  const createStore = useCreateStore();

  const [step, setStep] = useState<1 | 2>(1);

  const [merchantForm, setMerchantForm] = useState({
    business_name: "",
    email: "",
    phone: "",
    website_url: "",
    description: "",
  });

  const [storeForm, setStoreForm] = useState({
    name: "",
    currency: "INR",
    country: "India",
  });

  useEffect(() => {
    if (!isLoading && user?.merchant) {
      router.replace("/dashboard");
    }
  }, [isLoading, user, router]);

  async function handleCreateMerchant(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createMerchant.mutateAsync({
        business_name: merchantForm.business_name,
        email: merchantForm.email || undefined,
        phone: merchantForm.phone || undefined,
        website_url: merchantForm.website_url || undefined,
        description: merchantForm.description || undefined,
      });
      setStep(2);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create merchant");
    }
  }

  async function handleCreateStore(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createStore.mutateAsync(storeForm);
      toast.success("Store created! Welcome to your dashboard.");
      router.replace("/dashboard");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create store");
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="flex items-center gap-2 text-primary">
            <StoreIcon className="size-5" />
            <span className="text-sm font-medium">
              Step {step} of 2
            </span>
          </div>
          <CardTitle className="text-2xl">
            {step === 1 ? "Create your merchant profile" : "Set up your first store"}
          </CardTitle>
          <CardDescription>
            {step === 1
              ? "Tell us about your business. You can update this later."
              : "Every merchant needs at least one store to list products."}
          </CardDescription>
        </CardHeader>

        {step === 1 ? (
          <form onSubmit={handleCreateMerchant}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="business_name">Business name</Label>
                <Input
                  id="business_name"
                  required
                  value={merchantForm.business_name}
                  onChange={(e) =>
                    setMerchantForm((f) => ({ ...f, business_name: e.target.value }))
                  }
                  placeholder="TechStore Pvt Ltd"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Business email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={merchantForm.email}
                    onChange={(e) =>
                      setMerchantForm((f) => ({ ...f, email: e.target.value }))
                    }
                    placeholder="hello@techstore.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    value={merchantForm.phone}
                    onChange={(e) =>
                      setMerchantForm((f) => ({ ...f, phone: e.target.value }))
                    }
                    placeholder="+91 98765 43210"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="website_url">Website</Label>
                <Input
                  id="website_url"
                  value={merchantForm.website_url}
                  onChange={(e) =>
                    setMerchantForm((f) => ({ ...f, website_url: e.target.value }))
                  }
                  placeholder="https://techstore.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={merchantForm.description}
                  onChange={(e) =>
                    setMerchantForm((f) => ({ ...f, description: e.target.value }))
                  }
                  placeholder="What does your business sell?"
                />
              </div>
            </CardContent>
            <CardFooter>
              <Button type="submit" className="w-full" disabled={createMerchant.isPending}>
                {createMerchant.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  "Continue"
                )}
              </Button>
            </CardFooter>
          </form>
        ) : (
          <form onSubmit={handleCreateStore}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="store_name">Store name</Label>
                <Input
                  id="store_name"
                  required
                  value={storeForm.name}
                  onChange={(e) =>
                    setStoreForm((f) => ({ ...f, name: e.target.value }))
                  }
                  placeholder="Tech Store"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="currency">Currency</Label>
                  <Input
                    id="currency"
                    value={storeForm.currency}
                    onChange={(e) =>
                      setStoreForm((f) => ({ ...f, currency: e.target.value }))
                    }
                    placeholder="INR"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="country">Country</Label>
                  <Input
                    id="country"
                    value={storeForm.country}
                    onChange={(e) =>
                      setStoreForm((f) => ({ ...f, country: e.target.value }))
                    }
                    placeholder="India"
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button type="submit" className="w-full" disabled={createStore.isPending}>
                {createStore.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  "Create store & continue"
                )}
              </Button>
            </CardFooter>
          </form>
        )}
      </Card>
    </div>
  );
}
