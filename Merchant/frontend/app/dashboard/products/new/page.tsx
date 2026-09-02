"use client";

import { Loader2, Star, Trash2 } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { CategoryPicker } from "@/components/products/category-picker";
import { ImageUploadButton } from "@/components/products/image-upload-button";
import {
  VariantDraftList,
  emptyVariantDraft,
  variantDraftsToPayload,
  type VariantDraft,
} from "@/components/products/variant-draft-list";
import { useCreateProduct } from "@/lib/queries/use-products";
import { useStores } from "@/lib/queries/use-stores";

interface DraftImage {
  image_url: string;
  cloudinary_public_id: string;
  is_primary: boolean;
}

export default function NewProductPage() {
  const router = useRouter();
  const { data: stores } = useStores();
  const createProduct = useCreateProduct();

  const [storeId, setStoreId] = useState<string>("");
  const [name, setName] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [description, setDescription] = useState("");
  const [brand, setBrand] = useState("");
  const [status, setStatus] = useState("DRAFT");
  const [isAgentSearchable, setIsAgentSearchable] = useState(true);
  const [categoryIds, setCategoryIds] = useState<string[]>([]);
  const [images, setImages] = useState<DraftImage[]>([]);
  const [variants, setVariants] = useState<VariantDraft[]>([emptyVariantDraft()]);

  const activeStoreId = storeId || stores?.[0]?.id || "";
  const activeStore = stores?.find((s) => s.id === activeStoreId);
  const currency = activeStore?.currency ?? "INR";

  function handleImageUploaded(result: {
    image_url: string;
    cloudinary_public_id: string;
  }) {
    setImages((prev) => [
      ...prev,
      { ...result, is_primary: prev.length === 0 },
    ]);
  }

  function setPrimaryImage(index: number) {
    setImages((prev) => prev.map((img, i) => ({ ...img, is_primary: i === index })));
  }

  function removeImage(index: number) {
    setImages((prev) => {
      const next = prev.filter((_, i) => i !== index);
      if (next.length > 0 && !next.some((img) => img.is_primary)) {
        next[0].is_primary = true;
      }
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!activeStoreId) {
      toast.error("Please create a store before adding products.");
      return;
    }
    if (!name.trim()) {
      toast.error("Product name is required.");
      return;
    }

    const variantPayload = variantDraftsToPayload(variants, currency);
    if (variantPayload.length === 0) {
      toast.error("At least one variant with SKU and price is required.");
      return;
    }

    try {
      const product = await createProduct.mutateAsync({
        store_id: activeStoreId,
        name,
        short_description: shortDescription || undefined,
        description: description || undefined,
        brand: brand || undefined,
        status,
        is_agent_searchable: isAgentSearchable,
        category_ids: categoryIds,
        variants: variantPayload,
        images: images.map((img, i) => ({
          image_url: img.image_url,
          cloudinary_public_id: img.cloudinary_public_id,
          is_primary: img.is_primary,
          position: i,
        })),
      });
      toast.success("Product created successfully.");
      router.push(`/dashboard/products/${product.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create product");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Add Product</h1>
        <p className="text-muted-foreground">
          Fill in the details below to list a new product in your catalog.
        </p>
      </div>

      {stores && stores.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Store</CardTitle>
          </CardHeader>
          <CardContent>
            <Select
              value={activeStoreId}
              onValueChange={(value) => setStoreId(value ?? "")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a store" />
              </SelectTrigger>
              <SelectContent>
                {stores.map((store) => (
                  <SelectItem key={store.id} value={store.id}>
                    {store.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Basic Information</CardTitle>
          <CardDescription>The core details shoppers will see.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="name">Product name</Label>
            <Input
              id="name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Mechanical Keyboard K8"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="short_description">Short description</Label>
            <Input
              id="short_description"
              value={shortDescription}
              onChange={(e) => setShortDescription(e.target.value)}
              placeholder="Mechanical keyboard suitable for programming"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="description">Full description</Label>
            <Textarea
              id="description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the product in detail..."
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="brand">Brand</Label>
            <Input
              id="brand"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="KeyPro"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Images</CardTitle>
          <CardDescription>
            Upload multiple images. The first image is used as the main image
            unless you set another as primary.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            {images.map((img, index) => (
              <div
                key={img.cloudinary_public_id + index}
                className="group relative size-24 overflow-hidden rounded-md border"
              >
                <Image
                  src={img.image_url}
                  alt="Product"
                  fill
                  unoptimized
                  className="object-cover"
                />
                {img.is_primary && (
                  <span className="absolute left-1 top-1 rounded bg-primary px-1.5 py-0.5 text-[10px] font-medium text-primary-foreground">
                    Main
                  </span>
                )}
                <div className="absolute inset-x-0 bottom-0 flex items-center justify-center gap-1 bg-black/60 p-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={() => setPrimaryImage(index)}
                    className="rounded p-1 text-white hover:bg-white/20"
                    title="Set as primary"
                  >
                    <Star className="size-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => removeImage(index)}
                    className="rounded p-1 text-white hover:bg-white/20"
                    title="Remove"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          <ImageUploadButton onUploaded={handleImageUploaded} label="Upload Image" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Category</CardTitle>
        </CardHeader>
        <CardContent>
          <CategoryPicker selectedIds={categoryIds} onChange={setCategoryIds} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pricing, Variants &amp; Inventory</CardTitle>
          <CardDescription>
            Every product needs at least one variant with a SKU, price, and
            stock quantity.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <VariantDraftList
            variants={variants}
            onChange={setVariants}
            currency={currency}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Agent Availability</CardTitle>
          <CardDescription>
            Control whether this product can be discovered by authorized AI
            shopping agents.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-md border p-4">
            <div>
              <p className="text-sm font-medium">Agent searchable</p>
              <p className="text-sm text-muted-foreground">
                Active products marked as agent searchable will appear in the
                agent catalog API.
              </p>
            </div>
            <Switch
              checked={isAgentSearchable}
              onCheckedChange={setIsAgentSearchable}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Product status</Label>
            <Select
              value={status}
              onValueChange={(value) => setStatus(value ?? "DRAFT")}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="DRAFT">Draft</SelectItem>
                <SelectItem value="ACTIVE">Active</SelectItem>
                <SelectItem value="INACTIVE">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push("/dashboard/products")}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={createProduct.isPending}>
          {createProduct.isPending && <Loader2 className="size-4 animate-spin" />}
          Create Product
        </Button>
      </div>
    </form>
  );
}
