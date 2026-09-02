"use client";

import { UserButton } from "@clerk/nextjs";
import { Loader2, Menu, MessageSquarePlus } from "lucide-react";
import { useState } from "react";

import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { ChatSession } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SessionListProps {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  isLoading: boolean;
  isCreating: boolean;
}

function SessionListContent({
  sessions,
  activeId,
  onSelect,
  onNew,
  isLoading,
  isCreating,
}: SessionListProps) {
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
      <nav className="flex-1 space-y-1 overflow-y-auto p-3 pt-0">
        {isLoading ? (
          <Loader2 className="mx-auto mt-4 size-4 animate-spin text-muted-foreground" />
        ) : sessions.length === 0 ? (
          <p className="p-2 text-xs text-muted-foreground">No chats yet — start one above.</p>
        ) : (
          sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              onClick={() => onSelect(session.id)}
              className={cn(
                "block w-full truncate rounded-md px-3 py-2 text-left text-sm transition-colors",
                session.id === activeId
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {session.title || "New chat"}
            </button>
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

export function MobileSessionHeader(props: SessionListProps) {
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
      <UserButton />
    </header>
  );
}
