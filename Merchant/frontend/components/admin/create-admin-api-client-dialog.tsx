"use client";

import { Check, Copy, KeyRound, Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ApiClientInstance } from "@/lib/api";
import { useCreateAdminApiClient } from "@/lib/queries/use-admin-api-clients";

const AVAILABLE_SCOPES = [
  { value: "catalog:read", label: "catalog:read — search the catalog" },
  { value: "product:read", label: "product:read — read individual products" },
];

export function CreateAdminApiClientDialog({ api }: { api: ApiClientInstance }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [clientType, setClientType] = useState("AUTHORIZED_AGENT");
  const [scopes, setScopes] = useState<string[]>([
    "catalog:read",
    "product:read",
  ]);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const createClient = useCreateAdminApiClient(api);

  function toggleScope(scope: string) {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    );
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Client name is required.");
      return;
    }
    try {
      const client = await createClient.mutateAsync({
        name,
        client_type: clientType,
        scopes,
      });
      setCreatedKey(client.api_key);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create API client");
    }
  }

  function handleCopy() {
    if (!createdKey) return;
    navigator.clipboard.writeText(createdKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleClose(nextOpen: boolean) {
    setOpen(nextOpen);
    if (!nextOpen) {
      setName("");
      setClientType("AUTHORIZED_AGENT");
      setScopes(["catalog:read", "product:read"]);
      setCreatedKey(null);
      setCopied(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogTrigger render={<Button />}>
        <KeyRound className="size-4" /> Create Central API Key
      </DialogTrigger>
      <DialogContent>
        {createdKey ? (
          <>
            <DialogHeader>
              <DialogTitle>API key created</DialogTitle>
              <DialogDescription>
                Copy this key now. For security, it will never be shown again —
                only a masked version will be visible afterward. It grants
                read access across every merchant&apos;s agent-searchable
                catalog.
              </DialogDescription>
            </DialogHeader>
            <div className="flex items-center gap-2 rounded-md border bg-muted p-3">
              <code className="flex-1 truncate text-sm">{createdKey}</code>
              <Button type="button" size="icon" variant="ghost" onClick={handleCopy}>
                {copied ? (
                  <Check className="size-4 text-green-600" />
                ) : (
                  <Copy className="size-4" />
                )}
              </Button>
            </div>
            <DialogFooter>
              <Button onClick={() => handleClose(false)}>Done</Button>
            </DialogFooter>
          </>
        ) : (
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle>Create Central API Client</DialogTitle>
              <DialogDescription>
                Issue a scoped, platform-wide API key for an authorized
                agent or partner integration. It is not tied to any single
                merchant.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-1.5">
                <Label>Client name</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Shopping Agent — Production"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Client type</Label>
                <Select
                  value={clientType}
                  onValueChange={(value) => setClientType(value ?? "AUTHORIZED_AGENT")}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="INTERNAL_AGENT">Internal Agent</SelectItem>
                    <SelectItem value="AUTHORIZED_AGENT">
                      Authorized Agent
                    </SelectItem>
                    <SelectItem value="PARTNER">Partner</SelectItem>
                    <SelectItem value="DEVELOPER">Developer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Scopes</Label>
                {AVAILABLE_SCOPES.map((scope) => (
                  <label
                    key={scope.value}
                    className="flex items-center gap-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={scopes.includes(scope.value)}
                      onChange={() => toggleScope(scope.value)}
                      className="size-4"
                    />
                    {scope.label}
                  </label>
                ))}
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" disabled={createClient.isPending}>
                {createClient.isPending && (
                  <Loader2 className="size-4 animate-spin" />
                )}
                Create key
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
