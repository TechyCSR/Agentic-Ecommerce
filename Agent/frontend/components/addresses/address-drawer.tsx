"use client";

import { Check, Loader2, MapPin, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  useAddresses,
  useCreateAddress,
  useDeleteAddress,
  useSetDefaultAddress,
} from "@/lib/queries/use-addresses";
import type { AddressPayload } from "@/lib/types";
import { cn } from "@/lib/utils";

const EMPTY: AddressPayload = {
  label: "",
  full_name: "",
  phone: "",
  line1: "",
  line2: "",
  city: "",
  state: "",
  postal_code: "",
};

export function AddressDrawer() {
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState<AddressPayload>(EMPTY);

  const { data: addresses, isLoading } = useAddresses(open);
  const createAddress = useCreateAddress();
  const setDefault = useSetDefaultAddress();
  const deleteAddress = useDeleteAddress();

  const hasNone = !isLoading && (addresses ?? []).length === 0;

  function field(key: keyof AddressPayload, label: string, required = false) {
    return (
      <div className="space-y-1">
        <Label className="text-xs" htmlFor={key}>
          {label}
          {required && <span className="text-destructive"> *</span>}
        </Label>
        <Input
          id={key}
          value={form[key] ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        />
      </div>
    );
  }

  async function save() {
    try {
      await createAddress.mutateAsync(form);
      setForm(EMPTY);
      setAdding(false);
      toast.success("Address saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't save that address");
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button variant="outline" size="sm" className="relative gap-1.5">
            <MapPin className="size-4" />
            <span className="hidden sm:inline">Addresses</span>
            {hasNone && (
              <span className="absolute -top-1 -right-1 size-2 rounded-full bg-amber-500" />
            )}
          </Button>
        }
      />
      <SheetContent className="flex flex-col p-0">
        <SheetHeader className="border-b">
          <SheetTitle>Delivery addresses</SheetTitle>
        </SheetHeader>

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            (addresses ?? []).map((address) => (
              <div
                key={address.id}
                className={cn(
                  "rounded-xl border p-3",
                  address.is_default && "border-primary/60 bg-primary/5"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">
                      {address.label || "Address"}
                      {address.is_default && (
                        <span className="ml-2 text-xs text-primary">Default</span>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">{address.full_name} · {address.phone}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{address.one_line}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() =>
                      deleteAddress.mutate(address.id, {
                        onError: (e) =>
                          toast.error(e instanceof Error ? e.message : "Couldn't remove it"),
                      })
                    }
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
                {!address.is_default && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => setDefault.mutate(address.id)}
                  >
                    <Check className="size-3.5" />
                    Deliver here
                  </Button>
                )}
              </div>
            ))
          )}

          {hasNone && !adding && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No addresses yet. Add one so the agent can place an order for you.
            </p>
          )}

          {adding ? (
            <div className="space-y-3 rounded-xl border p-3">
              {field("label", "Label (Home, Office)")}
              {field("full_name", "Full name", true)}
              {field("phone", "Phone", true)}
              {field("line1", "Address line 1", true)}
              {field("line2", "Address line 2")}
              <div className="grid grid-cols-2 gap-2">
                {field("city", "City", true)}
                {field("state", "State")}
              </div>
              {field("postal_code", "PIN code", true)}
              <div className="flex gap-2">
                <Button size="sm" onClick={save} disabled={createAddress.isPending}>
                  {createAddress.isPending && <Loader2 className="size-3.5 animate-spin" />}
                  Save address
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setAdding(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <Button variant="outline" className="w-full" onClick={() => setAdding(true)}>
              <Plus className="size-4" />
              Add an address
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
