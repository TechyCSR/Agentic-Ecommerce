"use client";

import { Loader2, Plus, Star, Trash2 } from "lucide-react";
import Image from "next/image";
import { useParams, useRouter } from "next/navigation";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { CategoryPicker } from "@/components/products/category-picker";
import { ImageUploadButton } from "@/components/products/image-upload-button";
import { formatMoney, majorToSmallestUnit } from "@/lib/money";
import {
  useAddImage,
  useAddVariant,
  useDeleteImage,
  useDeleteProduct,
  useDeleteVariant,
  useProduct,
  useProductStatusAction,
  useSetPrimaryImage,
  useUpdateProduct,
  useUpdateVariant,
} from "@/lib/queries/use-products";

export default function EditProductPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const productId = params.id;

  const { data: product, isLoading } = useProduct(productId);
  const updateProduct = useUpdateProduct();
  const statusAction = useProductStatusAction();
  const deleteProduct = useDeleteProduct();
  const addImage = useAddImage();
  const deleteImage = useDeleteImage();
  const setPrimaryImage = useSetPrimaryImage();
  const addVariant = useAddVariant();
  const updateVariant = useUpdateVariant();
  const deleteVariant = useDeleteVariant();

  const [name, setName] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [description, setDescription] = useState("");
  const [brand, setBrand] = useState("");
  const [isAgentSearchable, setIsAgentSearchable] = useState(true);
  const [categoryIds, setCategoryIds] = useState<string[]>([]);
  const [syncedProductId, setSyncedProductId] = useState<string | null>(null);

  const [newVariant, setNewVariant] = useState({
    sku: "",
    name: "",
    price: "",
    stock_quantity: "0",
  });

  if (product && product.id !== syncedProductId) {
    setSyncedProductId(product.id);
    setName(product.name);
    setShortDescription(product.short_description ?? "");
    setDescription(product.description ?? "");
    setBrand(product.brand ?? "");
    setIsAgentSearchable(product.is_agent_searchable);
    setCategoryIds(product.categories.map((c) => c.id));
  }

  if (isLoading || !product) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const currency = product.variants[0]?.currency ?? "INR";

  async function handleSaveDetails() {
    try {
      await updateProduct.mutateAsync({
        productId,
        payload: {
          name,
          short_description: shortDescription || undefined,
          description: description || undefined,
          brand: brand || undefined,
          is_agent_searchable: isAgentSearchable,
          category_ids: categoryIds,
        },
      });
      toast.success("Product updated.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update product");
    }
  }

  async function handleStatusChange(newStatus: string | null) {
    if (!newStatus) return;
    try {
      if (newStatus === "ACTIVE") {
        await statusAction.mutateAsync({ productId, action: "activate" });
      } else if (newStatus === "INACTIVE") {
        await statusAction.mutateAsync({ productId, action: "deactivate" });
      } else if (newStatus === "ARCHIVED") {
        await statusAction.mutateAsync({ productId, action: "archive" });
      }
      toast.success(`Product marked as ${newStatus.toLowerCase()}.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update status");
    }
  }

  async function handleDeleteProduct() {
    if (!confirm("Delete this product permanently? This cannot be undone.")) return;
    try {
      await deleteProduct.mutateAsync(productId);
      toast.success("Product deleted.");
      router.push("/dashboard/products");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete product");
    }
  }

  async function handleImageUploaded(result: {
    image_url: string;
    cloudinary_public_id: string;
  }) {
    try {
      await addImage.mutateAsync({
        productId,
        payload: { ...result, is_primary: (product?.images.length ?? 0) === 0 },
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add image");
    }
  }

  async function handleAddVariant(e: React.FormEvent) {
    e.preventDefault();
    if (!newVariant.sku || !newVariant.name) {
      toast.error("Variant name and SKU are required.");
      return;
    }
    try {
      await addVariant.mutateAsync({
        productId,
        payload: {
          sku: newVariant.sku,
          name: newVariant.name,
          price: majorToSmallestUnit(parseFloat(newVariant.price || "0")),
          currency,
          stock_quantity: parseInt(newVariant.stock_quantity || "0", 10),
        },
      });
      setNewVariant({ sku: "", name: "", price: "", stock_quantity: "0" });
      toast.success("Variant added.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add variant");
    }
  }

  async function handleStockChange(variantId: string, value: string) {
    const stock = parseInt(value || "0", 10);
    try {
      await updateVariant.mutateAsync({
        variantId,
        productId,
        payload: { stock_quantity: stock },
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update stock");
    }
  }

  async function handleDeleteVariant(variantId: string) {
    if (!confirm("Remove this variant?")) return;
    try {
      await deleteVariant.mutateAsync({ variantId, productId });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove variant");
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">{product.name}</h1>
            <Badge variant={product.status === "ACTIVE" ? "default" : "outline"}>
              {product.status}
            </Badge>
          </div>
          <p className="text-muted-foreground">
            {product.total_stock} units in stock across {product.variants.length}{" "}
            variant(s)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={product.status} onValueChange={handleStatusChange}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="DRAFT">Draft</SelectItem>
              <SelectItem value="ACTIVE">Active</SelectItem>
              <SelectItem value="INACTIVE">Inactive</SelectItem>
              <SelectItem value="ARCHIVED">Archived</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="destructive" onClick={handleDeleteProduct}>
            <Trash2 className="size-4" /> Delete
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Basic Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>Product name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Short description</Label>
            <Input
              value={shortDescription}
              onChange={(e) => setShortDescription(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Full description</Label>
            <Textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Brand</Label>
            <Input value={brand} onChange={(e) => setBrand(e.target.value)} />
          </div>
          <Button onClick={handleSaveDetails} disabled={updateProduct.isPending}>
            {updateProduct.isPending && <Loader2 className="size-4 animate-spin" />}
            Save details
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Images</CardTitle>
          <CardDescription>
            The main image is shown first. Hover an image to set it as primary
            or remove it.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            {product.images.map((img) => (
              <div
                key={img.id}
                className="group relative size-24 overflow-hidden rounded-md border"
              >
                <Image
                  src={img.url}
                  alt={img.alt_text || product.name}
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
                    onClick={() =>
                      setPrimaryImage.mutate({ productId, imageId: img.id })
                    }
                    className="rounded p-1 text-white hover:bg-white/20"
                    title="Set as primary"
                  >
                    <Star className="size-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      deleteImage.mutate({ productId, imageId: img.id })
                    }
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
        <CardContent className="space-y-4">
          <CategoryPicker selectedIds={categoryIds} onChange={setCategoryIds} />
          <Button onClick={handleSaveDetails} disabled={updateProduct.isPending}>
            Save category
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Variants &amp; Inventory</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>SKU</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Stock</TableHead>
                <TableHead>Availability</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {product.variants.map((variant) => (
                <TableRow key={variant.id}>
                  <TableCell>{variant.name}</TableCell>
                  <TableCell className="font-mono text-xs">{variant.sku}</TableCell>
                  <TableCell>{formatMoney(variant.price, variant.currency)}</TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      min="0"
                      defaultValue={variant.stock_quantity}
                      className="w-24"
                      onBlur={(e) => handleStockChange(variant.id, e.target.value)}
                    />
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        variant.availability === "IN_STOCK" ? "default" : "outline"
                      }
                    >
                      {variant.availability}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteVariant(variant.id)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <form
            onSubmit={handleAddVariant}
            className="grid gap-3 rounded-md border p-4 sm:grid-cols-4"
          >
            <div className="space-y-1.5">
              <Label>Name</Label>
              <Input
                value={newVariant.name}
                onChange={(e) =>
                  setNewVariant((v) => ({ ...v, name: e.target.value }))
                }
                placeholder="White / Blue Switch"
              />
            </div>
            <div className="space-y-1.5">
              <Label>SKU</Label>
              <Input
                value={newVariant.sku}
                onChange={(e) =>
                  setNewVariant((v) => ({ ...v, sku: e.target.value }))
                }
                placeholder="K8-WHITE-BLUE"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Price ({currency})</Label>
              <Input
                type="number"
                min="0"
                step="0.01"
                value={newVariant.price}
                onChange={(e) =>
                  setNewVariant((v) => ({ ...v, price: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Stock</Label>
              <Input
                type="number"
                min="0"
                value={newVariant.stock_quantity}
                onChange={(e) =>
                  setNewVariant((v) => ({ ...v, stock_quantity: e.target.value }))
                }
              />
            </div>
            <div className="sm:col-span-4">
              <Button type="submit" disabled={addVariant.isPending}>
                <Plus className="size-4" /> Add variant
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Agent Availability</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between rounded-md border p-4">
            <div>
              <p className="text-sm font-medium">Agent searchable</p>
              <p className="text-sm text-muted-foreground">
                Toggle whether this product is discoverable through the agent
                catalog API.
              </p>
            </div>
            <Switch
              checked={isAgentSearchable}
              onCheckedChange={(checked) => {
                setIsAgentSearchable(checked);
                updateProduct.mutate({
                  productId,
                  payload: { is_agent_searchable: checked },
                });
              }}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
