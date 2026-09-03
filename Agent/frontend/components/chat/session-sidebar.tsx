"use client";

import { UserButton } from "@clerk/nextjs";
import { Check, Loader2, Menu, MessageSquarePlus, MoreHorizontal, Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useDeleteSession, useRenameSession } from "@/lib/queries/use-chat";
import type { ChatSession } from "@/lib/types";
import { cn, groupByRecency } from "@/lib/utils";

interface SessionListProps {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  isLoading: boolean;
  isCreating: boolean;
}

function SessionRow({
  session,
  isActive,
  onSelect,
}: {
  session: ChatSession;
  isActive: boolean;
  onSelect: (id: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(session.title || "");
  const renameSession = useRenameSession();
  const deleteSession = useDeleteSession();

  function commitRename() {
    const trimmed = title.trim();
    setEditing(false);
    if (!trimmed || trimmed === session.title) return;
    renameSession.mutate(
      { sessionId: session.id, title: trimmed },
      { onError: (err) => toast.error(err instanceof Error ? err.message : "Failed to rename chat") }
    );
  }

  if (editing) {
    return (
      <div className="flex items-center gap-1 px-1">
        <Input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitRename();
            if (e.key === "Escape") {
              setTitle(session.title || "");
              setEditing(false);
            }
          }}
          className="h-8 text-sm"
        />
        <Button variant="ghost" size="icon-sm" onClick={commitRename}>
          <Check className="size-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => {
            setTitle(session.title || "");
            setEditing(false);
          }}
        >
          <X className="size-3.5" />
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group flex items-center rounded-md pr-1 transition-colors",
        isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
    >
      <button
        type="button"
        onClick={() => onSelect(session.id)}
        className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm"
      >
        {session.title || "New chat"}
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn(
                "size-6 shrink-0 opacity-0 group-hover:opacity-100 data-popup-open:opacity-100",
                isActive && "text-primary-foreground hover:bg-primary-foreground/20 hover:text-primary-foreground"
              )}
            />
          }
        >
          <MoreHorizontal className="size-3.5" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => setEditing(true)}>
            <Pencil className="size-3.5" /> Rename
          </DropdownMenuItem>
          <DropdownMenuItem
            variant="destructive"
            onClick={() =>
              deleteSession.mutate(session.id, {
                onError: (err) => toast.error(err instanceof Error ? err.message : "Failed to delete chat"),
              })
            }
          >
            <Trash2 className="size-3.5" /> Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

function SessionListContent({
  sessions,
  activeId,
  onSelect,
  onNew,
  isLoading,
  isCreating,
}: SessionListProps) {
  const groups = groupByRecency(sessions, (s) => s.updated_at);

  return (
    <>
      <div className="flex h-16 items-center border-b px-4">
        <Logo markClassName="size-6" textClassName="text-sm font-semibold" />
      </div>
      <div className="p-3">
        <Button className="w-full" onClick={onNew} disabled={isCreating}>
          {isCreating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <MessageSquarePlus className="size-4" />
          )}
          New chat
        </Button>
      </div>
      <nav className="flex-1 space-y-3 overflow-y-auto p-3 pt-0">
        {isLoading ? (
          <Loader2 className="mx-auto mt-4 size-4 animate-spin text-muted-foreground" />
        ) : sessions.length === 0 ? (
          <p className="p-2 text-xs text-muted-foreground">No chats yet — start one above.</p>
        ) : (
          groups.map(([label, group]) => (
            <div key={label} className="space-y-1">
              <p className="px-3 py-1 text-xs font-medium text-muted-foreground">{label}</p>
              {group.map((session) => (
                <SessionRow key={session.id} session={session} isActive={session.id === activeId} onSelect={onSelect} />
              ))}
            </div>
          ))
        )}
      </nav>
      <div className="flex items-center gap-3 border-t p-4">
        <UserButton />
        <span className="text-sm text-muted-foreground">Account</span>
      </div>
    </>
  );
}

export function SessionSidebar(props: SessionListProps) {
  return (
    <aside className="hidden w-64 flex-col border-r bg-muted/20 md:flex">
      <SessionListContent {...props} />
    </aside>
  );
}

export function MobileSessionHeader(props: SessionListProps & { rightSlot?: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <header className="flex h-14 items-center justify-between border-b px-3 md:hidden">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger render={<Button variant="ghost" size="icon" />}>
          <Menu className="size-5" />
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <SheetTitle className="sr-only">Chats</SheetTitle>
          <div className="flex h-full flex-col">
            <SessionListContent
              {...props}
              onSelect={(id) => {
                props.onSelect(id);
                setOpen(false);
              }}
              onNew={() => {
                props.onNew();
                setOpen(false);
              }}
            />
          </div>
        </SheetContent>
      </Sheet>
      <Logo markClassName="size-6" textClassName="text-sm font-semibold" />
      <div className="flex items-center gap-2">
        {props.rightSlot}
        <UserButton />
      </div>
    </header>
  );
}
