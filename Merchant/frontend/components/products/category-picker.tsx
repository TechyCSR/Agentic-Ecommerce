"use client";

import { useCategories } from "@/lib/queries/use-categories";
import type { Category } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CategoryPickerProps {
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

export function CategoryPicker({ selectedIds, onChange }: CategoryPickerProps) {
  const { data: categories, isLoading } = useCategories();

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading categories...</p>;
  }

  const roots = (categories ?? []).filter((c) => !c.parent_id);
  const childrenOf = (parent: Category) =>
    (categories ?? []).filter((c) => c.parent_id === parent.id);

  function toggle(id: string) {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((sid) => sid !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  }

  return (
    <div className="space-y-4">
      {roots.map((root) => (
        <div key={root.id}>
          <p className="mb-2 text-sm font-medium">{root.name}</p>
          <div className="flex flex-wrap gap-2">
            {childrenOf(root).map((child) => {
              const active = selectedIds.includes(child.id);
              return (
                <button
                  type="button"
                  key={child.id}
                  onClick={() => toggle(child.id)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs transition-colors",
                    active
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-background text-muted-foreground hover:bg-muted"
                  )}
                >
                  {child.name}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
